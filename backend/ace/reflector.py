"""
ace/reflector.py
────────────────
Le Reflector ACE — style officiel ace-agent/ace.

Rôle :
  1. Reçoit la trajectoire produite par le Generator
  2. Analyse les erreurs, succès, patterns récurrents
  3. Peut itérer N rounds pour raffiner les insights
  4. Produit des delta bullets structurés pour le Curator
  5. Compare avant/après ACE pour la traceabilité

Le Reflector est le "critique analytique" : il sépare
l'évaluation de la curation (principe clé ACE).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from typing import Dict, List, Optional

from ace.playbook_store import (
    load_playbook,
    render_playbook,
    get_override_log,
    get_stats,
)

MAX_REFLECTION_ROUNDS = 3  # Raffinements itératifs max (style ACE paper)


def reflect_on_trajectory(
    generator_result: Dict,
    max_rounds: int = 2,
) -> Dict:
    """
    Analyse la trajectoire du Generator et raffine les insights.
    Retourne des delta bullets consolidés pour le Curator.

    Peut faire plusieurs rounds de réflexion (style ACE paper §3.1).
    """
    trace: List[Dict] = []

    def step(t: str, msg: str):
        trace.append({"type": t, "content": msg, "ts": datetime.utcnow().isoformat()})
        print(f"[ACE/Reflector/{t.upper()}] {msg[:120]}", file=sys.stderr)

    trajectory   = generator_result.get("trajectory", "")
    delta_bullets = generator_result.get("delta_bullets", [])
    event_id     = generator_result.get("event_id", "")
    direction    = generator_result.get("direction", "")
    is_significant = generator_result.get("is_significant", False)

    step("thought",
        f"Réflexion | event={event_id} | direction={direction} | "
        f"is_significant={is_significant} | {len(delta_bullets)} delta(s) initial")

    # Si pas significatif, pas besoin de réflexion profonde
    if not is_significant and not delta_bullets:
        step("observe", "Override non significatif — réflexion minimale")
        return {
            "refined_deltas": [],
            "rounds_done":    0,
            "insights":       "",
            "trace":          trace,
        }

    # ── Charger le contexte ────────────────────────────────────────────────────
    pb_text      = render_playbook()
    similar_count = generator_result.get("similar_count", 0)

    step("observe",
        f"Contexte : playbook={pb_text.count(chr(10))} lignes | "
        f"similar_overrides={similar_count}")

    # ── Rounds de réflexion ───────────────────────────────────────────────────
    refined_deltas  = list(delta_bullets)
    previous_reflection = ""
    rounds_done     = 0

    for round_n in range(1, min(max_rounds, MAX_REFLECTION_ROUNDS) + 1):
        step("action", f"Réflexion round {round_n}/{max_rounds}")

        llm_result = _call_reflector_llm(
            trajectory          = trajectory,
            current_deltas      = refined_deltas,
            playbook_text       = pb_text,
            similar_count       = similar_count,
            previous_reflection = previous_reflection,
            round_n             = round_n,
        )

        new_deltas           = llm_result.get("refined_deltas", [])
        previous_reflection  = llm_result.get("reasoning", "")
        rounds_done          = round_n

        step("observe",
            f"Round {round_n} → {len(new_deltas)} delta(s) | "
            f"reasoning='{previous_reflection[:80]}'")

        # Si le Reflector dit "pas de changement" → arrêter les rounds
        if llm_result.get("no_change", False) or not new_deltas:
            step("observe", "Pas d'amélioration supplémentaire — fin des rounds")
            break

        refined_deltas = new_deltas

    step("answer",
        f"Réflexion terminée | {rounds_done} round(s) | "
        f"{len(refined_deltas)} delta(s) finaux pour le Curator")

    return {
        "refined_deltas":   refined_deltas,
        "rounds_done":      rounds_done,
        "insights":         previous_reflection,
        "trace":            trace,
    }


def build_before_after_report() -> Dict:
    """
    Compare l'état AVANT ACE (baseline dans le playbook)
    avec l'état ACTUEL. Métriques clés pour la traceabilité.
    """
    pb    = load_playbook()
    stats = get_stats()

    baseline = pb.get("baseline_snapshot")
    current  = {
        "date":              pb.get("updated_at", ""),
        "total_bullets":     stats["playbook"]["total_bullets"],
        "total_overrides":   stats["overrides"]["total"],
        "upgrades":          stats["overrides"]["upgrades"],
        "curator_cycles":    stats["curator_cycles"],
        "avg_ai_score":      stats["overrides"]["avg_ai_score"],
        "bullets_by_section": stats["playbook"]["by_section"],
    }

    if not baseline:
        return {
            "baseline_available": False,
            "current":            current,
            "message":            "Appelez POST /ace/baseline pour enregistrer l'état initial.",
        }

    baseline_overrides = baseline.get("total_overrides", 0)
    baseline_cands     = max(baseline.get("total_candidates", 1), 1)
    current_overrides  = stats["overrides"]["total"]
    current_cands      = max(baseline_cands, 1)  # référence fixe

    baseline_rate = baseline_overrides / baseline_cands
    current_rate  = current_overrides  / current_cands
    improvement   = baseline_rate - current_rate

    # Efficacité des suggestions (si loggées)
    suggestion_acceptance = (
        stats.get("suggestions_accepted", 0) /
        max(stats.get("suggestions_total", 0), 1)
    )

    return {
        "baseline_available": True,
        "baseline": {
            **baseline,
            "override_rate": f"{baseline_rate:.1%}",
        },
        "current": {
            **current,
            "override_rate": f"{current_rate:.1%}",
        },
        "delta": {
            "override_rate_change": f"{improvement:+.1%}",
            "playbook_grew_by":     stats["playbook"]["total_bullets"],
            "curator_cycles_run":   stats["curator_cycles"],
            "label": (
                f"Depuis l'intégration ACE : taux d'override "
                f"{'↓ ' + f'{abs(improvement):.1%}' if improvement > 0 else '↑ ' + f'{abs(improvement):.1%}'}"
                f" | Playbook : {stats['playbook']['total_bullets']} bullets actifs"
            ),
        },
    }


# ── Appel LLM Reflector ───────────────────────────────────────────────────────
def _call_reflector_llm(
    trajectory: str,
    current_deltas: List[Dict],
    playbook_text: str,
    similar_count: int,
    previous_reflection: str,
    round_n: int,
) -> Dict:
    """
    Le Reflector LLM raffine les delta bullets.
    Multi-round : utilise previous_reflection pour s'améliorer.
    """
    from services.llm_client import generate

    prev_section = ""
    if previous_reflection:
        prev_section = f"\nRÉFLEXION PRÉCÉDENTE (round {round_n-1}) :\n{previous_reflection}\n"

    current_deltas_text = json.dumps(current_deltas, ensure_ascii=False, indent=2)

    prompt = f"""Tu es le Reflector ACE. Tu analyses des trajectoires de décision RH
pour raffiner les leçons à intégrer dans le playbook d'apprentissage.

PLAYBOOK ACTUEL :
{playbook_text}

TRAJECTOIRE DU GENERATOR :
{trajectory}

DELTAS PROPOSÉS (round {round_n}) :
{current_deltas_text}

CONTEXTE : {similar_count} override(s) similaire(s) observé(s) au total.
{prev_section}

TÂCHE : Raffine les delta bullets. Réponds UNIQUEMENT en JSON (sans markdown) :
{{
  "reasoning": "<analyse en 2 phrases : qu'est-ce qui est utile, qu'est-ce qui manque>",
  "no_change": false,
  "refined_deltas": [
    {{
      "section": "<scoring_thresholds|position_patterns|override_patterns|bias_guardrails>",
      "content": "<leçon concrète, actionnable, spécifique — 1 phrase max>",
      "metadata": {{}}
    }}
  ]
}}

Règles de raffinement :
- Rends les bullets plus spécifiques et actionnables (pas de généralités)
- Maximum 3 bullets, seulement si vraiment nouveaux par rapport au playbook
- Si les deltas actuels sont déjà bons → "no_change": true et "refined_deltas": []
- Pour bias_guardrails : seulement si pattern de biais clair et répété (≥3 fois)
- Privilege la précision sur la quantité (grow-and-refine ACE)
"""

    try:
        raw = generate(prompt, max_tokens=500, system=(
            "Tu es le Reflector ACE. Réponds UNIQUEMENT en JSON valide, sans markdown."
        )).strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        result.setdefault("reasoning", "")
        result.setdefault("no_change", False)
        result.setdefault("refined_deltas", [])
        return result
    except Exception as e:
        print(f"[ACE/Reflector/LLM] Erreur round {round_n}: {e}", file=sys.stderr)
        return {"reasoning": "", "no_change": True, "refined_deltas": []}
