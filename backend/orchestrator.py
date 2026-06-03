"""
Orchestrateur — responsabilité : coordination des agents.

Après refactorisation des responsabilités :

  ClassifierAgent   → classer chaque fichier
  SummarizerAgent   → résumer chaque fichier
  ScoreAgent        → scorer le CV vs offre d'emploi (+ injection playbook ACE)
  AceDecisionAgent  → décider selon la phase ACE (suggestion ou auto_act)
  TaskAgent         → créer les tâches MiniGED + mettre à jour le statut
                       + créer l'événement Calendar
  EmailAgent        → envoyer tout email (convocation, refus, score)

L'orchestrateur ne contient AUCUNE logique métier propre :
  il appelle les agents dans le bon ordre et assemble leurs résultats.
"""
from __future__ import annotations
import json, os, sys, uuid, time as _time
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from memory.short_term import get_short_term_memory

_trace: list = []
_t0: float = 0.0

def _step(step_type: str, content: str) -> None:
    ms = int((_time.time() - _t0) * 1000) if _t0 else 0
    _trace.append({"type": step_type, "content": content, "ms": ms})
    print(f"[Orchestrateur/{step_type.upper()}] {content[:120]}", file=sys.stderr)


def _get_files_from_miniged(document_id: str) -> list:
    from mcp_client import call_mcp_tool
    from core.constants import MCP_LOCAL
    stm = get_short_term_memory()
    try:
        raw  = call_mcp_tool(MCP_LOCAL["miniged"], "get_document_text",
                              {"document_id": int(document_id)})
        data = json.loads(raw)
        if "error" in data:
            _step("observe", f"MCP miniged: {data['error']}")
            return []
        files = [
            {"file_id": f.get("fileId"), "filename": f.get("filename"),
             "textContent": f.get("textContent", "")}
            for f in data.get("files", []) if f.get("hasText")
        ]
        _step("observe", f"MCP miniged: {len(files)} fichier(s) avec texte")
        return files
    except Exception as e:
        _step("observe", f"MCP miniged failed ({e}) → fallback mémoire")
        text     = stm.get_document_text()
        filename = stm.get_last_filename()
        if text.strip():
            return [{"file_id": None, "filename": filename, "textContent": text}]
        return []


# ── Résumé ────────────────────────────────────────────────────────────────────

def summarize_document_files(document_id: str, miniged_token: str = "",
                              force: bool = False) -> dict:
    global _trace, _t0
    _trace = []
    _t0 = _time.time()
    _step("thought", f"Résumé | doc_id={document_id}")
    files_data = _get_files_from_miniged(document_id)
    if not files_data:
        return {"document_id": document_id, "summaries": [],
                "consolidated": "Aucun fichier disponible.", "error": "no_files"}
    from agents.summarizer_agent import SummarizerAgent
    summaries = []
    for f in files_data:
        fname = f.get("filename", "fichier")
        text  = (f.get("textContent", "") or "").strip()
        if not text:
            summaries.append({"file_id": f.get("file_id"), "filename": fname,
                               "summary": "Contenu vide.", "skipped": True})
            continue
        _step("action", f"SummarizerAgent → '{fname}'")
        sr      = SummarizerAgent().run(text=text, filename=fname)
        summary = (sr.get("summary", "") or "").strip()
        summaries.append({"file_id": f.get("file_id"), "filename": fname,
                           "summary": summary, "skipped": False})
        _step("observe", f"'{fname}' → {len(summary)} car.")
    done         = [s for s in summaries if not s.get("skipped")]
    consolidated = _consolidate(done)
    get_short_term_memory().set_result("summary", consolidated)
    return {"document_id": document_id, "file_count": len(files_data),
            "summaries": summaries, "consolidated": consolidated,
            "react_trace": list(_trace)}


def summarize_specific_file(document_id: str, file_id: str,
                             miniged_token: str = "") -> dict:
    global _trace
    _trace = []
    _step("thought", f"Résumé fichier | doc_id={document_id} file_id={file_id}")
    files_data = _get_files_from_miniged(document_id)
    target = next(
        (f for f in files_data if str(f.get("file_id")) == str(file_id)), None)
    if not target:
        return {"error": f"Fichier {file_id} non trouvé dans le document {document_id}"}
    fname = target.get("filename", "fichier")
    text  = (target.get("textContent", "") or "").strip()
    if not text:
        return {"file_id": file_id, "filename": fname, "summary": "Contenu vide."}
    from agents.summarizer_agent import SummarizerAgent
    sr      = SummarizerAgent().run(text=text, filename=fname)
    summary = (sr.get("summary", "") or "").strip()
    get_short_term_memory().set_result("summary", summary)
    return {"file_id": file_id, "filename": fname, "summary": summary,
            "react_trace": list(_trace)}


# ── Analyse complète ──────────────────────────────────────────────────────────
#
# Pipeline de responsabilités après refactorisation :
#
#   1. ClassifierAgent  → type de chaque fichier
#   2. SummarizerAgent  → résumé de chaque fichier
#   3. RAG indexation   → orchestrateur
#   4. TaskAgent        → tâches MiniGED + statut initial "ATraiter"
#   5. ScoreAgent       → score CV (si doc RH scorable)
#   6. AceDecisionAgent → phase + confiance + suggestion (si score disponible)
#   7. Orchestrateur    → exécuter auto_act si Phase 4 (Calendar via TaskAgent,
#                          emails via EmailAgent)
#   8. Persistance .NET → AiScore + résumé
#   9. Action email     → pending_action pour confirmation RH
#
def analyze_document_files(document_id: str, miniged_token: str = "",
                            force: bool = False) -> dict:
    global _trace, _t0
    _trace = []
    _t0 = _time.time()
    _step("thought", f"Analyse classify+summarize | doc_id={document_id}")

    # ── 1 & 2 : Classifier + Summarizer ──────────────────────────────────────
    files_data = _get_files_from_miniged(document_id)
    if not files_data:
        return {"document_id": document_id, "document_type": "Autre",
                "summaries": [], "consolidated": "Aucun fichier disponible.",
                "error": "no_files"}

    from agents.classifier_agent import ClassifierAgent, aggregate_document_type
    from agents.summarizer_agent import SummarizerAgent

    classifier = ClassifierAgent()
    summarizer = SummarizerAgent()
    summaries  = []

    for f in files_data:
        fname   = f.get("filename", "fichier")
        text    = (f.get("textContent", "") or "").strip()
        file_id = f.get("file_id")
        if not text:
            summaries.append({"file_id": file_id, "filename": fname,
                               "document_type": "Autre", "confidence": 0.0,
                               "summary": "Contenu vide.", "skipped": True, "raw_text": ""})
            continue

        _step("action", f"ClassifierAgent → '{fname}'")
        clf   = classifier.run(text=text, filename=fname)
        ftype = clf.get("label", "Autre")
        conf  = clf.get("confidence", 0.0)
        _step("observe", f"'{fname}' → {ftype} ({conf:.0%})")

        _step("action", f"SummarizerAgent → '{fname}' ({ftype})")
        sr      = summarizer.run(text=text, filename=fname, document_type=ftype)
        summary = (sr.get("summary", "") or "").strip()
        _step("observe", f"'{fname}' résumé={len(summary)} car.")

        summaries.append({
            "file_id": file_id, "filename": fname,
            "document_type": ftype, "confidence": conf,
            "summary": summary, "skipped": False, "raw_text": text,
        })

    done         = [s for s in summaries if not s.get("skipped")]
    file_types   = [s["document_type"] for s in done]
    doc_type     = aggregate_document_type(file_types)
    _step("observe", f"Type agrégé → {doc_type}")
    consolidated = _consolidate_structured(done, doc_type)
    stm = get_short_term_memory()
    stm.set_result("summary", consolidated)

    # ── 3 : RAG indexation (non bloquant) ────────────────────────────────────
    user_id = stm.get_user_id()
    if user_id and done:
        try:
            from rag_pipeline import get_rag_pipeline
            rag_files = [
                {"file_id": s.get("file_id"), "filename": s.get("filename"),
                 "textContent": s.get("raw_text", "")}
                for s in done if s.get("raw_text")
            ]
            rag_result = get_rag_pipeline().index_multiple_files(
                doc_id=document_id, user_id=user_id,
                files=rag_files, doc_type=doc_type)
            _step("observe", f"RAG indexé: {rag_result.get('total_chunks', 0)} chunks")
        except Exception as e:
            _step("observe", f"RAG index failed (non bloquant): {e}")
            
    signature_result = {"needs_signature": False, "auto_signed": False}
    _SIGNATURE_TYPES = {"Contrat de travail", "Juridique", "Contrat", "Autre"}

    if doc_type in _SIGNATURE_TYPES and done:
        try:
            from agents.signature_agent import SignatureAgent
            full_text = "\n\n".join(s.get("raw_text", "") for s in done)
            signature_result = SignatureAgent().check_and_auto_sign(
                document_text = full_text,
                document_type = doc_type,
                filename      = done[0].get("filename", ""),
                user_id       = user_id or stm.get_user_id(),
            )
            _step("observe",
                f"SignatureAgent: needs={signature_result['needs_signature']} | "
                f"auto_signed={signature_result['auto_signed']}")
        except Exception as e:
            _step("observe", f"SignatureAgent non-bloquant: {e}")
            
    # ── Extraire le texte CV pour le scoring ──────────────────────────────────
    from agents.task_agent import RH_DOCUMENT_TYPES, SCORING_DOCUMENT_TYPES

    cv_text_for_scoring = ""
    if doc_type in RH_DOCUMENT_TYPES:
        cv_files = [s for s in done
                    if s.get("document_type") in ("CV", "Lettre de motivation")]
        cv_text_for_scoring = "\n\n".join(
            s.get("raw_text", "") for s in cv_files if s.get("raw_text"))
        if not cv_text_for_scoring.strip():
            cv_text_for_scoring = "\n\n".join(
                s.get("raw_text", "") for s in done if s.get("raw_text"))

    # ── 4 : TaskAgent — tâches MiniGED + statut initial ──────────────────────
    tasks_created  = 0
    tasks_list     = []
    task_result    = {"skipped": True, "tasks_created": 0}

    if doc_type in RH_DOCUMENT_TYPES:
        try:
            from agents.task_agent import TaskAgent, CANDIDATE_STATUS_AFTER_ANALYSIS
            ta = TaskAgent()

            _step("action", f"TaskAgent → tâches MiniGED | doc_id={document_id}")
            task_r = ta.create_tasks_for_document(document_id, doc_type, consolidated)
            tasks_created = task_r.get("tasks_created", 0)
            tasks_list    = task_r.get("tasks", [])
            _step("observe", f"TaskAgent : {tasks_created} tâche(s) créée(s)")

            notes_statut = f"[IA] Type détecté : {doc_type}"
            if consolidated:
                notes_statut += f"\n\nRésumé IA :\n{consolidated[:500]}"
            ta.update_candidate_status(
                document_id, doc_type,
                CANDIDATE_STATUS_AFTER_ANALYSIS,
                notes_statut,
            )
            _step("observe", f"Statut candidat → {CANDIDATE_STATUS_AFTER_ANALYSIS}")
            task_result = {"skipped": False, "tasks_created": tasks_created, "tasks": tasks_list}
        except Exception as e:
            _step("observe", f"TaskAgent (tâches+statut) failed: {e}")
            import traceback; _step("observe", traceback.format_exc()[:300])
    else:
        _step("observe", f"Skip TaskAgent : type '{doc_type}' non RH")

    # ── 5 : ScoreAgent — score CV (si document scorable) ─────────────────────
    score_result   = {"skipped": True}
    candidate_info = {}   # {name, email, position, candidate_id}

    if doc_type in SCORING_DOCUMENT_TYPES and cv_text_for_scoring.strip():
        try:
            from mcp_client import call_mcp_tool
            from core.constants import MCP_LOCAL
            raw  = call_mcp_tool(MCP_LOCAL["miniged"], "get_candidate",
                                  {"document_id": int(document_id)})
            cand = json.loads(raw) if isinstance(raw, str) else (raw or {})
            if "error" not in cand:
                candidate_info = {
                    "candidate_id": cand.get("candidateId", 0),
                    "name":         cand.get("name", ""),
                    "email":        cand.get("email", ""),
                    "position":     cand.get("position", ""),
                }
                _step("observe",
                    f"Candidat : {candidate_info['name']} | "
                    f"poste : {candidate_info['position']}")
            else:
                _step("observe", f"get_candidate: {cand.get('error')}")
        except Exception as e:
            _step("observe", f"get_candidate failed: {e}")

        position = candidate_info.get("position", "")
        name     = candidate_info.get("name", "")

        if position and name:
            _step("action",
                f"ScoreAgent → '{name}' | poste='{position}' | "
                f"texte={len(cv_text_for_scoring)} car.")
            try:
                from agents.score_agent import ScoreAgent
                score_result = ScoreAgent().run(
                    candidate_name = name,
                    position       = position,
                    cv_text        = cv_text_for_scoring,
                    document_id    = document_id,
                )
                score_result.update(candidate_info)   # enrichit avec id/email/position
                _step("observe",
                    f"ScoreAgent : score={score_result.get('score')}/100 | "
                    f"rec={score_result.get('recommendation')}")
            except Exception as e:
                _step("observe", f"ScoreAgent failed: {e}")
                import traceback; _step("observe", traceback.format_exc()[:300])
                score_result = {"skipped": True, "error": str(e)}
        else:
            _step("observe", "ScoreAgent skip : nom ou poste absent")
    else:
        _step("observe",
            f"ScoreAgent skip : doc_type='{doc_type}' non scorable "
            f"ou texte CV vide")

    # ── 6 : AceDecisionAgent — phase + confiance + suggestion ────────────────
    ace_decision   = None
    ace_suggestion = None

    if score_result and not score_result.get("skipped"):
        score          = score_result.get("score", 0)
        recommendation = score_result.get("recommendation", "")
        position       = score_result.get("position", "")

        if position:
            _step("action",
                f"AceDecisionAgent → score={score} | rec={recommendation}")
            try:
                from agents.ace_decision_agent import AceDecisionAgent
                ace_decision = AceDecisionAgent().run(
                    score          = score,
                    recommendation = recommendation,
                    position       = position,
                )
                ace_suggestion = ace_decision.get("suggestion")
                score_result["ace_phase"]      = ace_decision.get("phase")
                score_result["ace_confidence"] = ace_decision.get("ace_confidence")
                score_result["ace_suggestion"] = ace_suggestion
                score_result["ace_auto_acted"] = ace_decision.get("auto_act", False)
                _step("observe",
                    f"[ACE] Phase={ace_decision.get('phase')} | "
                    f"confiance={ace_decision.get('ace_confidence', 0):.0%} | "
                    f"auto_act={ace_decision.get('auto_act')}")
            except Exception as _ace_err:
                _step("observe", f"[ACE] AceDecisionAgent non-bloquant: {_ace_err}")

        # ── Ancien hook ace_router (proactif, non bloquant) ───────────────────
        try:
            from ace.ace_router import ace_post_score, ace_inject_into_trace
            _cid = int(score_result.get("candidate_id") or 0)
            if position:
                ace_proactive = ace_post_score(score_result, _cid, position, {})
                score_result  = ace_inject_into_trace(score_result, ace_proactive)
                if ace_proactive and ace_proactive.get("should_suggest"):
                    _step("observe",
                        f"[ACE] Suggestion proactive | "
                        f"bullet={ace_proactive.get('bullet_id')} | "
                        f"helpful={ace_proactive.get('helpful_count')}x")
        except Exception as _e:
            _step("observe", f"[ACE] ace_post_score non-bloquant: {_e}")

    # ── 7 : Exécution auto_act (Phase 4 uniquement) ───────────────────────────
    #
    #  Si ACE est autonome (phase 4, cas clair, confiance ≥ 60 %) :
    #    - "Entretien"    → TaskAgent.create_calendar_event() + EmailAgent
    #    - "ListeAttente" → TaskAgent.update_candidate_status()
    #    - "Refus"        → TaskAgent.update_candidate_status() + EmailAgent
    #
    calendar_result = {}

    if ace_decision and ace_decision.get("auto_act"):
        score          = score_result.get("score", 0)
        recommendation = score_result.get("recommendation", "")
        candidate_name  = score_result.get("name", "")
        candidate_email = score_result.get("email", "")
        position        = score_result.get("position", "")
        doc_type_local  = doc_type   # déjà calculé plus haut

        _step("action",
            f"[ACE AUTO] Phase 4 | {recommendation} | "
            f"score={score} | candidat={candidate_name}")

        try:
            from agents.task_agent import TaskAgent
            from agents.email_agent import EmailAgent
            ta = TaskAgent()

            if recommendation == "Entretien" and candidate_email:
                # Statut
                ta.update_candidate_status(
                    document_id, doc_type_local, "Entretien",
                    f"[ACE AUTO] Entretien planifié | score={score}/100")

                # Calendar (TaskAgent)
                calendar_result = ta.create_calendar_event(
                    candidate_name  = candidate_name,
                    candidate_email = candidate_email,
                    position        = position,
                    document_id     = document_id,
                )
                score_result["calendar_result"] = calendar_result
                _step("observe",
                    f"[ACE AUTO] Calendar "
                    f"{'créé' if calendar_result.get('event_created') else 'non créé'}")

                # Email convocation (EmailAgent)
                er = EmailAgent().send_recruitment_convocation(
                    to             = candidate_email,
                    candidate_name = candidate_name,
                    position       = position,
                    slot_formatted = calendar_result.get("slot_formatted", ""),
                    html_link      = calendar_result.get("html_link", "https://calendar.google.com"),
                    meet_link      = calendar_result.get("meet_link", ""),
                    strengths      = score_result.get("strengths", []),
                )
                _step("observe",
                    f"[ACE AUTO] Email convocation "
                    f"{'envoyé' if er.get('success') else 'échoué'} → {candidate_email}")

            elif recommendation == "ListeAttente":
                ta.update_candidate_status(
                    document_id, doc_type_local, "ListeAttente",
                    f"[ACE AUTO] Mis en liste d'attente | score={score}/100")
                _step("observe", "[ACE AUTO] Statut → ListeAttente")

            elif recommendation in ("Refus", "Refuse"):
                ta.update_candidate_status(
                    document_id, doc_type_local, "Refuse",
                    f"[ACE AUTO] Refus automatique | score={score}/100")
                if candidate_email:
                    er = EmailAgent().send_simple_refusal_email(
                        to             = candidate_email,
                        candidate_name = candidate_name,
                        position       = position,
                    )
                    _step("observe",
                        f"[ACE AUTO] Email refus "
                        f"{'envoyé' if er.get('success') else 'échoué'} → {candidate_email}")

            if ace_suggestion:
                ace_suggestion["auto_acted"] = True
            score_result["ace_auto_acted"] = True

            # ── Apprentissage continu : ACE enregistre sa propre décision ────
            # En Phase 4, le RH ne valide plus → personne ne déclenche le pipeline
            # Generator→Reflector→Curator. On l'appelle ici directement avec des
            # notes RH synthétiques construites depuis les vraies données du score
            # (strengths, gaps, justifications playbook) — même format que les
            # notes saisies manuellement par un RH en Phase 1-3.
            try:
                from ace.generator import observe_override
                from ace.reflector import reflect_on_trajectory
                from ace.curator   import run_curation

                ace_confidence_val = ace_decision.get("ace_confidence", 0.0)
                strengths = score_result.get("strengths", []) or []
                gaps      = score_result.get("gaps",      []) or []
                justifs   = (ace_suggestion or {}).get("justifications", []) or []

                auto_rh_notes = []

                # "+" — points forts du candidat (depuis ScoreAgent)
                for s in strengths[:3]:
                    if s and str(s).strip():
                        auto_rh_notes.append({"sign": "+", "text": str(s).strip()})

                # "+" — règles du playbook qui ont confirmé la décision
                for j in justifs:
                    if j.get("sign") == "+" and j.get("text", "").strip():
                        auto_rh_notes.append({
                            "sign": "+",
                            "text": f"[Règle playbook] {j['text'].strip()}",
                        })

                # "-" — gaps identifiés (informatifs)
                for g in gaps[:2]:
                    if g and str(g).strip():
                        auto_rh_notes.append({"sign": "-", "text": str(g).strip()})

                # Fallback si aucune donnée riche disponible
                if not auto_rh_notes:
                    label = {
                        "Entretien":    "Profil solide, score élevé",
                        "ListeAttente": "Profil correct, score intermédiaire",
                        "Refus":        "Profil insuffisant, score bas",
                    }.get(recommendation, f"Score {score}/100")
                    auto_rh_notes.append({"sign": "+", "text": label})

                auto_note = (
                    f"[ACE AUTO Phase 4] {recommendation} | "
                    f"score={score}/100 | confiance={ace_confidence_val:.0%} | "
                    f"poste='{position}' | "
                    f"{len(strengths)} points forts, {len(gaps)} gaps identifiés"
                )

                _gen = observe_override(
                    candidate_id      = int(score_result.get("candidate_id") or 0),
                    candidate_name    = candidate_name,
                    position          = position,
                    ai_score          = score,
                    ai_recommendation = recommendation,
                    ai_status         = recommendation,
                    human_status      = recommendation,
                    user_id           = "ace_auto",
                    notes             = auto_note,
                    rh_notes          = auto_rh_notes,
                )
                _ref = reflect_on_trajectory(_gen, max_rounds=1)
                _cur = run_curation(_ref.get("refined_deltas", []),
                                    source="ace_auto_act")
                _step("observe",
                    f"[ACE LEARN] Apprentissage auto_act OK | "
                    f"{len(auto_rh_notes)} note(s) RH synthétiques | "
                    f"added={_cur.get('summary', {}).get('added', [])} | "
                    f"updated={_cur.get('summary', {}).get('updated', [])}")
            except Exception as _learn_err:
                _step("observe",
                    f"[ACE LEARN] Pipeline apprentissage non-bloquant: {_learn_err}")

        except Exception as _auto_err:
            _step("observe", f"[ACE AUTO] Exécution échouée (non bloquant): {_auto_err}")
            import traceback; _step("observe", traceback.format_exc()[:300])
    else:
        # Pas d'auto_act : mettre à jour le statut candidat avec le score
        if score_result and not score_result.get("skipped"):
            try:
                from agents.task_agent import TaskAgent
                TaskAgent().update_candidate_status(
                    document_id, doc_type, "ATraiter",
                    f"[Score IA] {score_result.get('score', 0)}/100 — "
                    f"{score_result.get('recommendation', '')} | En attente décision RH",
                )
                _step("observe", "Statut candidat → ATraiter (en attente RH)")
            except Exception as e:
                _step("observe", f"update_candidate_status post-score non-bloquant: {e}")

    # ── 8a : Persister AiScore dans .NET ─────────────────────────────────────
    if score_result and not score_result.get("skipped"):
        _cid   = score_result.get("candidate_id", 0)
        _score = score_result.get("score", 0)
        _rec   = score_result.get("recommendation", "")
        if _cid and _score:
            try:
                import requests as _req
                _req.patch(
                    f"http://localhost:5092/api/recruitment/application/{_cid}/ai-score",
                    json={"aiScore": _score, "aiRecommendation": _rec},
                    timeout=5,
                )
                _step("observe", f"[ACE] AiScore={_score} persisté → candidate_id={_cid}")
            except Exception as _e:
                _step("observe", f"[ACE] Persist AiScore non-bloquant: {_e}")

    # ── 8b : Persister résumé + métadonnées en DB .NET ───────────────────────
    try:
        import requests as _save_req
        _save_req.patch(
            f"http://localhost:5092/api/dashboard/document/{document_id}/ai",
            json={
                "summary":      consolidated,
                "documentType": doc_type,
                "fileSummaries": [
                    {
                        "fileId":     s.get("file_id"),
                        "filename":   s.get("filename"),
                        "aiFileType": s.get("document_type"),
                        "aiSummary":  s.get("summary"),
                    }
                    for s in done if s.get("file_id")
                ],
            },
            timeout=8,
        )
        _step("observe", f"[AI] Résultats persistés en DB .NET | doc={document_id}")
    except Exception as _e:
        _step("observe", f"[AI] Persist DB non-bloquant: {_e}")

    # ── 9 : Action email en attente (confirmation RH) ─────────────────────────
    #
    #  Seulement si ACE n'a pas agi automatiquement.
    #  Le payload contient la suggestion ACE pour l'afficher dans la banner.
    #
    email_action_id = ""

    if score_result and not score_result.get("skipped") \
            and not score_result.get("ace_auto_acted"):
        candidate_email = score_result.get("email", "")
        if candidate_email:
            # Pré-générer le corps de l'email pour affichage dans ScoreValidationBanner.
            # EmailAgent génère le vrai contenu LLM ici — la bannière affichera
            # exactement ce qui sera envoyé au candidat, pas un template local.
            email_body_preview    = ""
            email_subject_preview = ""
            try:
                from agents.email_agent import EmailAgent as _EA
                _ea      = _EA()
                _subject, _body = _ea._write_score_email(
                    candidate_name = score_result.get("name", ""),
                    position       = score_result.get("position", ""),
                    recommendation = score_result.get("recommendation", ""),
                    score          = score_result.get("score", 0),
                    strengths      = score_result.get("strengths", []),
                    gaps           = score_result.get("gaps", []),
                    summary        = score_result.get("summary", ""),
                    slot_formatted = calendar_result.get("slot_formatted", ""),
                    meet_link      = calendar_result.get("meet_link", ""),
                    event_link     = calendar_result.get("html_link", ""),
                )
                email_body_preview    = _body
                email_subject_preview = _subject
                _step("observe", f"[EMAIL PREVIEW] Corps pré-généré ({len(_body)} car.)")
            except Exception as _pe:
                _step("observe", f"[EMAIL PREVIEW] Génération non-bloquante: {_pe}")

            score_action_id = str(uuid.uuid4())
            stm.add_pending_action(score_action_id, "send_score_email", {
                "to":             candidate_email,
                "candidate_name": score_result.get("name", ""),
                "position":       score_result.get("position", ""),
                "score":          score_result.get("score", 0),
                "recommendation": score_result.get("recommendation", ""),
                "strengths":      score_result.get("strengths", []),
                "gaps":           score_result.get("gaps", []),
                "summary":        score_result.get("summary", ""),
                "slot_formatted": calendar_result.get("slot_formatted", ""),
                "meet_link":      calendar_result.get("meet_link", ""),
                "event_link":     calendar_result.get("html_link", ""),
                "ace_suggestion": ace_suggestion,
                "document_id":    document_id,
                "candidate_id":   score_result.get("candidate_id", 0),
                "body_sent":      email_body_preview,
                "subject_sent":   email_subject_preview,
            })
            email_action_id = score_action_id

    # ── Persister la trace ReAct sur disque ───────────────────────────────────
    try:
        import pathlib
        trace_dir = pathlib.Path("/tmp/ace_traces")
        trace_dir.mkdir(parents=True, exist_ok=True)
        trace_path = trace_dir / f"trace_{document_id}.json"
        processing_ms = int((_time.time() - _t0) * 1000)
        trace_data = {"steps": list(_trace), "processing_ms": processing_ms}
        trace_path.write_text(
            json.dumps(trace_data, ensure_ascii=False),
            encoding="utf-8",
        )
        _step("observe",
            f"[TRACE] Trace persistée ({len(_trace)} étapes, {processing_ms}ms) → {trace_path}")
    except Exception as _te:
        _step("observe", f"[TRACE] Persist trace non-bloquant: {_te}")

    return {
        "document_id":     document_id,
        "document_type":   doc_type,
        "file_count":      len(files_data),
        "summaries":       summaries,
        "consolidated":    consolidated,
        "signature_result": signature_result,
        "task_result":     task_result,
        "email_action_id": email_action_id,
        "score_result":    score_result,
        "ace_decision":    ace_decision,
        "ace_suggestion":  ace_suggestion,
        "react_trace":     list(_trace),
        
    }


# ── Décision recrutement (Accepte / Refuse) ───────────────────────────────────

def execute_recruitment_decision(
    candidate_id: int,
    document_id:  str,
    decision:     str,
    notes:        str = "",
) -> dict:
    global _trace, _t0
    _trace = []
    _t0 = _time.time()

    if decision not in ("Accepte", "Refuse"):
        return {"success": False, "error": f"Décision invalide : '{decision}'"}

    from mcp_client     import call_mcp_tool
    from core.constants import MCP_LOCAL

    _step("action", f"execute_recruitment_decision | {decision} | candidate_id={candidate_id}")

    # ── 1. Mettre à jour le statut via MCP ────────────────────────────────────
    try:
        raw = call_mcp_tool(
            MCP_LOCAL["miniged"], "update_candidate_status",
            {
                "candidate_id": candidate_id,
                "document_id":  int(document_id) if document_id else 0,
                "status":       decision,
                "notes":        notes or f"[RH] Décision post-entretien : {decision}",
            },
        )
        status_result = json.loads(raw) if isinstance(raw, str) else (raw or {})
        if not status_result.get("success"):
            err = status_result.get("error", "inconnu")
            _step("observe", f"update_candidate_status failed : {err}")
            return {"success": False, "error": f"Mise à jour statut échouée : {err}"}
        _step("observe",
            f"Statut : {status_result.get('oldStatus')} → {status_result.get('newStatus')}")
    except Exception as e:
        _step("observe", f"MCP update_candidate_status exception : {e}")
        return {"success": False, "error": str(e)}

    old_status = status_result.get("oldStatus", "")
    position   = status_result.get("position", "")

    # ── 2. Notifier ACE de la décision RH ─────────────────────────────────────
    ai_score = 0
    ai_rec   = old_status
    try:
        import requests as _ace_req
        r = _ace_req.get(
            f"http://localhost:5092/api/recruitment/application/{candidate_id}",
            timeout=5,
        )
        if r.status_code == 200:
            cand_data = r.json()
            ai_score  = cand_data.get("aiScore") or 0
            ai_rec    = cand_data.get("aiRecommendation") or old_status
            if not position:
                position = cand_data.get("position", "")
    except Exception:
        pass

    try:
        import requests as _ace_req
        _ace_req.post(
            "http://localhost:8000/ace/override",
            json={
                "candidate_id":      candidate_id,
                "candidate_name":    status_result.get("name", ""),
                "position":          position,
                "ai_score":          ai_score,
                "ai_recommendation": ai_rec,
                "ai_status":         old_status,
                "human_status":      decision,
                "user_id":           "rh_decision_button",
                "notes":             notes or f"Décision post-entretien : {decision}",
            },
            timeout=10,
        )
        _step("observe",
            f"[ACE] Override notifié | {old_status}→{decision} | "
            f"score={ai_score} | pos='{position}'")
    except Exception as _e:
        _step("observe", f"[ACE] Override non-bloquant : {_e}")

    # ── 3. Récupérer les infos candidat pour l'email ───────────────────────────
    candidate_name  = status_result.get("name", "")
    candidate_email = ""

    try:
        raw2 = call_mcp_tool(MCP_LOCAL["miniged"], "get_candidate",
                              {"candidate_id": candidate_id})
        cand            = json.loads(raw2) if isinstance(raw2, str) else (raw2 or {})
        candidate_email = cand.get("email", "")
        candidate_name  = cand.get("name",  candidate_name)
        position        = cand.get("position", position)
        ai_score        = cand.get("aiScore", 0) or 0
        ai_rec          = cand.get("aiRecommendation", "") or ""
        _step("observe",
            f"Candidat : {candidate_name} | email : {candidate_email} | poste : {position}")
    except Exception as e:
        _step("observe", f"get_candidate failed : {e}")

    # ── 4. Envoyer l'email de décision via EmailAgent ─────────────────────────
    email_sent  = False
    email_error = ""

    if not candidate_email:
        email_error = "Email candidat absent"
        _step("observe", email_error)
    else:
        _step("action", f"EmailAgent.send_decision_email → {candidate_email}")
        try:
            from agents.email_agent import EmailAgent
            er = EmailAgent().send_decision_email(
                to             = candidate_email,
                candidate_name = candidate_name,
                position       = position,
                decision       = decision,
            )
            email_sent  = er.get("success", False)
            email_error = er.get("error", "")
            _step("observe",
                f"Email décision {'envoyé' if email_sent else 'échoué'} → {candidate_email}"
                + (f" | {email_error}" if email_error else ""))
        except Exception as e:
            email_error = str(e)
            _step("observe", f"EmailAgent exception : {e}")

    return {
        "success":        True,
        "candidate_id":   candidate_id,
        "new_status":     decision,
        "candidate_name": candidate_name,
        "email_sent":     email_sent,
        "email_to":       candidate_email,
        "email_error":    email_error,
        "react_trace":    list(_trace),
    }


def execute_schedule_interview(
    candidate_id: int,
    document_id:  str,
    notes:        str = "",
    rh_notes:     list = None,
) -> dict:
    """
    Planifie un entretien manuellement depuis l'UI RH.
    1. Récupère les infos candidat
    2. Met à jour le statut → Entretien  (TaskAgent)
    3. Crée l'event Google Calendar       (TaskAgent)
    4. Envoie l'email d'invitation        (EmailAgent)
    5. Notifie ACE                        (ace/override)
    """
    global _trace, _t0
    _trace = []
    _t0 = _time.time()
    _step("action", f"execute_schedule_interview | candidate_id={candidate_id}")

    from mcp_client import call_mcp_tool
    from core.constants import MCP_LOCAL

    # 1. Récupérer les infos candidat
    try:
        raw  = call_mcp_tool(MCP_LOCAL["miniged"], "get_candidate",
                              {"candidate_id": candidate_id})
        cand = json.loads(raw) if isinstance(raw, str) else (raw or {})
        name     = cand.get("name", "")
        email    = cand.get("email", "")
        position = cand.get("position", "")
        ai_score = cand.get("aiScore", 0) or 0
        ai_rec   = cand.get("aiRecommendation", "") or ""
        _step("observe", f"Candidat : {name} | email : {email} | poste : {position}")
    except Exception as e:
        return {"success": False, "error": f"get_candidate failed: {e}"}

    # 2. Mettre à jour le statut → Entretien  (TaskAgent)
    try:
        from agents.task_agent import TaskAgent
        ta = TaskAgent()
        ta.update_candidate_status(
            document_id, "CV", "Entretien",
            notes or "[RH] Entretien planifié manuellement depuis l'UI",
        )
        _step("observe", "Statut → Entretien")
    except Exception as e:
        _step("observe", f"update_candidate_status failed: {e}")
        ta = None

    # 3. Créer l'événement Calendar  (TaskAgent)
    cal = {"event_created": False, "email_sent": False}
    try:
        if ta is None:
            from agents.task_agent import TaskAgent
            ta = TaskAgent()
        cal = ta.create_calendar_event(
            candidate_name  = name,
            candidate_email = email,
            position        = position,
            document_id     = document_id,
        )
        _step("observe",
            f"Calendar {'créé' if cal.get('event_created') else 'non créé'}")
    except Exception as e:
        _step("observe", f"Calendar failed: {e}")
        cal = {"event_created": False, "slot_formatted": "", "meet_link": "",
               "html_link": "", "calendar_error": str(e)}

    # 4. Envoyer l'email d'invitation  (EmailAgent)
    email_sent  = False
    email_error = ""
    if email:
        try:
            from agents.email_agent import EmailAgent
            er = EmailAgent().send_recruitment_convocation(
                to             = email,
                candidate_name = name,
                position       = position,
                slot_formatted = cal.get("slot_formatted", ""),
                html_link      = cal.get("html_link", "https://calendar.google.com"),
                meet_link      = cal.get("meet_link", ""),
                strengths      = [],
            )
            email_sent  = er.get("success", False)
            email_error = er.get("error", "")
            _step("observe",
                f"Email convocation {'envoyé' if email_sent else 'échoué'} → {email}")
        except Exception as e:
            email_error = str(e)
            _step("observe", f"EmailAgent failed: {e}")
    else:
        email_error = "Email candidat absent"

    # 5. Notifier ACE
    try:
        import requests as _r
        _r.post("http://localhost:8000/ace/override", json={
            "candidate_id":      candidate_id,
            "candidate_name":    name,
            "position":          position,
            "ai_score":          ai_score,
            "ai_recommendation": ai_rec or "ATraiter",
            "ai_status":         ai_rec or "ATraiter",
            "human_status":      "Entretien",
            "user_id":           "rh_schedule_manual",
            "notes":             notes or "RH a planifié l'entretien manuellement",
            "rh_notes":          rh_notes or [],
        }, timeout=8)
        _step("observe", "[ACE] Override notifié | ATraiter→Entretien (validation RH)")
    except Exception as e:
        _step("observe", f"[ACE] Non-bloquant : {e}")

    return {
        "success":          True,
        "candidate_id":     candidate_id,
        "new_status":       "Entretien",
        "calendar_created": cal.get("event_created", False),
        "slot_formatted":   cal.get("slot_formatted", ""),
        "meet_link":        cal.get("meet_link", ""),
        "email_sent":       email_sent,
        "email_error":      email_error,
        "react_trace":      list(_trace),
    }


def execute_simple_refusal(
    candidate_id: int,
    document_id:  str,
    notes:        str = "",
    rh_notes:     list = None,
) -> dict:
    global _trace, _t0
    _trace = []
    _t0 = _time.time()
    _step("action", f"execute_simple_refusal | candidate_id={candidate_id}")

    from mcp_client import call_mcp_tool
    from core.constants import MCP_LOCAL

    # 1. Récupérer les infos candidat
    try:
        raw  = call_mcp_tool(MCP_LOCAL["miniged"], "get_candidate",
                              {"candidate_id": candidate_id})
        cand = json.loads(raw) if isinstance(raw, str) else (raw or {})
        name     = cand.get("name", "")
        email    = cand.get("email", "")
        position = cand.get("position", "")
        ai_score = cand.get("aiScore", 0) or 0
        _step("observe", f"Candidat : {name} | email : {email}")
    except Exception as e:
        return {"success": False, "error": str(e)}

    # 2. Mettre à jour le statut → Refuse  (TaskAgent)
    try:
        from agents.task_agent import TaskAgent
        TaskAgent().update_candidate_status(
            document_id, "CV", "Refuse",
            notes or "[RH] Candidature non retenue (avant entretien)",
        )
        _step("observe", "Statut → Refuse")
    except Exception as e:
        _step("observe", f"update_status failed: {e}")

    # 3. Email simple "candidature non retenue"  (EmailAgent)
    email_sent  = False
    email_error = ""
    if email:
        try:
            from agents.email_agent import EmailAgent
            er = EmailAgent().send_simple_refusal_email(
                to=email, candidate_name=name, position=position
            )
            email_sent  = er.get("success", False)
            email_error = er.get("error", "")
            _step("observe",
                f"Email refus simple {'envoyé' if email_sent else 'échoué'} → {email}")
        except Exception as e:
            email_error = str(e)
            _step("observe", f"EmailAgent exception : {e}")
    else:
        email_error = "Email candidat absent"

    # 4. Notifier ACE
    try:
        import requests as _r
        _r.post("http://localhost:8000/ace/override", json={
            "candidate_id":      candidate_id,
            "candidate_name":    name,
            "position":          position,
            "ai_score":          ai_score,
            "ai_recommendation": "ATraiter",
            "ai_status":         "ATraiter",
            "human_status":      "Refuse",
            "user_id":           "rh_simple_refusal",
            "notes":             notes or "Refus avant entretien",
            "rh_notes":          rh_notes or [],
        }, timeout=8)
        _step("observe", "[ACE] Override notifié | ATraiter→Refuse")
    except Exception as e:
        _step("observe", f"[ACE] Non-bloquant : {e}")

    return {
        "success":     True,
        "candidate_id": candidate_id,
        "new_status":  "Refuse",
        "email_sent":  email_sent,
        "email_to":    email,
        "email_error": email_error,
        "react_trace": list(_trace),
    }


# ── Exécution d'une action en attente ─────────────────────────────────────────

def execute_pending(
    action_id:        str,
    confirmed:        bool,
    payload_override: dict | None = None,
) -> dict:
    stm    = get_short_term_memory()
    action = stm.get_pending_action(action_id)
    if not action:
        return {"error": f"action_id '{action_id}' introuvable"}

    if not confirmed:
        stm.update_action_status(action_id, "rejected")
        return {"action_id": action_id, "status": "rejected"}

    stm.update_action_status(action_id, "executing")
    payload = {**action["payload"], **(payload_override or {})}

    try:
        a_type = action["action_type"]

        if a_type == "sign":
            result = run_sign(**payload)

        elif a_type == "send_email":
            from agents.email_agent import EmailAgent
            er = EmailAgent().run(
                mode          = "report",
                to            = payload.get("to", ""),
                subject       = payload.get("subject", ""),
                body          = payload.get("body", ""),
                filename      = payload.get("filename", ""),
                document_type = payload.get("document_type", ""),
                summary       = payload.get("summary", ""),
                extraction    = payload.get("extraction", ""),
            )
            result = {
                "success":        er.get("success", False),
                "email_to":       payload.get("to", ""),
                "has_attachment": False,
                "error":          er.get("error", ""),
            }

        elif a_type == "send_email_with_attachment":
            from agents.email_agent import EmailAgent
            to           = payload.get("to", "")
            subject      = payload.get("subject", "[GED] Document")
            body         = payload.get("body", "")
            filename_att = payload.get("filename", "document.pdf")
            pdf_b64      = payload.get("pdf_base64", "")
            has_att      = payload.get("has_attachment", False)

            _step("observe",
                f"send_email_with_attachment → to={to} | "
                f"fichier={filename_att} | has_pdf={bool(pdf_b64)} | has_att={has_att}")

            er = EmailAgent().run(
                mode       = "attachment",
                to         = to,
                subject    = subject,
                body       = body,
                filename   = filename_att,
                pdf_base64 = pdf_b64 if has_att else "",
            )
            result = {
                "success":        er.get("success", False),
                "email_to":       to,
                "has_attachment": er.get("has_attachment", bool(pdf_b64 and has_att)),
                "filename":       filename_att,
                "error":          er.get("error", ""),
            }
            _step("observe",
                f"EmailAgent résultat : success={result['success']} | "
                f"attachment={result['has_attachment']} | "
                f"error={result['error'][:80] if result['error'] else 'OK'}")

        elif a_type == "send_score_email":
            from agents.email_agent import EmailAgent
            # Si le RH a édité le corps dans la bannière, payload_override contient
            # body et subject — on les utilise directement sans re-générer via LLM.
            body_override    = payload.get("body", "").strip()
            subject_override = payload.get("subject", "").strip()

            if body_override:
                # Corps édité par le RH → envoi direct sans LLM
                _to      = payload.get("to", "")
                _subject = subject_override or f"Suite de votre candidature — {payload.get('position', '')}"
                er = EmailAgent()._dispatch(_to, _subject, body_override)
                er["body_sent"]    = body_override
                er["subject_sent"] = _subject
            else:
                # Corps non fourni → génération LLM normale
                er = EmailAgent().send_score_email(
                    to             = payload.get("to", ""),
                    candidate_name = payload.get("candidate_name", ""),
                    position       = payload.get("position", ""),
                    recommendation = payload.get("recommendation", ""),
                    score          = payload.get("score", 0),
                    strengths      = payload.get("strengths", []),
                    gaps           = payload.get("gaps", []),
                    summary        = payload.get("summary", ""),
                    slot_formatted = payload.get("slot_formatted", ""),
                    meet_link      = payload.get("meet_link", ""),
                    event_link     = payload.get("event_link", ""),
                )

            recommendation = payload.get("recommendation", "")
            document_id    = payload.get("document_id", "")
            status_map     = {
                "Entretien":    "Entretien",
                "ListeAttente": "ListeAttente",
                "Refus":        "Refuse",
                "Refuse":       "Refuse",
            }
            new_status = status_map.get(recommendation)

            if new_status and document_id:
                try:
                    from mcp_client import call_mcp_tool
                    from core.constants import MCP_LOCAL
                    call_mcp_tool(MCP_LOCAL["miniged"], "update_candidate_status", {
                        "document_id": int(document_id),
                        "status":      new_status,
                        "notes":       (
                            f"[RH] Décision confirmée depuis la banner | "
                            f"score={payload.get('score', 0)}/100 | "
                            f"recommandation ACE : {recommendation}"
                        ),
                    })
                except Exception as _e:
                    print(f"[execute_pending] update_status non-bloquant: {_e}", file=sys.stderr)

            result = {
                "success":        er.get("success", False),
                "email_to":       payload.get("to", ""),
                "recommendation": recommendation,
                "score":          payload.get("score", 0),
                "new_status":     new_status,
                "has_attachment": False,
                "error":          er.get("error", ""),
            }

        else:
            result = {"error": f"Type d'action inconnu : '{a_type}'"}

        stm.update_action_status(action_id, "done")
        result["action_id"] = action_id
        return result

    except Exception as e:
        stm.update_action_status(action_id, "error")
        return {"action_id": action_id, "status": "error", "error": str(e)}


# ── Signature / Email signé ───────────────────────────────────────────────────
def run_sign(pdf_base64: str, signature_png: str, signer_name: str = "Signataire",
             page: int = 0, x: float = 80.0, y: float = 60.0,
             width: float = 220.0, height: float = 70.0, filename: str = "",
             user_id: str = "", document_type: str = "") -> dict:
    """
    Point d'entrée unique de signature.
    Délègue intégralement au SignatureAgent (détection + apprentissage + apposition).
    """
    stm = get_short_term_memory()
    if not filename: filename = stm.get_last_filename()
    if not user_id:  user_id  = stm.get_user_id()
    from agents.signature_agent import SignatureAgent
    return SignatureAgent().run(
        pdf_base64    = pdf_base64,
        signature_png = signature_png,
        signer_name   = signer_name,
        filename      = filename,
        page          = page,
        x             = x,
        y             = y,
        width         = width,
        height        = height,
        user_id       = user_id,
        document_type = document_type,
    )
 
 
def run_send_signed(to: str, subject: str, body: str,
                    pdf_base64: str, filename: str = "document_signe.pdf") -> dict:
    from agents.email_agent import EmailAgent
    return EmailAgent().run(
        mode="signed_pdf", to=to, subject=subject,
        body=body, pdf_base64=pdf_base64, filename=filename,
    )
# ── Chat ──────────────────────────────────────────────────────────────────────

def run_chat(message: str, document_type: str = "", filename: str = "",
             document_id: str = "", history: Optional[list] = None,
             miniged_token: str = "", skills: list = None,
             conv_id: str = "", user_id: str = "") -> dict:
    stm = get_short_term_memory()

    if user_id:
        stm.set_user_id(user_id)
    if conv_id:
        stm.set_conv_id(conv_id)

    document_text = stm.get_document_text(filename)
    if not filename:
        filename = stm.get_last_filename()

    if conv_id and not history:
        try:
            from memory.long_term import get_long_term_memory
            history = get_long_term_memory().get_conversation_as_history(conv_id, last_n=10)
            _step("observe", f"Historique chargé: {len(history)} messages pour conv={conv_id}")
        except Exception as e:
            _step("observe", f"Chargement historique failed: {e}")
            history = []

    from agents.assistant_agent import AssistantAgent
    result = AssistantAgent().run(
        message=message, document_text=document_text,
        document_type=document_type, filename=filename,
        history=history or [], miniged_token=miniged_token,
        skills=skills or [], user_id=user_id or stm.get_user_id(),
    )
    action_done   = result.get("action_done")
    action_result = result.get("action_result") or {}

    if action_done == "sign_requested":
        from memory.long_term import get_long_term_memory
        ltm    = get_long_term_memory()
        already = ltm.is_document_signed(filename) or stm.is_signed(filename)
        if already:
            sig = ltm.is_document_signed(filename) or {}
            result["reply"]       = f"Document déjà signé par {sig.get('signer_name','')}."
            result["action_done"] = "already_signed"
        else:
            action_id = str(uuid.uuid4())
            stm.add_pending_action(action_id, "sign",
                {"pdf_base64": "", "signature_png": "", "signer_name": "Signataire",
                 "filename": filename})
            result["sign_action_id"] = action_id
            result["reply"] = "Demande de signature créée. Confirmez depuis l'interface."

    elif action_done == "email_requested":
        email_to = action_result.get("email_to", "")
        if not email_to:
            result["reply"] = "Adresse email non détectée. Précisez le destinataire."
        else:
            active_id = stm.get_current_miniged_id()
            action_id = str(uuid.uuid4())
            stm.add_pending_action(action_id, "send_email", {
                "to":           email_to,
                "filename":     filename or stm.get_last_filename() or "document",
                "document_id":  active_id or document_id,
                "document_type": document_type or stm.summary().get("current_type", ""),
                "summary":      stm.get_result("summary") or "",
                "extraction":   stm.get_result("extraction") or "",
            })
            result.update({
                "email_action_id": action_id,
                "email_to":        email_to,
                "action_done":     "email_pending_confirm",
                "reply": result.get("reply") or f"Brouillon email prêt pour {email_to}.",
            })

    elif action_done == "summarize":
        if document_text:
            try:
                from agents.summarizer_agent import SummarizerAgent
                sr      = SummarizerAgent().run(text=document_text, filename=filename,
                                                document_type=document_type)
                summary = (sr.get("summary", "") or "").strip()
                result["reply"] = result["summary"] = summary or "Résumé non disponible."
                stm.set_result("summary", result["reply"])
            except Exception as e:
                result["reply"] = f"Résumé impossible : {e}"
        else:
            target_id = document_id or stm.get_current_miniged_id()
            if target_id:
                sr = summarize_document_files(target_id, miniged_token)
                result["reply"] = result["summary"] = sr.get(
                    "consolidated", "Résumé non disponible.")
                stm.set_result("summary", result["reply"])
            else:
                result["reply"] = "Aucun document sélectionné pour le résumé."

    active_conv_id = conv_id or stm.get_conv_id()
    active_user_id = user_id or stm.get_user_id()

    stm.add_chat_message("user", message)
    stm.add_chat_message("assistant", result.get("reply", ""))

    if active_conv_id and active_user_id:
        try:
            from memory.long_term import get_long_term_memory
            ltm = get_long_term_memory()
            ltm.save_conversation_message(active_conv_id, active_user_id, "user", message)
            ltm.save_conversation_message(active_conv_id, active_user_id, "assistant",
                                           result.get("reply", ""))
            conv = ltm.list_conversations(active_user_id, limit=1)
            if not conv or (conv and conv[0]["conv_id"] == active_conv_id
                            and conv[0]["message_count"] <= 2):
                ltm.update_conversation_session(
                    active_conv_id,
                    title=message[:80],
                    doc_context=filename or document_id,
                )
        except Exception as e:
            _step("observe", f"Sauvegarde conversation failed: {e}")

    return result


# ── Utilitaires ───────────────────────────────────────────────────────────────

def list_pending_actions() -> list:
    return get_short_term_memory().list_pending_actions()


def get_reminders(days_ahead: int = 30) -> dict:
    try:
        from services.calendar_service import get_upcoming_reminders
        return get_upcoming_reminders(days_ahead)
    except Exception:
        return {"reminders": [], "count": 0, "urgent": 0}


def start_scheduler() -> bool:
    try:
        from services.folder_scheduler import start_scheduler as _start
        return _start()
    except Exception as e:
        print(f"[Orchestrateur] Scheduler non démarré : {e}", file=sys.stderr)
        return False


def stop_scheduler() -> None:
    try:
        from services.folder_scheduler import stop_scheduler as _stop
        _stop()
    except Exception:
        pass


def _consolidate(done: list) -> str:
    if not done:
        return "Aucun résumé disponible."
    if len(done) == 1:
        return done[0].get("summary", "")
    parts = [f"[{s['filename']}]\n{s.get('summary', '')}" for s in done]
    return "\n\n".join(parts)


def _consolidate_structured(done: list, doc_type: str) -> str:
    if not done:
        return "Aucun résumé disponible."
    if len(done) == 1:
        return done[0].get("summary", "")
    sections = "\n\n".join(
        f"[{s['document_type']}] {s['filename']} :\n{s.get('summary', '')}"
        for s in done)
    try:
        from services.llm_client import generate
        return generate(
            f"Dossier '{doc_type}' : {len(done)} fichiers.\n\n{sections}\n\n"
            "Synthèse structurée par type [entre crochets], 200-250 mots :",
            max_tokens=500, system="Expert RH. Synthèses structurées en français.").strip()
    except Exception:
        return sections