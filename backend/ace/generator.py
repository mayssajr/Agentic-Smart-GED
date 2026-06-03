"""
ace/generator.py — Le Generator ACE avec support des notes RH structurées (+/-).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from typing import Dict, List, Optional

from ace.playbook_store import (
    load_playbook,
    log_override,
    render_playbook,
    update_bullet_counters,
    get_override_log,
    _normalize,
)

SIGNIFICANT_UPGRADES = {
    ("ListeAttente", "Entretien"),
    ("Refuse", "ListeAttente"),
    ("Refuse", "Entretien"),
    ("ATraiter", "Entretien"),
}

STATUS_RANK = {
    "Recu": 0, "ATraiter": 1, "Refuse": 2,
    "ListeAttente": 3, "Entretien": 4, "Accepte": 5,
}


def observe_override(
    candidate_id:      int,
    candidate_name:    str,
    position:          str,
    ai_score:          int,
    ai_recommendation: str,
    ai_status:         str,
    human_status:      str,
    user_id:           str  = "system",
    notes:             str  = "",
    rh_notes:          List[Dict] = None, 
) -> Dict:
    """
    Point d'entrée principal du Generator.
    Analyse l'override + les notes RH structurées pour créer des bullets précis.
    """
    trace: List[Dict] = []

    def step(t: str, msg: str):
        trace.append({"type": t, "content": msg, "ts": datetime.utcnow().isoformat()})
        print(f"[ACE/Generator/{t.upper()}] {msg[:120]}", file=sys.stderr)

    rh_notes = rh_notes or [] 
    # ── Direction de l'override ────────────────────────────────────────────────
    ai_rank  = STATUS_RANK.get(ai_status, -1)
    hum_rank = STATUS_RANK.get(human_status, -1)
    direction = (
        "upgrade"   if hum_rank > ai_rank else
        "downgrade" if hum_rank < ai_rank else
        "same"
    )

    # Résumé des notes pour le log
    notes_summary = ""
    if rh_notes:
        positives = [n["text"] for n in rh_notes if n.get("sign") == "+"]
        negatives = [n["text"] for n in rh_notes if n.get("sign") == "-"]
        notes_summary = (
            f" | +[{', '.join(positives[:2])}]" if positives else ""
        ) + (
            f" | -[{', '.join(negatives[:2])}]" if negatives else ""
        )

    step("thought",
        f"Override | '{candidate_name}' | pos='{position}' | score={ai_score}/100 | "
        f"{ai_status}→{human_status} ({direction}){notes_summary}")

    # ── Log dans le playbook.json ──────────────────────────────────────────────
    event_id = log_override({
        "candidate_id":      candidate_id,
        "candidate_name":    candidate_name,
        "position":          position,
        "ai_score":          ai_score,
        "ai_recommendation": ai_recommendation,
        "ai_status":         ai_status,
        "human_status":      human_status,
        "delta_direction":   direction,
        "user_id":           str(user_id),
        "notes":             notes,
        "rh_notes":          rh_notes,  # ← stocké dans le log pour traçabilité
    })
    step("action", f"Override loggé → event_id={event_id} | {len(rh_notes)} note(s) RH")

    # ── Charger le playbook ────────────────────────────────────────────────────
    pb_text = render_playbook()
    step("observe", f"Playbook chargé — {pb_text.count(chr(10))} lignes")

    # ── Overrides similaires ───────────────────────────────────────────────────
    score_bucket_min = (ai_score // 10) * 10
    score_bucket_max = score_bucket_min + 9
    similar = get_override_log(
        position_pattern=position,
        score_min=score_bucket_min,
        score_max=score_bucket_max,
        direction="upgrade",
        limit=10,
    )
    step("observe",
        f"{len(similar)} override(s) similaire(s) | "
        f"score {score_bucket_min}-{score_bucket_max}")

    # ── Appel LLM ────────────────────────────────────────────────────────────
    llm_result = _call_generator_llm(
        playbook_text     = pb_text,
        position          = position,
        ai_score          = ai_score,
        ai_status         = ai_status,
        human_status      = human_status,
        ai_recommendation = ai_recommendation,
        similar_overrides = similar,
        direction         = direction,
        notes             = notes,
        rh_notes          = rh_notes,  # ← transmis au prompt LLM
    )
    step("action",
        f"LLM Generator → {len(llm_result.get('delta_bullets', []))} delta(s) | "
        f"helpful={llm_result.get('helpful_ids', [])} | "
        f"harmful={llm_result.get('harmful_ids', [])}")

    # ── Mettre à jour les compteurs ───────────────────────────────────────────
    if llm_result.get("helpful_ids") or llm_result.get("harmful_ids"):
        update_bullet_counters(
            llm_result.get("helpful_ids", []),
            llm_result.get("harmful_ids", []),
        )
        step("observe", "Compteurs helpful/harmful mis à jour")

    step("answer",
        f"Trajectoire générée | is_significant={direction in ('upgrade','downgrade')} | "
        f"delta_bullets={len(llm_result.get('delta_bullets', []))}")

    return {
        "event_id":       event_id,
        "direction":      direction,
        "is_significant": (ai_status, human_status) in SIGNIFICANT_UPGRADES,
        "trajectory":     llm_result.get("trajectory", ""),
        "delta_bullets":  llm_result.get("delta_bullets", []),
        "helpful_ids":    llm_result.get("helpful_ids", []),
        "harmful_ids":    llm_result.get("harmful_ids", []),
        "similar_count":  len(similar),
        "score_bucket":   f"{score_bucket_min}-{score_bucket_max}",
        "trace":          trace,
    }


# ── Appel LLM Generator ───────────────────────────────────────────────────────

def _call_generator_llm(
    playbook_text:     str,
    position:          str,
    ai_score:          int,
    ai_status:         str,
    human_status:      str,
    ai_recommendation: str,
    similar_overrides: List[Dict],
    direction:         str,
    notes:             str,
    rh_notes:          List[Dict],
) -> Dict:
    from services.llm_client import generate

    # ── Section overrides similaires ──────────────────────────────────────────
    similar_text = ""
    if similar_overrides:
        similar_text = f"\n\nOVERRIDES SIMILAIRES ({len(similar_overrides)}) :\n"
        for o in similar_overrides[-5:]:
            similar_text += (
                f"  - score={o['ai_score']} | {o['ai_status']}→{o['human_status']} "
                f"| pos='{o['position']}'\n"
            )

    # ── Section notes RH structurées ──────────────────────────────────────────
    # C'est la VRAIE valeur ajoutée : le RH explique POURQUOI il a pris cette décision.
    # Le LLM peut créer des bullets très précis basés sur ces explications.
    rh_notes_section = ""
    if rh_notes:
        positives = [n["text"] for n in rh_notes if n.get("sign") == "+"]
        negatives = [n["text"] for n in rh_notes if n.get("sign") == "-"]
        rh_notes_section = "\n\nNOTES RH STRUCTURÉES (raisons de la décision) :\n"
        if positives:
            rh_notes_section += "  POINTS POSITIFS (+) observés par le RH :\n"
            for p in positives:
                rh_notes_section += f"    + {p}\n"
        if negatives:
            rh_notes_section += "  POINTS NÉGATIFS (-) observés par le RH :\n"
            for n in negatives:
                rh_notes_section += f"    - {n}\n"
        rh_notes_section += (
            "\n  → Ces notes sont les VRAIES raisons de la décision RH. "
            "Utilise-les pour créer des bullets TRÈS SPÉCIFIQUES dans le playbook."
        )

    prompt = f"""Tu es un analyste RH expert. Analyse cet override de décision IA.

CONTEXTE PLAYBOOK ACE (connaissance accumulée) :
{playbook_text}

OVERRIDE ACTUEL :
- Poste : {position}
- Score IA : {ai_score}/100
- Recommandation IA : {ai_recommendation} (statut : {ai_status})
- Décision RH : {human_status} ({direction})
- Notes RH libres : {notes or "aucune"}
{rh_notes_section}
{similar_text}

TÂCHE : Analyse cet override et réponds UNIQUEMENT en JSON valide (sans markdown) :
{{
  "trajectory": "<2-3 phrases : pourquoi l'IA s'est trompée et ce que le RH a corrigé>",
  "helpful_ids": ["<ids bullets utiles>"],
  "harmful_ids": ["<ids bullets nuisibles>"],
  "delta_bullets": [
    {{
      "section": "<scoring_thresholds|position_patterns|override_patterns|bias_guardrails>",
      "content": "<leçon TRÈS SPÉCIFIQUE basée sur les notes RH si disponibles>",
      "metadata": {{
        "position_pattern": "{position}",
        "ai_score_observed": {ai_score},
        "correction_type": "{direction}",
        "rh_note_signs": "<'+' ou '-' selon les notes qui ont motivé ce bullet>"
      }}
    }}
  ]
}}

Règles :
- Si des notes RH structurées (+/-) sont présentes, elles doivent OBLIGATOIREMENT
  orienter le contenu des delta_bullets (elles expliquent la vraie raison)
- Maximum 2 bullets, UNIQUEMENT si la leçon est nouvelle et concrète
- Ne pas dupliquer les patterns existants dans le playbook
- Pour les notes "+" : créer des bullets "si présence de X → Entretien"
- Pour les notes "-" : créer des bullets "si absence de X → vérifier avant validation"
"""

    try:
        raw = generate(prompt, max_tokens=600, system=(
            "Tu es un analyste ACE. Réponds UNIQUEMENT en JSON valide, sans markdown."
        )).strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        result.setdefault("trajectory", "")
        result.setdefault("helpful_ids", [])
        result.setdefault("harmful_ids", [])
        result.setdefault("delta_bullets", [])
        return result
    except Exception as e:
        print(f"[ACE/Generator/LLM] Erreur: {e}", file=sys.stderr)
        return {
            "trajectory": (
                f"Le RH a corrigé ({ai_status}→{human_status}) "
                f"pour score {ai_score}/100 au poste '{position}'."
            ),
            "helpful_ids": [],
            "harmful_ids": [],
            "delta_bullets": _fallback_delta(
                position, ai_score, ai_status, human_status, direction, rh_notes
            ) if direction in ("upgrade", "downgrade") else [],
        }


def _fallback_delta(
    position:     str,
    ai_score:     int,
    ai_status:    str,
    human_status: str,
    direction:    str,
    rh_notes:     List[Dict],
) -> List[Dict]:
    """Delta minimal sans LLM — intègre les notes RH si disponibles."""
    s_min    = (ai_score // 10) * 10
    s_max    = s_min + 9
    pos_norm = " ".join(_normalize(position).split()[:4])

    # Construire le contenu du bullet en tenant compte des notes RH
    rh_context = ""
    if rh_notes:
        positives = [n["text"] for n in rh_notes if n.get("sign") == "+"]
        negatives = [n["text"] for n in rh_notes if n.get("sign") == "-"]
        if positives:
            rh_context += f" Points forts : {', '.join(positives[:2])}."
        if negatives:
            rh_context += f" Points faibles : {', '.join(negatives[:2])}."

    return [{
        "section": "scoring_thresholds",
        "content": (
            f"Pour '{pos_norm}', score {s_min}-{s_max} → "
            f"RH préfère '{human_status}' (observé 1x).{rh_context}"
        ),
        "metadata": {
            "position_pattern": pos_norm,
            "score_min":        s_min,
            "score_max":        s_max,
            "correction_type":  direction,
            "rh_note_signs":    ",".join(
                set(n.get("sign", "") for n in rh_notes)
            ) if rh_notes else "",
        },
    }]