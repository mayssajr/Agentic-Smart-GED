"""
ace/playbook_store.py
─────────────────────
Mémoire évolutive ACE — style officiel ace-agent/ace.

Le Playbook est un fichier JSON structuré en bullets :
  {id, section, content, helpful_count, harmful_count, metadata}

Format de rendu (pour injecter dans un prompt LLM) :
  ## SEUILS DE SCORING EFFECTIFS
  [scr-00001] helpful=5 harmful=0 :: Pour 'dev senior' score 60-69 → suggérer Entretien

Le Curator écrit des operations ADD / UPDATE / REMOVE qui sont
mergées de façon déterministe (pas de réécriture complète = no context collapse).

Les logs d'override et d'opérations Curator sont aussi dans le JSON
pour une traçabilité totale avant/après.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# ── Chemin du playbook ────────────────────────────────────────────────────────
_ACE_DIR    = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR   = os.path.join(_ACE_DIR, "playbooks")
PLAYBOOK_PATH = os.environ.get(
    "ACE_PLAYBOOK_PATH",
    os.path.join(_DATA_DIR, "playbook.json")
)
os.makedirs(_DATA_DIR, exist_ok=True)

# Préfixes d'ID par section (style officiel ACE)
SECTION_PREFIXES = {
    "scoring_thresholds": "scr",
    "position_patterns":  "pos",
    "override_patterns":  "ovr",
    "bias_guardrails":    "bia",
    "workflow_patterns":  "wfl",   
}


# ── Lecture / Écriture ────────────────────────────────────────────────────────
def load_playbook() -> Dict:
    """Charge le playbook depuis le fichier JSON."""
    if not os.path.exists(PLAYBOOK_PATH):
        return _empty_playbook()
    with open(PLAYBOOK_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_playbook(pb: Dict) -> None:
    """Persiste le playbook sur disque (atomic write)."""
    pb["updated_at"] = datetime.utcnow().isoformat()
    tmp = PLAYBOOK_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(pb, f, ensure_ascii=False, indent=2)
    os.replace(tmp, PLAYBOOK_PATH)


def _empty_playbook() -> Dict:
    return {
        "version": "1.0",
        "task": "recruitment_scoring",
        "updated_at": datetime.utcnow().isoformat(),
        "token_budget": 8000,
        "sections": {
            "scoring_thresholds": {"label": "SEUILS DE SCORING EFFECTIFS"},
            "position_patterns":  {"label": "PATTERNS PAR TYPE DE POSTE"},
            "override_patterns":  {"label": "PATTERNS DE CORRECTION RH"},
            "bias_guardrails":    {"label": "GARDE-FOUS ANTI-BIAIS — NE PAS IGNORER"},
        },
        "bullets": [],
        "override_log": [],
        "curator_operations_log": [],
    }


# ── Rendu Markdown du playbook (pour injection dans un prompt LLM) ────────────
def render_playbook(pb: Optional[Dict] = None) -> str:
    """
    Retourne le playbook au format texte structuré (style ACE officiel) :
      [id] helpful=X harmful=Y :: contenu
    Prêt à être injecté dans le system prompt du ScoreAgent.
    """
    if pb is None:
        pb = load_playbook()

    bullets = pb.get("bullets", [])
    if not bullets:
        return "# PLAYBOOK ACE\n*(vide — en cours d'apprentissage)*"

    # Grouper par section
    by_section: Dict[str, List[Dict]] = {}
    for b in bullets:
        sec = b.get("section", "override_patterns")
        by_section.setdefault(sec, []).append(b)

    sections_meta = pb.get("sections", {})
    lines = ["# PLAYBOOK ACE — Scoring Recrutement\n"]

    for sec_key, sec_bullets in by_section.items():
        label = sections_meta.get(sec_key, {}).get("label", sec_key.upper())
        lines.append(f"## {label}")
        for b in sorted(sec_bullets, key=lambda x: -x.get("helpful_count", 0)):
            h = b.get("helpful_count", 0)
            k = b.get("harmful_count", 0)
            bid = b.get("id", "???")
            content = b.get("content", "")
            lines.append(f"[{bid}] helpful={h} harmful={k} :: {content}")
        lines.append("")

    return "\n".join(lines)


# ── Operations Curator (ADD / UPDATE / REMOVE) ────────────────────────────────
def apply_operations(operations: List[Dict], source: str = "curator") -> Dict:
    """
    Merge déterministe des opérations Curator dans le playbook.
    operations = liste de dicts :
      { "op": "ADD",    "section": "...", "content": "...", "metadata": {} }
      { "op": "UPDATE", "id": "xxx",     "content": "...", "helpful_delta": +1, "harmful_delta": 0 }
      { "op": "REMOVE", "id": "xxx" }

    Retourne un résumé des opérations appliquées.
    """
    pb      = load_playbook()
    summary = {"added": [], "updated": [], "removed": [], "skipped": []}

    for op in operations:
        action = op.get("op", "").upper()

        if action == "ADD":
            section = op.get("section", "override_patterns")
            content = op.get("content", "").strip()
            if not content:
                summary["skipped"].append({"op": op, "reason": "empty_content"})
                continue

            # Déduplications légère : éviter les bullets quasi-identiques
            if _is_duplicate(content, pb["bullets"]):
                summary["skipped"].append({"op": op, "reason": "duplicate"})
                continue

            prefix  = SECTION_PREFIXES.get(section, "gen")
            new_id  = _next_id(prefix, pb["bullets"])
            now     = datetime.utcnow().isoformat()
            bullet  = {
                "id":            new_id,
                "section":       section,
                "content":       content,
                "helpful_count": 0,
                "harmful_count": 0,
                "created_at":    now,
                "updated_at":    now,
                "metadata":      op.get("metadata", {}),
            }
            pb["bullets"].append(bullet)
            summary["added"].append(new_id)

        elif action == "UPDATE":
            bid     = op.get("id")
            bullet  = _find_bullet(bid, pb["bullets"])
            if not bullet:
                summary["skipped"].append({"op": op, "reason": "not_found"})
                continue

            if "content" in op and op["content"].strip():
                bullet["content"] = op["content"].strip()
            bullet["helpful_count"] += op.get("helpful_delta", 0)
            bullet["harmful_count"] += op.get("harmful_delta", 0)
            bullet["updated_at"]     = datetime.utcnow().isoformat()
            summary["updated"].append(bid)

        elif action == "REMOVE":
            bid    = op.get("id")
            before = len(pb["bullets"])
            pb["bullets"] = [b for b in pb["bullets"] if b.get("id") != bid]
            if len(pb["bullets"]) < before:
                summary["removed"].append(bid)
            else:
                summary["skipped"].append({"op": op, "reason": "not_found"})

    # Enregistrer l'opération dans l'audit log
    pb["curator_operations_log"].append({
        "timestamp": datetime.utcnow().isoformat(),
        "source":    source,
        "summary":   summary,
        "operations": operations,
    })

    save_playbook(pb)
    return summary


# ── Override Log ──────────────────────────────────────────────────────────────
def log_override(override: Dict) -> str:
    """Ajoute un override dans le log du playbook. Retourne un event_id."""
    pb       = load_playbook()
    event_id = f"ov-{uuid.uuid4().hex[:10]}"
    pb["override_log"].append({
        "event_id":   event_id,
        "logged_at":  datetime.utcnow().isoformat(),
        **override,
    })
    save_playbook(pb)
    return event_id


def get_override_log(
    position_pattern: Optional[str] = None,
    score_min: int = 0,
    score_max: int = 100,
    direction: Optional[str] = None,
    limit: int = 50,
) -> List[Dict]:
    """Filtre les overrides depuis le log du playbook."""
    pb  = load_playbook()
    log = pb.get("override_log", [])

    if position_pattern:
        norm = _normalize(position_pattern)
        log  = [o for o in log if norm in _normalize(o.get("position", ""))]
    if direction:
        log = [o for o in log if o.get("delta_direction") == direction]

    log = [o for o in log
           if score_min <= o.get("ai_score", 0) <= score_max]

    return log[-limit:]


# ── Bullet utils ──────────────────────────────────────────────────────────────
def get_active_bullets(section: Optional[str] = None) -> List[Dict]:
    """Retourne les bullets actifs (harmful_count < helpful_count ou harmful=0)."""
    pb      = load_playbook()
    bullets = pb.get("bullets", [])
    if section:
        bullets = [b for b in bullets if b.get("section") == section]
    # Trier : plus utiles d'abord
    return sorted(
        bullets,
        key=lambda b: b.get("helpful_count", 0) - b.get("harmful_count", 0),
        reverse=True,
    )


def update_bullet_counters(bullet_ids_helpful: List[str],
                           bullet_ids_harmful: List[str]) -> None:
    """Met à jour les compteurs helpful/harmful après usage par le Generator."""
    ops = []
    for bid in bullet_ids_helpful:
        ops.append({"op": "UPDATE", "id": bid, "helpful_delta": 1, "harmful_delta": 0})
    for bid in bullet_ids_harmful:
        ops.append({"op": "UPDATE", "id": bid, "helpful_delta": 0, "harmful_delta": 1})
    if ops:
        apply_operations(ops, source="generator_feedback")


def get_stats() -> Dict:
    """Statistiques globales du playbook."""
    pb      = load_playbook()
    bullets = pb.get("bullets", [])
    log     = pb.get("override_log", [])
    ops_log = pb.get("curator_operations_log", [])

    total_helpful = sum(b.get("helpful_count", 0) for b in bullets)
    total_harmful = sum(b.get("harmful_count", 0) for b in bullets)
    upgrades      = sum(1 for o in log if o.get("delta_direction") == "upgrade")
    downgrades    = sum(1 for o in log if o.get("delta_direction") == "downgrade")

    return {
        "playbook": {
            "total_bullets":   len(bullets),
            "total_helpful":   total_helpful,
            "total_harmful":   total_harmful,
            "by_section": {
                s: sum(1 for b in bullets if b.get("section") == s)
                for s in SECTION_PREFIXES
            },
        },
        "overrides": {
            "total":      len(log),
            "upgrades":   upgrades,
            "downgrades": downgrades,
            "avg_ai_score": (
                round(sum(o.get("ai_score", 0) for o in log) / len(log), 1)
                if log else 0
            ),
        },
        "curator_cycles": len(ops_log),
        "last_updated":   pb.get("updated_at", ""),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────
def _normalize(text: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFD", text.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^\w\s]", " ", t)


def _is_duplicate(content: str, bullets: List[Dict], threshold: float = 0.85) -> bool:
    """Détection légère de doublon par ratio de mots communs."""
    norm_new = set(_normalize(content).split())
    for b in bullets:
        norm_ex = set(_normalize(b.get("content", "")).split())
        if not norm_ex:
            continue
        overlap = len(norm_new & norm_ex) / max(len(norm_new | norm_ex), 1)
        if overlap >= threshold:
            return True
    return False


def _find_bullet(bid: str, bullets: List[Dict]) -> Optional[Dict]:
    for b in bullets:
        if b.get("id") == bid:
            return b
    return None


def _next_id(prefix: str, bullets: List[Dict]) -> str:
    """Génère le prochain ID séquentiel : scr-00001, scr-00002, …"""
    existing = [
        int(re.search(r"\d+", b["id"]).group())
        for b in bullets
        if b.get("id", "").startswith(prefix + "-") and re.search(r"\d+", b["id"])
    ]
    n = max(existing) + 1 if existing else 1
    return f"{prefix}-{n:05d}"
