"""
AceDecisionAgent — Responsabilité UNIQUE : logique de décision par phases ACE.

Extrait de TaskAgent où cette logique était mélangée avec la création de tâches,
la coordination du scoring et l'envoi d'emails.

Phases :
  Phase 1 ( 0– 9 overrides) : ACE observe silencieusement — RH décide tout.
  Phase 2 (10–19 overrides) : ACE suggère, RH valide.
  Phase 3 (20–29 overrides) : ACE suggère fortement (justifications), RH valide.
  Phase 4 (30+  overrides)  : ACE autonome sur cas clairs (score >85 ou <40)
                               si confiance ≥ 60 %.

Appelé par l'orchestrateur APRÈS que ScoreAgent a retourné son résultat.

NE FAIT PAS :
  - Scorer un CV              → ScoreAgent
  - Créer des tâches MiniGED  → TaskAgent
  - Envoyer des emails        → EmailAgent
  - Planifier Calendar        → TaskAgent.create_calendar_event()
  - Persister des données     → orchestrateur
"""
from __future__ import annotations

from agents.base_agent import BaseAgent

# ── Seuils ACE ────────────────────────────────────────────────────────────────
ACE_CONFIDENCE_THRESHOLD = 0.60
ACE_PHASE4_SCORE_HIGH    = 85
ACE_PHASE4_SCORE_LOW     = 40


class AceDecisionAgent(BaseAgent):
    """
    Reçoit le résultat brut de ScoreAgent et retourne :
      - La phase ACE courante (1-4)
      - Le niveau de confiance calculé
      - La suggestion structurée (pour ScoreValidationBanner.vue)
      - Un flag `auto_act` indiquant si ACE peut agir seul (Phase 4 uniquement)

    NE FAIT PAS :
      - Scorer un CV                → ScoreAgent
      - Créer des tâches MiniGED    → TaskAgent
      - Envoyer des emails          → EmailAgent
      - Planifier Calendar          → TaskAgent.create_calendar_event()
      - Persister des données       → orchestrateur
    """

    NAME         = "AceDecisionAgent"
    SKILLS       = []
    TOOL_SERVERS = []
    SYSTEM_PROMPT = ""

    # ═══════════════════════════════════════════════════════════════════════
    # POINT D'ENTRÉE PRINCIPAL
    # ═══════════════════════════════════════════════════════════════════════

    def run(
        self,
        score:          int,
        recommendation: str,
        position:       str,
    ) -> dict:
        """
        Évalue la décision ACE à partir du score et de la recommandation
        produits par ScoreAgent.

        Paramètres :
          score          : score IA (0-100)
          recommendation : "Entretien" | "ListeAttente" | "Refus"
          position       : intitulé du poste (pour filtrer les bullets pertinents)

        Retourne :
          {
            "phase":           int,    # 1 | 2 | 3 | 4
            "ace_confidence":  float,  # 0.0 – 0.95
            "total_overrides": int,
            "suggestion":      dict,   # payload pour ScoreValidationBanner.vue
            "auto_act":        bool,   # True → orchestrateur peut agir sans RH
            "react_trace":     list,
          }
        """
        self._reset()
        self._step("thought",
            f"AceDecisionAgent | score={score} | rec={recommendation} | pos='{position}'")

        phase, total_overrides, bullets = self._get_phase()
        ace_confidence = self._compute_confidence(position, score)

        suggestion = self._build_suggestion(
            score           = score,
            recommendation  = recommendation,
            position        = position,
            phase           = phase,
            total_overrides = total_overrides,
            ace_confidence  = ace_confidence,
            bullets         = bullets,
        )

        is_clear_case = (
            score >= ACE_PHASE4_SCORE_HIGH or score <= ACE_PHASE4_SCORE_LOW
        )
        auto_act = (
            phase == 4
            and is_clear_case
            and ace_confidence >= ACE_CONFIDENCE_THRESHOLD
        )

        self._step("observe",
            f"Phase={phase} | overrides={total_overrides} | "
            f"confiance={ace_confidence:.0%} | auto_act={auto_act}")

        if phase == 1:
            self._step("observe",
                f"[ACE Phase 1] Apprentissage passif "
                f"({total_overrides}/10 CVs) → RH requis")
        elif phase == 2:
            self._step("observe",
                f"[ACE Phase 2] Suggestion → {recommendation} | "
                f"confiance={ace_confidence:.0%} | {total_overrides}/20 CVs traités")
        elif phase == 3:
            if is_clear_case:
                self._step("observe",
                    f"[ACE Phase 3] Cas clair (score={score}) | "
                    f"confiance={ace_confidence:.0%} "
                    "→ suggestion forte — validation RH OBLIGATOIRE")
            else:
                self._step("observe",
                    f"[ACE Phase 3] Cas ambigu (score={score} entre "
                    f"{ACE_PHASE4_SCORE_LOW} et {ACE_PHASE4_SCORE_HIGH}) "
                    "→ suggestion visible — validation RH OBLIGATOIRE")
        elif phase == 4:
            if auto_act:
                self._step("observe",
                    f"[ACE Phase 4] Autonome | cas clair (score={score}) | "
                    f"confiance={ace_confidence:.0%} → {recommendation}")
            elif not is_clear_case:
                self._step("observe",
                    f"[ACE Phase 4] Cas ambigu (score={score} entre "
                    f"{ACE_PHASE4_SCORE_LOW} et {ACE_PHASE4_SCORE_HIGH}) "
                    "→ RH requis même en Phase 4")
            else:
                self._step("observe",
                    f"[ACE Phase 4] Confiance {ace_confidence:.0%} "
                    f"< seuil {ACE_CONFIDENCE_THRESHOLD:.0%} → RH requis")

        return {
            "phase":           phase,
            "ace_confidence":  ace_confidence,
            "total_overrides": total_overrides,
            "suggestion":      suggestion,
            "auto_act":        auto_act,
            "react_trace":     self.trace,
        }

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE
    # ═══════════════════════════════════════════════════════════════════════

    def _get_phase(self) -> tuple[int, int, list]:
        """
        Lit le playbook ACE et retourne (phase, total_overrides, bullets).
        Fallback sur Phase 1 / 0 overrides si le playbook est inaccessible.
        """
        try:
            from ace.playbook_store import load_playbook
            pb              = load_playbook()
            total_overrides = len(pb.get("override_log", []))
            bullets         = pb.get("bullets", [])
            if   total_overrides < 10: phase = 1
            elif total_overrides < 20: phase = 2
            elif total_overrides < 30: phase = 3
            else:                      phase = 4
            return phase, total_overrides, bullets
        except Exception as e:
            self._step("observe", f"[ACE] Phase non calculée : {e}")
            return 1, 0, []

    # ═══════════════════════════════════════════════════════════════════════
    # CONFIANCE
    # ═══════════════════════════════════════════════════════════════════════

    def _compute_confidence(self, position: str, score: int) -> float:
        """
        Calcule un indice de confiance entre 0.0 et 0.95
        en fonction du nombre d'overrides RH passés sur ce type de poste
        et du helpful_count cumulé des bullets actifs.

        Le paramètre `score` est conservé pour une évolution future
        (pondération par plage de score).
        """
        try:
            import re, unicodedata
            from ace.playbook_store import load_playbook

            def _norm(t: str) -> str:
                t = unicodedata.normalize("NFD", t.lower()).encode("ascii", "ignore").decode()
                return re.sub(r"[^\w\s]", " ", t).strip()

            pb       = load_playbook()
            pos_norm = _norm(position)

            n_overrides = len([
                o for o in pb.get("override_log", [])
                if (pos_norm in _norm(o.get("position", ""))
                    or _norm(o.get("position", "")) in pos_norm)
            ])
            total_helpful = sum(
                b.get("helpful_count", 0) for b in pb.get("bullets", [])
            )
            base = n_overrides + total_helpful
            if base == 0:
                return 0.0
            return min(0.95, round(1.0 - (1.0 / (1.0 + base * 0.4)), 3))
        except Exception as e:
            self._step("observe", f"[ACE] Confiance non calculée : {e}")
            return 0.0

    # ═══════════════════════════════════════════════════════════════════════
    # SUGGESTION
    # ═══════════════════════════════════════════════════════════════════════

    def _build_suggestion(
        self,
        score:           int,
        recommendation:  str,
        position:        str,
        phase:           int,
        total_overrides: int,
        ace_confidence:  float,
        bullets:         list,
    ) -> dict:
        """
        Construit la payload suggestion affichée dans ScoreValidationBanner.vue.
        Ne prend aucune décision — construit uniquement la structure de données.
        """
        import re, unicodedata

        def _norm(t: str) -> str:
            t = unicodedata.normalize("NFD", t.lower()).encode("ascii", "ignore").decode()
            return re.sub(r"[^\w\s]", " ", t).strip()

        pos_norm       = _norm(position)
        justifications = []

        for b in bullets:
            meta    = b.get("metadata", {})
            pos_pat = _norm(meta.get("position_pattern", ""))
            signs   = meta.get("rh_note_signs", "")

            if not pos_pat:
                continue
            if pos_pat not in pos_norm and pos_norm not in pos_pat:
                continue

            # Filtrer sur les bornes de score si non-triviales
            s_min = meta.get("score_min", 0)
            s_max = meta.get("score_max", 100)
            if not (s_min == 0 and s_max == 100):
                if not (s_min <= score <= s_max):
                    continue

            sign = "+" if "+" in signs else ("-" if "-" in signs else "ℹ")
            justifications.append({
                "sign":          sign,
                "text":          b.get("content", ""),
                "helpful_count": b.get("helpful_count", 0),
                "bullet_id":     b.get("id", ""),
            })

        justifications = sorted(
            justifications, key=lambda x: -x["helpful_count"]
        )[:5]

        is_clear_case = (
            score >= ACE_PHASE4_SCORE_HIGH or score <= ACE_PHASE4_SCORE_LOW
        )
        auto_act = (
            phase == 4
            and is_clear_case
            and ace_confidence >= ACE_CONFIDENCE_THRESHOLD
        )

        phase_labels     = {1: "ACE observe", 2: "ACE suggère",
                            3: "ACE suggère (fort)", 4: "ACE autonome"}
        overrides_to_next = {1: 10, 2: 20, 3: 30, 4: 30}

        if phase == 1:
            message = (
                f"ACE est en apprentissage ({total_overrides}/10 CVs traités). "
                "Notes RH obligatoires pour améliorer l'IA."
            )
        elif phase == 2:
            message = (
                f"ACE suggère : {recommendation}. "
                "Votre validation est requise."
            )
        elif phase == 3:
            message = (
                f"ACE recommande fortement : {recommendation} "
                f"(score={score}/100, confiance={ace_confidence:.0%}). "
                "Votre validation est requise — ACE ne peut pas encore agir seul."
            )
        else:  # Phase 4
            if is_clear_case and ace_confidence >= ACE_CONFIDENCE_THRESHOLD:
                message = (
                    f"ACE autonome ({ace_confidence:.0%} confiance) — "
                    "décision appliquée automatiquement. Vous pouvez annuler."
                )
            else:
                message = (
                    f"ACE autonome mais confiance insuffisante "
                    f"({ace_confidence:.0%}) — votre validation est requise."
                )

        return {
            "phase":                   phase,
            "phase_label":             phase_labels.get(phase, "ACE"),
            "suggested_action":        recommendation,
            "confidence":              ace_confidence,
            "total_overrides":         total_overrides,
            "overrides_to_next_phase": max(
                0, overrides_to_next.get(phase, 30) - total_overrides),
            "justifications":          justifications,
            "score":                   score,
            "is_clear_case":           is_clear_case,
            "auto_acted":              auto_act,
            "needs_rh_notes":          phase <= 2,
            "message":                 message,
        }