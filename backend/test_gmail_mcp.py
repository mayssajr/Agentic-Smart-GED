# test_gmail_subprocess_mcp.py
"""
Test isolé du Gmail MCP subprocess : @gongrzhe/server-gmail-autoauth-mcp
Équivalent exact à test_calendar_mcp.py mais pour Gmail.

Prérequis :
    - npx disponible
    - gcp-oauth.keys.json dans data/
    - credentials Gmail dans ~/.gmail-mcp/credentials.json
      OU GMAIL_CREDENTIALS_PATH dans .env

Usage :
    python test_gmail_subprocess_mcp.py
"""
import os, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# ── Config ──────────────────────────────────────────────────────────────────
TO      = "mayssa.jarray@isimg.tn"
SUBJECT = "Test Gmail subprocess MCP — @gongrzhe/server-gmail-autoauth-mcp"
BODY    = (
    "Bonjour,\n\n"
    "Ceci est un email de test envoyé via le Gmail MCP subprocess "
    "(@gongrzhe/server-gmail-autoauth-mcp via npx).\n\n"
    "Si vous recevez ce message, le MCP subprocess Gmail est opérationnel.\n\n"
    "Cordialement,\nSmart GED"
)

# ── Étape 1 : Vérifier npx ──────────────────────────────────────────────────
print("\n─── Étape 1 : Vérification npx ───")
if not shutil.which("npx"):
    print("❌ npx introuvable — installez Node.js")
    sys.exit(1)
print(f"npx trouvé : {shutil.which('npx')}")

# ── Étape 2 : Vérifier les fichiers OAuth ───────────────────────────────────
print("\n─── Étape 2 : Vérification fichiers OAuth ───")

from core.constants import (
    _GOOGLE_OAUTH_CREDENTIALS,
    _get_gmail_credentials_path,
    _build_gmail_spec,
)

oauth_ok = os.path.exists(_GOOGLE_OAUTH_CREDENTIALS)
print(f"gcp-oauth.keys.json : {'✅' if oauth_ok else '❌'}  ({_GOOGLE_OAUTH_CREDENTIALS})")

creds_path = _get_gmail_credentials_path()
creds_ok   = bool(creds_path)
print(f"credentials Gmail   : {'✅' if creds_ok else '❌'}  ({creds_path or 'introuvable'})")

if not oauth_ok:
    print("\n gcp-oauth.keys.json manquant — générez-le dans Google Cloud Console")
    sys.exit(1)
if not creds_ok:
    print("\n credentials Gmail manquants — lancez : npx @gongrzhe/server-gmail-autoauth-mcp auth")
    sys.exit(1)

print(" Fichiers OAuth OK")

# ── Étape 3 : Afficher la spec MCP ──────────────────────────────────────────
print("\n─── Étape 3 : Spec MCP utilisée ───")
spec = _build_gmail_spec()
print(f"  command : {spec['command']}")
print(f"  args    : {spec['args']}")
print(f"  env     : GMAIL_OAUTH_PATH={spec['env'].get('GMAIL_OAUTH_PATH','')}")
print(f"            GMAIL_CREDENTIALS_PATH={spec['env'].get('GMAIL_CREDENTIALS_PATH','')}")

# ── Étape 4 : Appel MCP send_email ──────────────────────────────────────────
print(f"\n─── Étape 4 : Envoi email via MCP subprocess → {TO} ───")
try:
    from mcp_client import call_mcp_tool

    result = call_mcp_tool(spec, "send_email", {
        "to":      [TO],
        "subject": SUBJECT,
        "body":    BODY,
    })

    print(f"RESULT: {str(result)[:300]}")
    print(f"\n Email envoyé avec succès → {TO}")

except Exception as e:
    print(f"\n Échec MCP subprocess : {e}")
    print("\n── Diagnostic ──────────────────────────────────────────────────")
    print("  1. Relancez l'auth : npx @gongrzhe/server-gmail-autoauth-mcp auth")
    print(f"  2. Vérifiez GMAIL_CREDENTIALS_PATH dans .env → {creds_path}")
    print(f"  3. Vérifiez GMAIL_OAUTH_PATH            → {_GOOGLE_OAUTH_CREDENTIALS}")
    sys.exit(1)