"""
ScoreAgent — Responsabilités UNIQUES :
  1. Trouver l'offre d'emploi correspondante dans MiniGED (3 passes)
  2. Scorer le CV vs l'offre via LLM
  3. Retourner score + strengths + gaps + summary + recommendation

Le playbook ACE est toujours injecté ici pour que le LLM
en tienne compte dans l'évaluation — c'est intentionnel.
La DÉCISION sur ce qu'on fait du score appartient à AceDecisionAgent.

NE FAIT PAS :
  - Décider des phases ACE            → AceDecisionAgent
  - Créer des tâches MiniGED          → TaskAgent
  - Planifier Calendar / Email        → TaskAgent + EmailAgent
  - Coordonner les agents             → orchestrateur
"""
from __future__ import annotations
import json, re, time, unicodedata
from agents.base_agent import BaseAgent
from core.constants import MCP_LOCAL, MCP_SPECS

# ── Seuils de décision (utilisés pour la recommandation textuelle) ────────────
SCORE_INTERVIEW = 70
SCORE_WAITING   = 50


class ScoreAgent(BaseAgent):

    NAME          = "ScoreAgent"
    SKILLS        = []
    TOOL_SERVERS  = []
    SYSTEM_PROMPT = (
        "Tu es un expert RH. Tu compares objectivement un profil candidat "
        "avec une offre d'emploi. Réponds UNIQUEMENT en JSON valide."
    )

    # ═══════════════════════════════════════════════════════════════════════
    # POINT D'ENTRÉE PRINCIPAL
    # ═══════════════════════════════════════════════════════════════════════

    def run(
        self,
        candidate_name: str,
        position:       str,
        cv_text:        str,
        document_id:    str = "",
        linkedin_url:   str = "",
        **_,
    ) -> dict:
        """
        Score un CV par rapport à une offre d'emploi.

        Retourne :
          {
            "score":          int,        # 0-100
            "recommendation": str,        # "Entretien" | "ListeAttente" | "Refus"
            "status_to_set":  str,        # valeur MiniGED alignée
            "strengths":      list[str],
            "gaps":           list[str],
            "summary":        str,        # 2 phrases
            "offer_found":    bool,
            "offer_title":    str,
            "ace_playbook":   bool,       # True si playbook injecté dans le prompt
            "react_trace":    list,
          }
        """
        self._reset()
        self._step("thought", f"ScoreAgent | '{candidate_name}' → '{position}'")

        # ── 1. Injecter le playbook ACE dans le prompt LLM ──────────────────
        # Le playbook contient les leçons apprises des décisions RH passées.
        # AceDecisionAgent prend la DÉCISION ; ScoreAgent l'utilise uniquement
        # pour affiner le score LLM.
        playbook_text   = ""
        playbook_loaded = False
        try:
            from ace.playbook_store import render_playbook, get_active_bullets
            bullets = get_active_bullets()
            if bullets:
                playbook_text   = render_playbook()
                playbook_loaded = True
                self._step("observe",
                    f"[ACE] Playbook injecté | {len(bullets)} bullet(s) | "
                    f"pos='{position}'")
            else:
                self._step("observe",
                    "[ACE] Playbook vide — scoring sans contexte ACE")
        except Exception as e:
            self._step("observe",
                f"[ACE] Playbook non disponible (non bloquant) : {e}")

        # ── 2. Trouver l'offre dans MiniGED ─────────────────────────────────
        offer_text, offer_found, offer_title = self._find_job_offer(position)
        self._step("observe",
            f"Offre utilisée : '{offer_title}' ({len(offer_text)} car.) "
            f"| source={'ged' if offer_found else 'position_fallback'}")

        if linkedin_url:
            self._step("observe",
                "linkedin_url ignoré (scraping LinkedIn non supporté)")

        # ── 3. Scorer ───────────────────────────────────────────────────────
        score_data = self._score_with_llm(
            candidate_name, position, cv_text, offer_text, playbook_text)
        score = score_data.get("score", -1)

        if score < 0:
            self._step("observe", "Echec LLM → scoring skipped")
            return {
                "skipped":     True,
                "reason":      "llm_failure",
                "offer_found": offer_found,
                "react_trace": self.trace,
            }

        recommendation = self._decide_recommendation(score)
        status_to_set  = self._status_from_recommendation(recommendation)
        self._step("observe",
            f"Score={score}/100 | {recommendation} | →{status_to_set}")
        self._step("answer",
            f"Scoring OK | offer_found={offer_found} | "
            f"ace_playbook={playbook_loaded} | {self._elapsed_ms()}ms")

        return {
            "score":          score,
            "recommendation": recommendation,
            "status_to_set":  status_to_set,
            "strengths":      score_data.get("strengths", []),
            "gaps":           score_data.get("gaps", []),
            "summary":        score_data.get("summary", ""),
            "offer_found":    offer_found,
            "offer_title":    offer_title,
            "ace_playbook":   playbook_loaded,
            "react_trace":    self.trace,
        }

    # ═══════════════════════════════════════════════════════════════════════
    # RECHERCHE OFFRE D'EMPLOI (3 passes + Jaccard)
    # ═══════════════════════════════════════════════════════════════════════

    def _find_job_offer(self, position: str) -> tuple[str, bool, str]:
        """
        3 passes de recherche avec sélection Jaccard.
        Seuil minimum 12 % pour éviter les faux positifs.
        """
        keywords    = self._extract_keywords(position)
        MIN_RELEVANCE = 0.12
        self._step("action", f"MiniGED search_documents → '{keywords}'")

        def _norm_set(t: str) -> set:
            t = unicodedata.normalize("NFD", t.lower()).encode("ascii","ignore").decode()
            return set(re.sub(r"[^\w\s]", " ", t).split())

        def _is_offer(r: dict) -> bool:
            for field in [
                r.get("aiDocumentType",""), r.get("documentType",""),
                r.get("documentTitle",""),  r.get("title",""),
                r.get("documentDescription",""), r.get("snippet",""),
            ]:
                f = self._normalize(field)
                if "offre" in f or "emploi" in f:
                    return True
            return False

        def _jaccard(pos_words: set, r: dict) -> float:
            doc_text = " ".join([
                r.get("documentTitle",""), r.get("title",""),
                r.get("snippet",""), r.get("aiSummaryPreview",""),
                r.get("documentDescription",""),
            ])
            doc_words = _norm_set(doc_text)
            if not doc_words:
                return 0.0
            return len(pos_words & doc_words) / max(len(pos_words | doc_words), 1)

        def _parse_results(raw) -> list:
            outer = json.loads(raw) if isinstance(raw, str) else (raw or {})
            if isinstance(outer, list):
                items = outer
            else:
                items = outer.get("results",
                        outer.get("items",
                        outer.get("documents", [])))
            if isinstance(items, dict):
                items = items.get("items", [])
            parsed = []
            for r in (items if isinstance(items, list) else []):
                if isinstance(r, dict):
                    parsed.append(r)
                elif isinstance(r, str):
                    try:    parsed.append(json.loads(r))
                    except: parsed.append({"documentTitle": r})
            return parsed

        def _get_text_and_return(r: dict) -> tuple[str, bool, str]:
            doc_id = r.get("documentId") or r.get("id")
            title  = r.get("documentTitle") or r.get("title") or "Offre"
            text   = self._get_full_offer_text(doc_id) if doc_id else ""
            if not text:
                text = (
                    r.get("snippet") or r.get("aiSummaryPreview") or
                    r.get("documentDescription") or ""
                )
            self._step("observe",
                f"Offre trouvée (aiDocumentType) : "
                f"'{r.get('aiDocumentType', '')}' ({len(text)} car.)")
            return text, True, title

        def _best_offer(results: list, pos_words: set, passe: int):
            best, best_score = None, -1.0
            for r in results:
                if not _is_offer(r):
                    continue
                s = _jaccard(pos_words, r)
                if s > best_score:
                    best_score, best = s, r
            if best and best_score >= MIN_RELEVANCE:
                self._step("observe",
                    f"Offre sélectionnée (passe {passe}) | "
                    f"pertinence={best_score:.0%}")
                return best
            if best:
                self._step("observe",
                    f"Offre ignorée (passe {passe}) | "
                    f"pertinence={best_score:.0%} < seuil {MIN_RELEVANCE:.0%} | "
                    f"'{best.get('documentTitle','?')}' trop éloignée du poste")
            return None

        pos_words = _norm_set(position)

        try:
            from mcp_client import call_mcp_tool

            # PASSE 1 — mots-clés du poste
            raw1     = call_mcp_tool(
                MCP_LOCAL["miniged"], "search_documents",
                {"query": keywords, "page": 1, "page_size": 10},
            )
            results1 = _parse_results(raw1)
            self._step("observe",
                f"search_documents: {len(results1)} résultat(s) parsés")
            best = _best_offer(results1, pos_words, 1)
            if best:
                return _get_text_and_return(best)

            # PASSE 2 — 'offre emploi'
            self._step("action", "Fallback search → 'offre emploi'")
            raw2     = call_mcp_tool(
                MCP_LOCAL["miniged"], "search_documents",
                {"query": "offre emploi", "page": 1, "page_size": 10},
            )
            results2 = _parse_results(raw2)
            self._step("observe",
                f"fallback search: {len(results2)} résultat(s)")
            best = _best_offer(results2, pos_words, 2)
            if best:
                return _get_text_and_return(best)

            # PASSE 3 — get_documents complet
            self._step("action", "Fallback get_documents → liste complète")
            raw3  = call_mcp_tool(
                MCP_LOCAL["miniged"], "get_documents",
                {"user_id": 0, "limit": 50},
            )
            data3 = json.loads(raw3) if isinstance(raw3, str) else (raw3 or {})
            docs3 = (
                data3 if isinstance(data3, list)
                else data3.get("items", data3.get("documents", []))
            )
            self._step("observe", f"get_documents: {len(docs3)} docs au total")
            best = _best_offer(docs3, pos_words, 3)
            if best:
                return _get_text_and_return(best)

            self._step("observe",
                "Aucune offre pertinente trouvée après 3 passes")
            return (
                f"Poste recherché : {position}\n\n"
                "Critères généraux attendus : expérience pertinente sur le poste, "
                "compétences techniques en adéquation, formation adaptée.",
                False, position,
            )

        except Exception as e:
            self._step("observe", f"_find_job_offer failed: {e}")
            import traceback
            self._step("observe", traceback.format_exc()[:300])
            return (f"Poste recherché : {position}", False, position)

    def _get_full_offer_text(self, doc_id) -> str:
        try:
            from mcp_client import call_mcp_tool
            raw  = call_mcp_tool(
                MCP_LOCAL["miniged"], "get_document_text",
                {"document_id": int(doc_id)},
            )
            data = json.loads(raw) if isinstance(raw, str) else raw or {}
            return data.get("mergedText", "")[:3000]
        except Exception:
            return ""

    # ═══════════════════════════════════════════════════════════════════════
    # SCORING LLM avec injection du playbook ACE
    # ═══════════════════════════════════════════════════════════════════════

    def _score_with_llm(
        self,
        candidate_name: str,
        position:       str,
        cv_text:        str,
        offer_text:     str,
        playbook_text:  str = "",
    ) -> dict:
        self._step("action", "Groq → scoring CV vs offre")

        ace_section = ""
        if playbook_text.strip():
            ace_section = (
                f"\n\n{playbook_text}\n\n"
                "INSTRUCTIONS IMPORTANTES :\n"
                "- Applique les règles du playbook ACE ci-dessus dans ton évaluation.\n"
                "- Les règles avec helpful élevé sont les plus fiables.\n"
                "- Une règle '+' signifie que ce critère justifie un Entretien.\n"
                "- Une règle '-' signifie un point de vigilance à vérifier.\n"
            )

        prompt = (
            f"Analyse la correspondance STRICTE entre ce candidat et ce poste.\n\n"
            f"CANDIDAT : {candidate_name}\n\n"
            f"=== CV ===\n{cv_text[:2500]}\n\n"
            f"=== OFFRE D'EMPLOI ===\n{offer_text[:1500]}\n"
            f"{ace_section}\n"
            "Critères de notation STRICTS :\n"
            "- Expérience 40% : années EN PRODUCTION (pas académique)\n"
            "- Compétences 35% : correspondance EXACTE avec les outils de l'offre\n"
            "- Formation 15% : diplôme requis\n"
            "- Soft skills 10%\n\n"
            "RÈGLE ABSOLUE : Si les compétences techniques SPÉCIFIQUES de l'offre "
            "sont absentes du CV, le score NE PEUT PAS dépasser 50.\n\n"
            "Retourne UNIQUEMENT ce JSON (sans markdown) :\n"
            '{"score":<0-100>,"strengths":["..."],"gaps":["..."],'
            '"summary":"<2 phrases>","recommendation":"Entretien|ListeAttente|Refus"}'
        )

        from services.llm_client import generate
        try:
            raw = generate(
                prompt,
                max_tokens=450,
                system=self.SYSTEM_PROMPT,
                temperature=0.1,
            ).strip()
            raw = re.sub(r"```json|```", "", raw).strip()

            if not raw:
                self._step("observe", "Scoring LLM échec définitif: Réponse vide")
                return self._empty_score()

            data = json.loads(raw)
            data["score"] = max(0, min(100, int(data.get("score", 0))))
            for field in ("strengths", "gaps"):
                if not isinstance(data.get(field), list):
                    data[field] = []
            data.setdefault("summary", "")
            data.setdefault("recommendation", "")

            self._step("observe",
                f"score={data['score']} | {data.get('recommendation')}")
            return data

        except json.JSONDecodeError as e:
            self._step("observe",
                f"Scoring LLM échec — JSON invalide: {e} | raw='{raw[:80]}'")
            return self._empty_score()
        except Exception as e:
            self._step("observe", f"Scoring LLM échec définitif: {e}")
            return self._empty_score()

    def _empty_score(self) -> dict:
        return {
            "score":          -1,
            "strengths":      [],
            "gaps":           [],
            "summary":        "",
            "recommendation": "",
        }

    # ═══════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════

    def _extract_keywords(self, position: str) -> str:
        stop = {
            "de","du","la","le","les","en","et","ou","un","une","des",
            "au","aux","pour","par","sur","dans","avec","est","son","sa",
            "h","f","hf","h/f","(h/f)",
        }
        cleaned = re.sub(r"[^\w\s]", " ", position)
        words   = [
            self._normalize(w)
            for w in cleaned.split()
            if len(w) > 2 and self._normalize(w) not in stop
        ]
        return " ".join(words[:6]) if words else self._normalize(position[:60])

    @staticmethod
    def _normalize(text: str) -> str:
        return (
            unicodedata.normalize("NFD", text.lower())
                       .encode("ascii", "ignore")
                       .decode()
        )

    def _decide_recommendation(self, score: int) -> str:
        if score >= SCORE_INTERVIEW: return "Entretien"
        if score >= SCORE_WAITING:   return "ListeAttente"
        return "Refus"

    def _status_from_recommendation(self, recommendation: str) -> str:
        key  = re.sub(r"[\s\-_]+", "", recommendation).lower()
        _MAP = {
            "entretien":    "Entretien",
            "listeattente": "ListeAttente",
            "listdattente": "ListeAttente",
            "liste":        "ListeAttente",
            "attente":      "ListeAttente",
            "refus":        "Refuse",
            "refuse":       "Refuse",
            "refusé":       "Refuse",
        }
        status = _MAP.get(key)
        if status:
            return status
        if "entretien" in key:
            return "Entretien"
        if "attente" in key or "liste" in key:
            return "ListeAttente"
        if "refus" in key:
            return "Refuse"
        self._step("observe",
            f"_status_from_recommendation: '{recommendation}' → ATraiter")
        return "ATraiter"