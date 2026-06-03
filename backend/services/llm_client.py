from __future__ import annotations

import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional

import requests

LLM_MODEL    = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
TIMEOUT      = int(os.getenv("LLM_TIMEOUT",      "30"))
TEMPERATURE  = float(os.getenv("LLM_TEMPERATURE", "0.3"))

MAX_RETRIES = 3

DAILY_QUOTA_THRESHOLD = float(os.getenv("GROQ_DAILY_QUOTA_THRESHOLD", "60"))

MAX_BURST_WAIT = float(os.getenv("GROQ_MAX_BURST_WAIT", "15"))


def _load_api_keys() -> List[str]:
    keys = []
    primary = os.getenv("GROQ_API_KEY", "").strip()
    if primary:
        keys.append(primary)
    for i in range(2, 11):
        k = os.getenv(f"GROQ_API_KEY_{i}", "").strip()
        if k:
            keys.append(k)
    if not keys:
        raise RuntimeError(
            "Aucune clé GROQ_API_KEY définie dans .env. "
            "Ajoutez GROQ_API_KEY (et optionnellement GROQ_API_KEY_2, …)."
        )
    return keys

_API_KEYS: List[str] = _load_api_keys()
_key_cursor: int = 0

def _get_key() -> str:
    return _API_KEYS[_key_cursor % len(_API_KEYS)]

def _rotate_key(reason: str) -> bool:
    """Passe à la clé suivante. Retourne True si une nouvelle clé est dispo."""
    global _key_cursor
    if len(_API_KEYS) == 1:
        return False
    _key_cursor += 1
    slot = _key_cursor % len(_API_KEYS)
    _log(f"🔄 Rotation → clé #{slot + 1}/{len(_API_KEYS)} | {reason}")
    return True

# ── Helpers ───────────────────────────────────────────────────────────────────

_DOC_TYPES = [
    "CV",
    "Lettre de motivation",
    "Offre d'emploi",
    "Contrat de travail",
    "Juridique",
    "Technique",
    "Autre",
]

def _log(msg: str) -> None:
    print(f"[LLM/Groq] {msg}", file=sys.stderr)

def _headers(key: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
    }

def _parse_retry_after(resp: requests.Response) -> Optional[float]:
    """Lit le retry-after brut en secondes (sans plafonnement)."""
    for header in ("retry-after", "x-ratelimit-reset-requests", "x-ratelimit-reset-tokens"):
        raw = resp.headers.get(header)
        if raw:
            try:
                return float(raw)
            except ValueError:
                pass
    try:
        body = resp.json()
        val = body.get("error", {}).get("retry_after") or body.get("retry_after")
        if val is not None:
            return float(val)
    except Exception:
        pass
    return None



def generate(
    prompt:      str,
    max_tokens:  int   = 500,
    system:      str   = "",
    temperature: float = TEMPERATURE,
    model:       str   = "",
) -> str:

    if not prompt.strip():
        return ""

    active_model = model or LLM_MODEL
    messages = []
    if system.strip():
        messages.append({"role": "system", "content": system.strip()})
    messages.append({"role": "user", "content": prompt.strip()})

    exhausted_slots: set = set()

    for attempt in range(1, MAX_RETRIES + 1):
        current_key  = _get_key()
        current_slot = _key_cursor % len(_API_KEYS)
        key_label    = f"clé #{current_slot + 1}/{len(_API_KEYS)}"

        payload = {
            "model":       active_model,
            "messages":    messages,
            "max_tokens":  max_tokens,
            "temperature": temperature,
            "stream":      False,
        }

        try:
            t0      = time.time()
            resp    = requests.post(
                GROQ_API_URL,
                json    = payload,
                headers = _headers(current_key),
                timeout = TIMEOUT,
            )
            elapsed = int((time.time() - t0) * 1000)

            if resp.status_code == 200:
                data    = resp.json()
                content = data["choices"][0]["message"]["content"].strip()
                usage   = data.get("usage", {})
                _log(
                    f"OK {elapsed}ms | "
                    f"prompt={usage.get('prompt_tokens','?')} "
                    f"completion={usage.get('completion_tokens','?')} tokens | {key_label}"
                )
                return content

            if resp.status_code == 429:
                retry_after = _parse_retry_after(resp)

                if retry_after is not None and retry_after >= DAILY_QUOTA_THRESHOLD:
                    _log(
                        f" Quota daily épuisé | {key_label} | "
                        f"retry-after={retry_after:.0f}s → rotation immédiate"
                    )
                    exhausted_slots.add(current_slot)
                    rotated  = _rotate_key(f"quota épuisé ({retry_after:.0f}s)")
                    new_slot = _key_cursor % len(_API_KEYS)

                    if rotated and new_slot not in exhausted_slots:
                        continue  
                    else:
                        _log(" Toutes les clés API sont épuisées → abandon immédiat")
                        return ""

                wait = retry_after if retry_after is not None else 5.0
                wait = min(wait, MAX_BURST_WAIT)
                _log(
                    f" Burst limit | {key_label} | "
                    f"attente {wait:.1f}s (tentative {attempt}/{MAX_RETRIES})"
                )
                time.sleep(wait)
                continue

            _log(f"HTTP {resp.status_code}: {resp.text[:200]}")
            return ""

        except requests.exceptions.Timeout:
            _log(f"Timeout ({TIMEOUT}s) — tentative {attempt}/{MAX_RETRIES}")
            if attempt == MAX_RETRIES:
                return ""
            time.sleep(1)

        except Exception as e:
            _log(f"Erreur inattendue: {e}")
            return ""

    _log(f"Toutes les tentatives épuisées ({MAX_RETRIES}) → réponse vide")
    return ""



def classify(text: str, labels: List[str] = None, context_hint: str = "") -> Dict[str, Any]:
    labels     = labels or _DOC_TYPES
    labels_str = " | ".join(labels)
    ctx        = f"\nExemples du GED :\n{context_hint[:400]}\n" if context_hint.strip() else ""
    system = (
        "Tu es un classificateur de documents GED. "
        "Reponds UNIQUEMENT par un des labels proposes, sans explication."
    )
    prompt = (
        f"Labels : {labels_str}\n{ctx}"
        f"Document :\n{text[:1200]}\n\nLabel :"
    )
    raw       = generate(prompt, max_tokens=15, system=system, temperature=0.0)
    raw_clean = raw.strip().rstrip(".,;:")
    label     = next((l for l in labels if l.lower() in raw_clean.lower()), labels[-1])
    scores    = {l: (0.85 if l == label else 0.05) for l in labels}
    return {"label": label, "scores": scores, "method": "groq-llm"}


def summarize(text: str, document_type: str = "", system: str = "") -> str:
    type_hint = {
        "CV": (
            "curriculum vitae (nom, poste visé, années d'expérience, "
            "compétences clés, formations, langues)"
        ),
        "Lettre de motivation": (
            "lettre de motivation (candidat, poste visé, motivations principales, "
            "points forts mis en avant, ton général)"
        ),
        "Offre d'emploi": (
            "offre d'emploi (intitulé du poste, entreprise, missions principales, "
            "profil recherché, conditions, rémunération)"
        ),
        "Contrat de travail": (
            "contrat de travail (parties, type de contrat CDI/CDD, poste, "
            "salaire, durée, période d'essai, clauses clés)"
        ),
        "Juridique": (
            "acte juridique (parties, objet, obligations, risques, échéances)"
        ),
        "Technique": (
            "document technique (objectif, architecture, composants clés, "
            "technologies, points d'attention)"
        ),
    }.get(document_type, "document professionnel (objet, points principaux, actions requises)")
    default_sys = (
        "Tu es un agent expert en synthese documentaire GED. "
        "Tu produis des resumes professionnels precis en francais. "
        "Tu n'inventes aucune information absente du document. "
        "Tu rediges en prose fluide, sans tirets ni listes."
    )
    prompt = (
        f"Type : {type_hint}\n\n"
        f"Document :\n{text[:3000]}\n\n"
        f"Resume (150-200 mots) :"
    )
    return generate(prompt, max_tokens=350, system=system or default_sys)


def extract_info(text: str, extraction_request: str, system: str = "") -> str:
    default_sys = (
        "Tu es un agent expert en extraction d'informations GED. "
        "Tu extrais avec precision les informations demandees. "
        "Tu ne reformules pas, tu copies les valeurs exactes. "
        "Si une information est absente, indique 'Non trouve'. "
        "Format : - Libelle : valeur"
    )
    prompt = (
        f"Demande : {extraction_request}\n\n"
        f"Document :\n{text[:2500]}\n\n"
        f"Extraction :"
    )
    return generate(prompt, max_tokens=500, system=system or default_sys)


def generate_tasks(context: str, document_type: str, filename: str) -> List[dict]:
    system = (
        "Tu generes des taches GED en JSON. "
        "Reponds UNIQUEMENT avec un tableau JSON valide, sans backtick. "
        'Format : [{"title":"...","description":"...","priority":"Haute|Moyenne|Basse","due_days":7}]'
    )
    prompt = (
        f"Document : {filename} (type={document_type})\n"
        f"Contexte :\n{context[:600]}\n\n"
        f"Genere 1 ou 2 taches concretes :"
    )
    raw = generate(prompt, max_tokens=200, system=system, temperature=0.1)
    raw = re.sub(r"```(?:json)?\s*|```\s*", "", raw).strip()
    try:
        m = re.search(r'\[.*?\]', raw, re.DOTALL)
        if m:
            tasks = json.loads(m.group(0))
            return [t for t in tasks if isinstance(t, dict) and t.get("title")][:2]
    except (json.JSONDecodeError, ValueError):
        pass
    return []


def generate_email_body(filename: str, document_type: str,
                        summary: str, extraction: str) -> str:
    system = (
        "Tu rediges des emails professionnels en francais. "
        "Email clair, concis, formel."
    )
    content = summary[:400] if summary else extraction[:400]
    prompt  = (
        f"Redige un email professionnel pour transmettre l'analyse de : "
        f"{filename} (type : {document_type})\n\n"
        f"Contenu :\n{content}\n\n"
        f"Email (objet + corps) :"
    )
    return generate(prompt, max_tokens=350, system=system)