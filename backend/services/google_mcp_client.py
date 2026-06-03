"""
services/google_mcp_client.py
Client MCP HTTP pour Gmail et Google Calendar officiels.
Token refresh automatique — aucune réauthentification nécessaire.
"""
from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()


import os, sys, time, json
from typing import Any, Optional
import requests


_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "")
_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN", "")

_GMAIL_MCP_URL    = "https://gmailmcp.googleapis.com/mcp/v1"
_CALENDAR_MCP_URL = "https://calendarmcp.googleapis.com/mcp/v1"

_access_token:  str   = ""
_token_expiry:  float = 0.0


def _log(msg: str) -> None:
    print(f"[GoogleMcpClient] {msg}", file=sys.stderr)


def _get_access_token() -> str:
    """Retourne un access_token valide, en le rafraîchissant si nécessaire."""
    global _access_token, _token_expiry

    if _access_token and time.time() < _token_expiry - 60:
        return _access_token

    if not _REFRESH_TOKEN:
        raise RuntimeError(
            "GOOGLE_REFRESH_TOKEN manquant — lancez generate_google_token.py"
        )

    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id":     _CLIENT_ID,
        "client_secret": _CLIENT_SECRET,
        "refresh_token": _REFRESH_TOKEN,
        "grant_type":    "refresh_token",
    }, timeout=10)

    if resp.status_code != 200:
        raise RuntimeError(f"Token refresh failed: {resp.text[:200]}")

    data          = resp.json()
    _access_token = data["access_token"]
    _token_expiry = time.time() + data.get("expires_in", 3600)
    _log(f"Access token rafraîchi (expire dans {data.get('expires_in',3600)}s)")
    return _access_token


def _call_mcp(endpoint_url: str, tool_name: str, params: dict) -> Any:
    """Appel générique à un endpoint MCP HTTP Google."""
    token = _get_access_token()
    payload = {
        "jsonrpc": "2.0",
        "id":      1,
        "method":  "tools/call",
        "params": {
            "name":      tool_name,
            "arguments": params,
        }
    }
    resp = requests.post(
        endpoint_url,
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"MCP HTTP {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"MCP error: {data['error']}")

    result = data.get("result", {})
    content = result.get("content", [])
    if content and isinstance(content, list):
        return content[0].get("text", "")
    return result


# ── Gmail ─────────────────────────────────────────────────────────────────────

def gmail_send(
    to:       str,
    subject:  str,
    body:     str,
    reply_to: str = "",
) -> dict:
    """
    Envoie un email via Gmail MCP officiel (sans pièce jointe).
    Persistant — refresh automatique du token.
    """
    try:
        params = {
            "to":      to,
            "subject": subject,
            "body":    body,
        }
        if reply_to:
            params["replyTo"] = reply_to

        result = _call_mcp(_GMAIL_MCP_URL, "send_email", params)
        _log(f"Gmail MCP OK → {to}")
        return {"success": True, "email_to": to, "raw": result}

    except Exception as e:
        _log(f"Gmail MCP failed: {e}")
        return {"success": False, "error": str(e)}


def gmail_list_labels() -> list:
    """Liste les labels Gmail (test de connectivité)."""
    try:
        raw = _call_mcp(_GMAIL_MCP_URL, "list_labels", {})
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception as e:
        _log(f"gmail_list_labels: {e}")
        return []


# ── Google Calendar ───────────────────────────────────────────────────────────

def calendar_create_event(
    summary:    str,
    start_dt:   str,   # ISO 8601 ex: "2026-05-12T10:00:00+02:00"
    end_dt:     str,
    description: str  = "",
    calendar_id: str  = "primary",
    attendees:   list = None,
) -> dict:
    """
    Crée un événement Google Calendar via MCP officiel.
    Persistant — refresh automatique du token.
    """
    try:
        params = {
            "summary":    summary,
            "start":      {"dateTime": start_dt, "timeZone": "Europe/Paris"},
            "end":        {"dateTime": end_dt,   "timeZone": "Europe/Paris"},
            "calendarId": calendar_id,
        }
        if description:
            params["description"] = description
        if attendees:
            params["attendees"] = [{"email": a} for a in attendees]

        result = _call_mcp(_CALENDAR_MCP_URL, "create_event", params)
        _log(f"Calendar MCP OK → '{summary}'")
        return {"success": True, "raw": result}

    except Exception as e:
        _log(f"Calendar MCP failed: {e}")
        return {"success": False, "error": str(e)}


def calendar_list_events(
    calendar_id: str = "primary",
    max_results: int = 5,
    time_min:    str = "",   # ISO 8601
) -> list:
    """Liste les événements Calendar via MCP officiel."""
    try:
        params = {
            "calendarId": calendar_id,
            "maxResults": max_results,
        }
        if time_min:
            params["timeMin"] = time_min

        raw = _call_mcp(_CALENDAR_MCP_URL, "list_events", params)
        result = json.loads(raw) if isinstance(raw, str) else raw
        return result if isinstance(result, list) else []

    except Exception as e:
        _log(f"calendar_list_events: {e}")
        return []


def is_available() -> bool:
    """Vérifie que les credentials Google sont configurés."""
    return bool(_CLIENT_ID and _CLIENT_SECRET and _REFRESH_TOKEN)