"""
ace/curator.py
──────────────
Le Curator ACE — style officiel ace-agent/ace.

Rôle :
  1. Reçoit les delta bullets du Reflector
  2. Appelle un LLM pour produire des opérations ADD/UPDATE/REMOVE
  3. Merge déterministe dans le playbook.json (pas de réécriture complète)
  4. Applique les garde-fous de biais (section bias_guardrails)
  5. Prune les bullets avec harmful_count > helpful_count (grow-and-refine)

Principe clé ACE : le merge est déterministe (non-LLM).
Seule la décision "quoi ajouter/modifier" est LLM-driven.
→ Évite le context collapse.
→ Permet le merge parallèle de plusieurs deltas.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from typing import Dict, List, Optional

from ace.playbook_store import (
    load_playbook,
    save_playbook,
    render_playbook,
    apply_operations,
    get_stats,
    _is_duplicate,
)


def run_curation(
    refined_deltas: List[Dict],
    source: str = "reflector",
) -> Dict:
    """
    Cycle complet de curation :
    1. LLM décide des opérations (ADD/UPDATE/REMOVE)
    2. Merge déterministe dans playbook.json
    3. Prune si nécessaire (grow-and-refine)
    4. Retourne le rapport de curation.
    """
    trace: List[Dict] = []

    def step(t: str, msg: str):
        trace.append({"type": t, "content": msg, "ts": datetime.utcnow().isoformat()})
        print(f"[ACE/Curator/{t.upper()}] {msg[:120]}", file=sys.stderr)

    step("thought",
        f"Curation | {len(refined_deltas)} delta(s) à intégrer | source={source}")

    if not refined_deltas:
        step("observe", "Aucun delta — curation terminée sans changement")
        return {"operations": [], "summary": {}, "pruned": 0, "trace": trace}

    # ── 1. LLM décide des opérations ──────────────────────────────────────────
    pb_text     = render_playbook()
    pb          = load_playbook()
    operations  = _call_curator_llm(refined_deltas, pb_text, pb.get("bullets", []))
    step("action",
        f"Curator LLM → {len(operations)} opération(s) : "
        f"{[o.get('op') for o in operations]}")

    # ── 2. Garde-fou anti-biais ────────────────────────────────────────────────
    operations = _apply_bias_guardrails(operations, step)

    # ── 3. Merge déterministe (non-LLM) ───────────────────────────────────────
    summary = apply_operations(operations, source=source)
    step("observe",
        f"Merge OK | added={summary['added']} | updated={summary['updated']} | "
        f"removed={summary['removed']} | skipped={len(summary['skipped'])}")

    # ── 4. Grow-and-refine : pruning si nécessaire ───────────────────────────
    pruned = _prune_if_needed(step)

    step("answer",
        f"Curation terminée | +{len(summary['added'])} bullets | "
        f"~{len(summary['updated'])} maj | -{pruned} pruned")

    return {
        "operations":    operations,
        "summary":       summary,
        "pruned":        pruned,
        "playbook_size": len(load_playbook().get("bullets", [])),
        "trace":         trace,
    }


def suggest_for_candidate(
    candidate_id: int,
    position: str,
    ai_score: int,
    ai_recommendation: str,
) -> Optional[Dict]:
    """
    Consulte le playbook pour générer une suggestion proactive.
    Le Curator injecte les bullets pertinents dans un prompt LLM
    pour décider si une suggestion s'impose.
    """
    from ace.playbook_store import get_active_bullets, log_override

    pb       = load_playbook()
    bullets  = pb.get("bullets", [])
    if not bullets:
        return {"should_suggest": False, "suggestion": None}

    # Filtrer les bullets pertinents pour cette position + score
    relevant = _get_relevant_bullets(bullets, position, ai_score)
    if not relevant:
        return {"should_suggest": False, "suggestion": None}

    # Vérifier si un bullet de type scoring_thresholds s'applique
    for b in relevant:
        meta      = b.get("metadata", {})
        s_min     = meta.get("score_min", 0)
        s_max     = meta.get("score_max", 100)
        pos_pat   = meta.get("position_pattern", "")
        # Bullet de scoring applicable ?
        if (b.get("section") == "scoring_thresholds" and
                s_min <= ai_score <= s_max and
                b.get("helpful_count", 0) >= 2 and
                b.get("harmful_count", 0) < b.get("helpful_count", 0)):

            # Bullet de biais ? → ne pas suggérer
            bias_bullets = [
                bb for bb in bullets
                if bb.get("section") == "bias_guardrails" and
                _normalize_pos(pos_pat) in _normalize_pos(bb.get("content", ""))
            ]
            if bias_bullets:
                continue

            from ace.playbook_store import load_playbook as _lp
            pb2 = _lp()
            pb2.setdefault("suggestions_log", []).append({
                "candidate_id":    candidate_id,
                "rule_bullet_id":  b["id"],
                "ai_score":        ai_score,
                "ai_recommendation": ai_recommendation,
                "timestamp":       datetime.utcnow().isoformat(),
                "accepted":        -1,  # en attente
            })
            save_playbook(pb2)

            suggestion_id = len(pb2["suggestions_log"]) - 1
            content       = b.get("content", "")
            return {
                "should_suggest":   True,
                "suggestion":       (
                    f"Ce profil correspond à vos critères habituels pour '{position}' "
                    f"(score {ai_score}/100 — {content}). "
                    f"Souhaitez-vous planifier un entretien ?"
                ),
                "bullet_id":        b["id"],
                "suggestion_id":    suggestion_id,
                "helpful_count":    b.get("helpful_count", 0),
                "content":          content,
            }

    return {"should_suggest": False, "suggestion": None}


def update_suggestion_outcome(suggestion_id: int, accepted: bool) -> None:
    """Met à jour l'issue d'une suggestion (feedback RH)."""
    pb = load_playbook()
    log = pb.get("suggestions_log", [])
    if 0 <= suggestion_id < len(log):
        log[suggestion_id]["accepted"] = 1 if accepted else 0
        # Feedback vers le playbook : si acceptée → +1 helpful sur le bullet
        bullet_id = log[suggestion_id].get("rule_bullet_id")
        if bullet_id:
            from ace.playbook_store import update_bullet_counters
            if accepted:
                update_bullet_counters([bullet_id], [])
            else:
                update_bullet_counters([], [bullet_id])
        pb["suggestions_log"] = log
        save_playbook(pb)


# ── Appel LLM Curator ─────────────────────────────────────────────────────────
def _call_curator_llm(
    refined_deltas: List[Dict],
    playbook_text: str,
    existing_bullets: List[Dict],
) -> List[Dict]:
    """
    Le Curator LLM produit des opérations ADD/UPDATE/REMOVE.
    Le merge lui-même est déterministe (apply_operations).
    """
    from services.llm_client import generate

    deltas_text = json.dumps(refined_deltas, ensure_ascii=False, indent=2)

    prompt = f"""Tu es le Curator ACE. Tu intègres des leçons dans le playbook d'apprentissage.

PLAYBOOK ACTUEL :
{playbook_text}

LEÇONS À INTÉGRER (du Reflector) :
{deltas_text}

TÂCHE : Produis des opérations de mise à jour. Réponds UNIQUEMENT en JSON (sans markdown) :
[
  {{
    "op": "ADD",
    "section": "<scoring_thresholds|position_patterns|override_patterns|bias_guardrails>",
    "content": "<bullet concis et actionnable>",
    "metadata": {{}}
  }},
  {{
    "op": "UPDATE",
    "id": "<id existant>",
    "content": "<nouveau contenu>",
    "helpful_delta": 0,
    "harmful_delta": 0
  }},
  {{
    "op": "REMOVE",
    "id": "<id à supprimer car redondant ou erroné>"
  }}
]

Règles strictes :
- ADD uniquement si la leçon n'existe pas déjà dans le playbook (vérifier les bullets existants)
- UPDATE si un bullet existant doit être affiné ou a un compteur à ajuster
- REMOVE uniquement si un bullet est clairement redondant ou contredit la nouvelle leçon
- Maximum 3 opérations ADD par cycle (grow-and-refine, pas de bulk insert)
- Favorise la précision et la spécificité sur la généralité
- Ne JAMAIS ajouter des généralités comme "être plus attentif aux candidats"

RÈGLE DE CONSOLIDATION OBLIGATOIRE :
- Si plusieurs bullets de la même section traitent du même critère avec des
  valeurs différentes (ex: "80% poids pratique" ET "75% poids pratique"), 
  REMOVE l'ancien et UPDATE ou ADD la version la plus récente et la plus précise.
- Un seul bullet actif par critère + poste. Les doublons créent de la confusion.
"""

    try:
        raw = generate(prompt, max_tokens=600, system=(
            "Tu es le Curator ACE. Réponds UNIQUEMENT avec un tableau JSON valide, sans markdown."
        )).strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        ops = json.loads(raw)
        if isinstance(ops, list):
            return ops
        if isinstance(ops, dict) and "operations" in ops:
            return ops["operations"]
        return []
    except Exception as e:
        print(f"[ACE/Curator/LLM] Erreur: {e}", file=sys.stderr)
        # Fallback : ajouter directement les deltas comme ADD operations
        return [
            {
                "op":       "ADD",
                "section":  d.get("section", "override_patterns"),
                "content":  d.get("content", ""),
                "metadata": d.get("metadata", {}),
            }
            for d in refined_deltas
            if d.get("content", "").strip()
        ]


# ── Garde-fous anti-biais ─────────────────────────────────────────────────────
def _apply_bias_guardrails(operations: List[Dict], step) -> List[Dict]:
    """
    Vérifie chaque ADD pour détecter des patterns de biais potentiels.
    Déplace vers bias_guardrails ou supprime si trop risqué.
    """
    BIAS_SIGNALS = [
        "genre", "sexe", "femme", "homme", "nationalit",
        "origine", "religion", "age", "handicap",
    ]
    safe_ops = []
    for op in operations:
        if op.get("op") != "ADD":
            safe_ops.append(op)
            continue

        content_low = op.get("content", "").lower()
        has_bias    = any(sig in content_low for sig in BIAS_SIGNALS)

        if has_bias:
            step("observe",
                f"GARDE-FOU — bullet contient signal de biais potentiel → "
                f"redirigé vers bias_guardrails : '{content_low[:60]}'")
            op = {**op, "section": "bias_guardrails",
                  "content": f"[SURVEILLANCE] {op['content']}"}

        safe_ops.append(op)
    return safe_ops


# ── Grow-and-refine : pruning ─────────────────────────────────────────────────
def _prune_if_needed(step) -> int:
    """
    Supprime les bullets avec harmful_count > helpful_count + 2 (nets négatifs).
    Style ACE : proactive pruning pour garder le playbook sain.
    """
    pb      = load_playbook()
    bullets = pb.get("bullets", [])
    to_prune = [
        b["id"] for b in bullets
        if b.get("harmful_count", 0) > b.get("helpful_count", 0)
    ]
    if not to_prune:
        return 0

    step("action", f"Pruning {len(to_prune)} bullet(s) nets négatifs")
    prune_ops = [{"op": "REMOVE", "id": bid} for bid in to_prune]
    apply_operations(prune_ops, source="pruning")
    return len(to_prune)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _get_relevant_bullets(bullets: List[Dict], position: str, ai_score: int) -> List[Dict]:
    """Filtre les bullets pertinents pour une position + score donné."""
    pos_norm = _normalize_pos(position)
    relevant = []
    for b in bullets:
        meta    = b.get("metadata", {})
        pos_pat = _normalize_pos(meta.get("position_pattern", ""))
        s_min   = meta.get("score_min", 0)
        s_max   = meta.get("score_max", 100)
        # Pertinent si : position match ET score dans le range
        if pos_pat and pos_pat in pos_norm and s_min <= ai_score <= s_max:
            relevant.append(b)
        elif pos_pat and pos_norm in pos_pat and s_min <= ai_score <= s_max:
            relevant.append(b)
    return relevant


def _normalize_pos(text: str) -> str:
    import unicodedata, re
    t = unicodedata.normalize("NFD", text.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^\w\s]", " ", t).strip()
