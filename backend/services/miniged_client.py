from __future__ import annotations

import os
import re
import sys
from typing import Any, Dict, List, Optional

import requests

MINIGED_BASE = os.getenv("MINIGED_API_URL", "http://localhost:5092")
TIMEOUT      = int(os.getenv("MINIGED_TIMEOUT", "8"))

# Mots vides à exclure de la requête PostgreSQL
_STOP_FR = {
    "cherche","trouve","recherche","montre","affiche","liste","donne","voir",
    "quels","quel","quelle","quelles","combien","tous","toutes","moi","mon",
    "le","la","les","un","une","des","de","du","au","aux","et","ou","que",
    "qui","est","sont","dans","pour","avec","sur","par","il","y","a","t",
    "document","documents","fichier","fichiers","ged",
    "existent","existe","maintenant","actuellement",
}


def _log(msg: str) -> None:
    print(f"[MiniGedClient] {msg}", file=sys.stderr)


def _headers(bearer_token: str = "") -> Dict[str, str]:
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if bearer_token:
        token = bearer_token.strip()
        if not token.lower().startswith("bearer "):
            token = f"Bearer {token}"
        h["Authorization"] = token
    return h


def _headers_no_content(bearer_token: str = "") -> Dict[str, str]:
    """Headers sans Content-Type pour les requêtes de téléchargement binaire."""
    h = {"Accept": "application/octet-stream, application/pdf, */*"}
    if bearer_token:
        token = bearer_token.strip()
        if not token.lower().startswith("bearer "):
            token = f"Bearer {token}"
        h["Authorization"] = token
    return h


def _clean_query(raw: str) -> str:
    """
    Extrait les mots significatifs pour PostgreSQL websearch_to_tsquery.

    Exemples :
      "cherche le contrat CDI Jean Dupont" → "contrat CDI Jean Dupont"
      "combien de documents y a t il"      → ""  (vide → liste récente)
      "candidature Paul Genie"             → "candidature Paul Genie"
    """
    words = re.sub(r"[^\w\s]", " ", raw).split()
    meaningful = [w for w in words if w.lower() not in _STOP_FR and len(w) > 1]
    return " ".join(meaningful[:6])


def search_documents(query: str, bearer_token: str = "",
                     limit: int = 10) -> List[dict]:
    """
    Recherche full-text MiniGED via POST /api/document/search.
    Utilise DocumentSearchRequest.Query (champ exact du C#).
    Nettoie la query avant envoi pour matcher le tsvector PostgreSQL.
    """
    if not query.strip():
        return []

    clean = _clean_query(query)
    if not clean:
        _log(f"search: query trop vague → []")
        return []

    try:
        resp = requests.post(
            f"{MINIGED_BASE}/api/document/search",
            json={"query": clean, "page": 1, "pageSize": limit},
            headers=_headers(bearer_token),
            timeout=TIMEOUT,
        )
        _log(f"search POST '{clean}' → {resp.status_code}")

        if resp.status_code == 200:
            data  = resp.json()
            items = (data.get("results", {}).get("items", [])
                     or data.get("items", [])
                     or (data if isinstance(data, list) else []))
            _log(f"search résultats: {len(items)}")
            return items

        if resp.status_code == 401:
            _log("search 401 : token invalide ou expiré")
        else:
            _log(f"search HTTP {resp.status_code}: {resp.text[:100]}")

    except Exception as e:
        _log(f"search_documents exception: {type(e).__name__}: {e}")
    return []


def list_recent_documents(bearer_token: str = "", limit: int = 20) -> List[dict]:
    """
    Liste les documents de l'utilisateur via GET /api/Document.
    Utilisé pour les questions générales ("combien de documents", "liste tout").
    """
    try:
        resp = requests.get(
            f"{MINIGED_BASE}/api/Document",
            headers=_headers(bearer_token),
            timeout=TIMEOUT,
        )
        _log(f"list_recent GET → {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            docs = data if isinstance(data, list) else data.get("items", [])
            _log(f"list_recent: {len(docs)} documents")
            return docs[:limit]
    except Exception as e:
        _log(f"list_recent exception: {e}")
    return []


def get_document(document_id: str, bearer_token: str = "") -> Optional[dict]:
    """Récupère les métadonnées d'un document avec ses fichiers."""
    try:
        resp = requests.get(
            f"{MINIGED_BASE}/api/Document/{document_id}",
            headers=_headers(bearer_token),
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        _log(f"get_document exception: {e}")
    return None


def get_file_text(file_id: str, bearer_token: str = "") -> str:
    """Récupère le texte extrait d'un fichier PDF."""
    try:
        resp = requests.get(
            f"{MINIGED_BASE}/api/Document/file/{file_id}/text",
            headers=_headers(bearer_token),
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("textContent", data.get("text", ""))
    except Exception as e:
        _log(f"get_file_text exception: {e}")
    return ""


def get_file_bytes(document_id: str, bearer_token: str = "",
                   file_id: str = "") -> Optional[bytes]:
    """
    Télécharge le fichier PDF d'un document en bytes.
    Utilisé pour les pièces jointes email.

    Essaie dans l'ordre :
    1. GET /api/document/pdf/{file_id}        (endpoint existant AllowAnonymous)
    2. GET /api/document/{document_id}/file/{file_id}/bytes  (nouveau endpoint)
    3. GET /api/document/{document_id}/download              (fallback)
    """
    # Stratégie 1 : endpoint PDF direct (déjà dans DocumentFileController)
    if file_id:
        try:
            resp = requests.get(
                f"{MINIGED_BASE}/api/document/pdf/{file_id}",
                headers=_headers_no_content(bearer_token),
                timeout=30,
            )
            _log(f"get_file_bytes pdf/{file_id} → {resp.status_code} ({len(resp.content)} bytes)")
            if resp.status_code == 200 and resp.content:
                return resp.content
        except Exception as e:
            _log(f"get_file_bytes strategy1 exception: {e}")

    # Stratégie 2 : endpoint bytes (si ajouté dans MiniGED)
    target_id = file_id or document_id
    try:
        resp = requests.get(
            f"{MINIGED_BASE}/api/document/{document_id}/file/{target_id}/bytes",
            headers=_headers_no_content(bearer_token),
            timeout=30,
        )
        _log(f"get_file_bytes strategy2 → {resp.status_code}")
        if resp.status_code == 200 and resp.content:
            return resp.content
    except Exception as e:
        _log(f"get_file_bytes strategy2 exception: {e}")

    # Stratégie 3 : endpoint download générique
    try:
        resp = requests.get(
            f"{MINIGED_BASE}/api/document/{document_id}/download",
            headers=_headers_no_content(bearer_token),
            timeout=30,
        )
        _log(f"get_file_bytes strategy3 → {resp.status_code}")
        if resp.status_code == 200 and resp.content:
            return resp.content
    except Exception as e:
        _log(f"get_file_bytes strategy3 exception: {e}")

    _log(f"get_file_bytes: aucune stratégie n'a fonctionné pour doc={document_id}")
    return None


def get_document_files_info(document_id: str, bearer_token: str = "") -> List[dict]:
    """
    Récupère la liste des fichiers d'un document avec leurs IDs.
    Utile pour sélectionner quel fichier envoyer en pièce jointe.
    """
    doc = get_document(document_id, bearer_token)
    if not doc:
        return []
    files = doc.get("files", doc.get("Files", []))
    return [
        {
            "id":        f.get("id") or f.get("Id"),
            "filename":  f.get("fileName") or f.get("FileName") or f.get("filename", ""),
            "fileSize":  f.get("fileSize") or f.get("FileSize", 0),
            "status":    f.get("status") or f.get("Status", ""),
            "pageCount": f.get("pageCount") or f.get("PageCount", 0),
        }
        for f in files
    ]


def push_tasks(document_id: str, tasks: List[dict],
               bearer_token: str = "") -> dict:
    pushed, failed, ids = 0, 0, []
    for task in tasks:
        if not task.get("title"):
            continue
        try:
            resp = requests.post(
                f"{MINIGED_BASE}/api/Document/{document_id}/tasks",
                json={
                    "title":       task["title"],
                    "description": task.get("description", ""),
                    "priority":    task.get("priority", "Moyenne"),
                    "dueDate":     task.get("due_date", ""),
                },
                headers=_headers(bearer_token),
                timeout=TIMEOUT,
            )
            if resp.status_code in (200, 201):
                pushed += 1
                data = resp.json()
                ids.append(data.get("id") or data.get("taskId", ""))
            else:
                failed += 1
                _log(f"push_task rejeté ({resp.status_code}): '{task['title']}'")
        except Exception as e:
            failed += 1
            _log(f"push_task exception: {e}")
    return {"pushed": pushed, "failed": failed, "ids": ids}


def update_document_metadata(
    document_id:   str,
    document_type: str       = "",
    summary:       str       = "",
    keywords:      List[str] = None,
    confidence:    float     = 0.0,
    bearer_token:  str       = "",
) -> bool:
    try:
        body: Dict[str, Any] = {}
        if document_type: body["documentType"] = document_type
        if summary:        body["summary"]      = summary[:500]
        if keywords:       body["keywords"]     = keywords
        if confidence:     body["aiConfidence"] = round(confidence, 3)
        if not body:
            return True
        resp = requests.patch(
            f"{MINIGED_BASE}/api/Document/{document_id}/metadata",
            json=body,
            headers=_headers(bearer_token),
            timeout=TIMEOUT,
        )
        success = resp.status_code in (200, 204)
        _log(f"{'OK' if success else 'KO'} metadata doc={document_id}")
        return success
    except Exception as e:
        _log(f"update_document_metadata exception: {e}")
        return False