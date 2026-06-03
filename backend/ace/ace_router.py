"""
ace/ace_router.py
─────────────────
Router FastAPI ACE + Middleware pour l'orchestrator.

Endpoints :
  POST /ace/override              → RH corrige → Generator → Reflector → Curator
  GET  /ace/suggest/{cand_id}    → Suggestion proactive depuis le playbook
  GET  /ace/playbook             → Playbook rendu (bullets + stats)
  POST /ace/reflect              → Cycle complet de réflexion manuelle
  GET  /ace/stats                → Dashboard avant/après ACE
  POST /ace/baseline             → Snapshot initial (à faire aujourd'hui)
  PATCH /ace/suggest/{id}/outcome → Feedback RH sur une suggestion
  GET  /ace/overrides            → Log des overrides

Middleware (pour orchestrator.py) :
  ace_pre_score(position, candidate_id)   → contexte playbook
  ace_post_score(result, cand_id, pos, ctx) → suggestion proactive
  ace_inject_into_trace(result, suggestion) → trace ReAct enrichie
"""
from __future__ import annotations

import sys
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

ace_router = APIRouter(prefix="/ace", tags=["ACE — Agentic Context Engineering"])


class BaselineRequest(BaseModel):
    total_candidates: int
    total_overrides:  int   = 0
    avg_ai_score:     float = 0.0
    notes:            str   = ""


class SuggestionOutcome(BaseModel):
    accepted: bool

class OverrideEvent(BaseModel):
    candidate_id:      int
    candidate_name:    str   = ""
    position:          str
    ai_score:          int
    ai_recommendation: str   = "ListeAttente"
    ai_status:         str   = "ListeAttente"
    human_status:      str
    user_id:           str   = "system"
    notes:             str   = ""
    rh_notes:          list  = []   # ← AJOUT : [{"sign": "+", "text": "..."}, ...]
    
# ── PIPELINE COMPLET d'apprentissage: Override → Generator → Reflector → Curator ─────────────
@ace_router.post("/override")
def record_override(event: OverrideEvent):
    """
    Déclenche le pipeline ACE complet sur un override RH.
    Generator → Reflector → Curator → playbook.json mis à jour.
    """
    from ace.generator  import observe_override
    from ace.reflector  import reflect_on_trajectory
    from ace.curator    import run_curation

    # 1. Generator — observation de la trajectoire
    gen = observe_override(
        candidate_id      = event.candidate_id,
        candidate_name    = event.candidate_name,
        position          = event.position,
        ai_score          = event.ai_score,
        ai_recommendation = event.ai_recommendation,
        ai_status         = event.ai_status,
        human_status      = event.human_status,
        user_id           = event.user_id,
        notes             = event.notes,
        rh_notes          = event.rh_notes, 
    )

    # 2. Reflector — raffinement des insights
    ref = reflect_on_trajectory(gen, max_rounds=2)

    # 3. Curator — merge dans le playbook.json
    cur = run_curation(ref.get("refined_deltas", []), source="override_pipeline")

    return {
        "status":   "ok",
        "event_id": gen.get("event_id"),
        "pipeline": {
            "generator": {
                "direction":       gen.get("direction"),
                "is_significant":  gen.get("is_significant"),
                "trajectory":      gen.get("trajectory", "")[:200],
                "helpful_ids":     gen.get("helpful_ids", []),
                "harmful_ids":     gen.get("harmful_ids", []),
                "similar_overrides": gen.get("similar_count", 0),
            },
            "reflector": {
                "rounds_done":     ref.get("rounds_done"),
                "insights":        ref.get("insights", "")[:200],
                "deltas_count":    len(ref.get("refined_deltas", [])),
            },
            "curator": {
                "added":    cur.get("summary", {}).get("added", []),
                "updated":  cur.get("summary", {}).get("updated", []),
                "pruned":   cur.get("pruned", 0),
                "playbook_size": cur.get("playbook_size", 0),
            },
        },
        "traces": {
            "generator": gen.get("trace", []),
            "reflector": ref.get("trace", []),
            "curator":   cur.get("trace", []),
        },
    }


# ── SUGGESTION PROACTIVE ──────────────────────────────────────────────────────
@ace_router.get("/suggest/{candidate_id}")
def get_suggestion(
    candidate_id:      int,
    position:          str = Query(...),
    ai_score:          int = Query(...),
    ai_recommendation: str = Query("ListeAttente"),
):
    """Retourne une suggestion proactive si le playbook a une règle applicable."""
    from ace.curator import suggest_for_candidate
    return suggest_for_candidate(candidate_id, position, ai_score, ai_recommendation)


# ── PLAYBOOK (rendu + stats) ──────────────────────────────────────────────────
@ace_router.get("/playbook")
def get_playbook(rendered: bool = Query(True)):
    """Retourne le playbook — rendu markdown ou JSON brut."""
    from ace.playbook_store import load_playbook, render_playbook, get_stats
    if rendered:
        return {"rendered": render_playbook(), "stats": get_stats()}
    return load_playbook()


# ── RÉFLEXION MANUELLE ────────────────────────────────────────────────────────
@ace_router.post("/reflect")
def trigger_reflection():
    """Lance un cycle complet de réflexion sur les overrides récents non encore traités."""
    from ace.reflector import build_before_after_report
    return build_before_after_report()


# ── STATS / TRACEABILITÉ ──────────────────────────────────────────────────────
@ace_router.get("/stats")
def get_stats():
    """Dashboard complet : playbook, overrides, avant/après ACE."""
    from ace.playbook_store import get_stats as _stats, render_playbook
    from ace.reflector      import build_before_after_report
    return {
        "ace_stats":    _stats(),
        "before_after": build_before_after_report(),
        "playbook_preview": render_playbook()[:800] + "…",
    }


# ── BASELINE ──────────────────────────────────────────────────────────────────
@ace_router.post("/baseline")
def take_baseline(req: BaselineRequest):
    """
    Enregistre l'état AVANT intégration ACE dans le playbook.json.
    À appeler UNE SEULE FOIS — aujourd'hui.
    """
    from ace.playbook_store import load_playbook, save_playbook
    pb = load_playbook()
    if "baseline_snapshot" in pb:
        return {"status": "already_exists", "baseline": pb["baseline_snapshot"]}
    pb["baseline_snapshot"] = {
        "date":             datetime.utcnow().isoformat(),
        "total_candidates": req.total_candidates,
        "total_overrides":  req.total_overrides,
        "avg_ai_score":     req.avg_ai_score,
        "notes":            req.notes,
        "override_rate":    f"{req.total_overrides / max(req.total_candidates, 1):.1%}",
    }
    save_playbook(pb)
    return {"status": "baseline_saved", "baseline": pb["baseline_snapshot"]}


# ── FEEDBACK SUGGESTION ───────────────────────────────────────────────────────
@ace_router.patch("/suggest/{suggestion_id}/outcome")
def update_outcome(suggestion_id: int, req: SuggestionOutcome):
    """Le RH accepte ou refuse une suggestion → feedback vers le playbook."""
    from ace.curator import update_suggestion_outcome
    update_suggestion_outcome(suggestion_id, req.accepted)
    return {"status": "updated", "suggestion_id": suggestion_id, "accepted": req.accepted}


# ── OVERRIDES LOG ─────────────────────────────────────────────────────────────
@ace_router.get("/overrides")
def get_overrides(
    position:  Optional[str] = Query(None),
    direction: Optional[str] = Query(None),
    limit:     int           = Query(50),
):
    """Liste les overrides loggés dans le playbook.json."""
    from ace.playbook_store import get_override_log
    return {
        "overrides": get_override_log(
            position_pattern=position, direction=direction, limit=limit
        )
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MIDDLEWARE (à importer dans orchestrator.py)
# ═══════════════════════════════════════════════════════════════════════════════

def ace_pre_score(position: str, candidate_id: int) -> Dict:
    """
    À appeler AVANT ScoreAgent.run().
    Charge les bullets pertinents du playbook pour contextualiser le scoring.
    """
    try:
        from ace.playbook_store import render_playbook, get_active_bullets
        bullets = get_active_bullets()
        pb_text = render_playbook() if bullets else ""
        print(
            f"[ACE/Middleware/PRE] Playbook injecté | {len(bullets)} bullets | pos='{position}'",
            file=sys.stderr,
        )
        return {
            "has_playbook":  bool(bullets),
            "playbook_text": pb_text,
            "bullet_count":  len(bullets),
            "position":      position,
            "candidate_id":  candidate_id,
        }
    except Exception as e:
        print(f"[ACE/Middleware/PRE] Non-bloquant: {e}", file=sys.stderr)
        return {"has_playbook": False, "playbook_text": "", "bullet_count": 0}


def ace_post_score(
    score_result: Dict,
    candidate_id: int,
    position: str,
    ace_ctx: Dict,
) -> Optional[Dict]:
    """
    À appeler APRÈS ScoreAgent.run().
    Génère une suggestion proactive si le playbook a une règle applicable.
    """
    if score_result.get("skipped"):
        return None
    try:
        from ace.curator import suggest_for_candidate
        return suggest_for_candidate(
            candidate_id      = candidate_id,
            position          = position,
            ai_score          = score_result.get("score", 0),
            ai_recommendation = score_result.get("recommendation", "ListeAttente"),
        )
    except Exception as e:
        print(f"[ACE/Middleware/POST] Non-bloquant: {e}", file=sys.stderr)
        return None


def ace_inject_into_trace(score_result: Dict, suggestion: Optional[Dict]) -> Dict:
    """
    Ajoute la suggestion ACE dans le react_trace du ScoreAgent.
    Visible dans l'UI AiTracePanel.
    """
    playbook_entry = {
        "type":    "ace_playbook",
        "content": "[ACE] Playbook injecté dans le contexte de scoring",
    }
    existing_trace = score_result.get("react_trace", [])

    if suggestion and suggestion.get("should_suggest"):
        ace_entry = {
            "type":    "ace_suggestion",
            "content": (
                f"[ACE Playbook] {suggestion.get('suggestion', '')} "
                f"(bullet: {suggestion.get('bullet_id', 'N/A')}, "
                f"helpful={suggestion.get('helpful_count', 0)}x)"
            ),
        }
        score_result["react_trace"]   = existing_trace + [playbook_entry, ace_entry]
        score_result["ace_suggestion"] = suggestion
    else:
        score_result["react_trace"] = existing_trace + [playbook_entry]

    return score_result
