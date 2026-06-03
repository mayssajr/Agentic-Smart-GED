from __future__ import annotations
from enum import Enum
import os


class WorkflowID(str, Enum):
    CLASSIFY    = "classify"
    SUMMARIZE   = "summarize"
    EXTRACT     = "extract"
    LEGAL       = "legal"
    SIGN        = "sign"
    EMAIL       = "email"
    TASKS       = "tasks"
    COMPARE     = "compare"
    REDACT      = "redact"
    FOLDER_SCAN = "folder_scan"


class SkillID(str, Enum):
    CLASSIFY_LLM     = "classify_llm"
    CLASSIFY_RAG     = "classify_rag"
    SUMMARIZE_DOC    = "summarize_doc"
    EXTRACT_FIELDS   = "extract_fields"
    EXTRACT_FORM     = "extract_form"
    EXTRACT_NER      = "extract_ner"
    LEGAL_SCORE      = "legal_score"
    LEGAL_REFS       = "legal_refs"
    LEGIFRANCE_CODE  = "legifrance_code"
    LEGIFRANCE_JURIS = "legifrance_juris"
    LEGIFRANCE_LODA  = "legifrance_loda"
    SIGN_PDF         = "sign_pdf"
    SIGN_DETECT      = "sign_detect"   # détection seule (SignatureAgent)
    OCR_EXTRACT      = "ocr_extract"
    EMAIL_REPORT     = "email_report"
    EMAIL_SIGNED     = "email_signed"
    EMAIL_ATTACHMENT = "email_attachment"
    TASK_RULES       = "task_rules"
    TASK_LLM         = "task_llm"
    MEMORY_READ      = "memory_read"
    MEMORY_WRITE     = "memory_write"
    RAG_INDEX        = "rag_index"
    RAG_SEARCH       = "rag_search"
    WEB_FETCH        = "web_fetch"
    GED_SEARCH       = "ged_search"
    TIME_GET         = "time_get"
    CALENDAR_READ    = "calendar_read"
    CALENDAR_WRITE   = "calendar_write"
    FILESYSTEM_LIST  = "filesystem_list"
    FILESYSTEM_READ  = "filesystem_read"


class DocType(str, Enum):
    CV                 = "CV"
    LETTRE_MOTIVATION  = "Lettre de motivation"
    OFFRE_EMPLOI       = "Offre d'emploi"
    CONTRAT_TRAVAIL    = "Contrat de travail"
    JURIDIQUE          = "Juridique"
    TECHNIQUE          = "Technique"
    AUTRE              = "Autre"


class DocumentCategory(str, Enum):
    CANDIDATURE        = "Candidature"
    DOSSIER_RH         = "Dossier RH"
    DOSSIER_RH_COMPLET = "Dossier RH complet"
    CONTRAT            = "Contrat de travail"
    OFFRE              = "Offre d'emploi"
    JURIDIQUE          = "Juridique"
    TECHNIQUE          = "Technique"
    AUTRE              = "Autre"


class CandidateStatus(str, Enum):
    RECU          = "Reçu"
    EN_ANALYSE    = "En analyse"
    A_TRAITER     = "À traiter"
    ENTRETIEN     = "Entretien"
    ACCEPTE       = "Accepté"
    REFUSE        = "Refusé"
    LISTE_ATTENTE = "Liste d'attente"


PLAN_WORKFLOWS: dict[str, list[WorkflowID]] = {
    "basic":      [WorkflowID.CLASSIFY, WorkflowID.SUMMARIZE,
                   WorkflowID.SIGN, WorkflowID.TASKS],
    "pro":        [WorkflowID.CLASSIFY, WorkflowID.SUMMARIZE, WorkflowID.EXTRACT,
                   WorkflowID.SIGN, WorkflowID.EMAIL, WorkflowID.TASKS, WorkflowID.COMPARE],
    "enterprise": list(WorkflowID),
}

DEFAULT_WORKFLOWS: list[WorkflowID] = [WorkflowID.CLASSIFY, WorkflowID.SUMMARIZE]

MAX_TEXT_PER_FILE   = 4_000
MAX_TEXT_MERGED     = 10_000
MAX_SUMMARY_TOKENS  = 350
MAX_EXTRACT_TOKENS  = 500
MAX_CLASSIFY_TOKENS = 15
MAX_LEGAL_TOKENS    = 450
MAX_TASK_LLM_TOKENS = 200
MAX_CHAT_TOKENS     = 700
MAX_FOLDER_FILES    = 20

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR    = os.path.abspath(os.getenv("GED_DATA_DIR", os.path.join(BASE_DIR, "data")))
DOCS_DIR    = os.path.abspath(os.getenv("DOCS_DIR",     os.path.join(BASE_DIR, "documents")))
DB_PATH     = os.path.abspath(os.getenv("GED_DB_PATH",  os.path.join(DATA_DIR, "ged.db")))
CHROMA_PATH = os.path.abspath(os.getenv("CHROMA_PATH",  os.path.join(DATA_DIR, "chroma")))

_OPENLEGI_TOKEN = os.getenv("OPENLEGI_TOKEN", "")

_GOOGLE_OAUTH_CREDENTIALS = os.path.abspath(
    os.getenv("GOOGLE_CREDENTIALS_PATH", "./data/gcp-oauth.keys.json")
)

_GOOGLE_TOKEN_PATH = os.path.abspath(
    os.getenv("GOOGLE_TOKEN_PATH", "./token.json")
)


_GMAIL_MCP_DEFAULT = os.path.join(
    os.path.expanduser("~"), ".gmail-mcp", "credentials.json"
)

def _get_gmail_credentials_path() -> str:
    env_path = os.getenv("GMAIL_CREDENTIALS_PATH", "")
    if env_path:
        expanded = os.path.abspath(env_path)
        if os.path.exists(expanded):
            return expanded
    if os.path.exists(_GMAIL_MCP_DEFAULT):
        return _GMAIL_MCP_DEFAULT
    if os.path.exists(_GOOGLE_TOKEN_PATH):
        return _GOOGLE_TOKEN_PATH
    return ""

def _gmail_mcp_available() -> bool:
    """
    Vérifie si le MCP Gmail subprocess (npx) est disponible.
    NOTE : avec google_mcp_client.py, cette voie n'est plus la première
    tentative dans EmailAgent. Elle reste pour compatibilité.
    """
    import shutil, sys
    npx_ok    = shutil.which("npx") is not None
    oauth_ok  = os.path.exists(_GOOGLE_OAUTH_CREDENTIALS)
    creds_ok  = bool(_get_gmail_credentials_path())
    print(
        f"[GmailMCP] npx={npx_ok} | oauth={oauth_ok} ({_GOOGLE_OAUTH_CREDENTIALS}) "
        f"| creds={creds_ok} ({_get_gmail_credentials_path()})",
        file=__import__("sys").stderr,
    )
    return npx_ok and oauth_ok and creds_ok


def _build_gcal_spec() -> dict:
    return {
        "command": "npx",
        "args": ["-y", "@cocal/google-calendar-mcp"],
        "env": {
            **os.environ,
            "GOOGLE_CREDENTIALS_PATH": _GOOGLE_OAUTH_CREDENTIALS,
            "GOOGLE_TOKEN_PATH":       _GOOGLE_TOKEN_PATH,
            "GOOGLE_CALENDAR_ID":      os.getenv("GOOGLE_CALENDAR_ID", "primary"),
        },
    }

def _build_gmail_spec() -> dict:
    return {
        "command": "npx",
        "args":    ["-y", "@gongrzhe/server-gmail-autoauth-mcp"],
        "env": {
            "GMAIL_OAUTH_PATH":       _GOOGLE_OAUTH_CREDENTIALS,
            "GMAIL_CREDENTIALS_PATH": _get_gmail_credentials_path(),
        },
    }


MCP_SPECS: dict = {
    "fetch": {
        "command": "python",
        "args":    ["-m", "mcp_server_fetch"],
        "env":     {"PYTHONIOENCODING": "utf-8"},
    },
    "time": {
        "command": "python",
        "args":    ["-m", "mcp_server_time"],
        "env":     {"PYTHONIOENCODING": "utf-8"},
    },
    "memory": {
        "command": "npx",
        "args":    ["-y", "@modelcontextprotocol/server-memory"],
        "env":     {"MEMORY_FILE_PATH": os.path.join(DATA_DIR, "ged_memory.json")},
    },
    "filesystem": {
        "command": "npx",
        "args":    ["-y", "@modelcontextprotocol/server-filesystem", DOCS_DIR],
        "env":     {},
    },

    "google_calendar": _build_gcal_spec(),
    "gmail":           _build_gmail_spec(),

    "openlegi": {
        "url":  f"https://mcp.openlegi.fr/legifrance/mcp?token={_OPENLEGI_TOKEN}",
        "type": "sse",
        "headers": {
            "Authorization": f"Bearer {_OPENLEGI_TOKEN}",
            "Content-Type":  "application/json",
            "Accept":        "application/json, text/event-stream",
        },
    },
}


MCP_LOCAL: dict = {
    "extractor":  os.path.join(BASE_DIR, "servers", "extractor_server.py"),
    "summarizer": os.path.join(BASE_DIR, "servers", "summarizer_server.py"),
    "metadata":   os.path.join(BASE_DIR, "servers", "metadata_server.py"),
    "miniged": {
        "command": "dotnet",
        "args": [
            "run",
            "--project",
            os.path.abspath(os.getenv(
                "MINIGED_BACKEND_PROJECT",
                r"D:\smart-ged\ged-smart-assistant-mini-GED\MiniGED.Backend\MiniGED.API.csproj"
            )),
            "--no-build", "--", "--mcp",
        ],
        "env": {},
    },
}


def get_google_credentials():
    """
    Retourne des credentials Google valides.

    Ordre de priorité :
      1. GOOGLE_REFRESH_TOKEN dans .env → credentials construites à la volée
         via google.oauth2.credentials.Credentials (refresh automatique)
         C'est la méthode générée par generate_google_token.py.
      2. token.json sur disque (chemin GOOGLE_TOKEN_PATH ou ~/.gmail-mcp/token.json)
         → compatibilité ascendante avec les tokens existants.

    Retourne None si aucune source n'est disponible ou si les credentials
    ne sont pas valides.
    """
    import sys

    # ── Priorité 1 : refresh_token dans .env ──────────────────────────────────
    refresh_token  = os.getenv("GOOGLE_REFRESH_TOKEN", "")
    client_id      = os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret  = os.getenv("GOOGLE_CLIENT_SECRET", "")

    if refresh_token and client_id and client_secret:
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request

            creds = Credentials(
                token         = None,          # sera rafraîchi automatiquement
                refresh_token = refresh_token,
                token_uri     = "https://oauth2.googleapis.com/token",
                client_id     = client_id,
                client_secret = client_secret,
            )
            # Forcer le refresh pour obtenir un access_token valide
            creds.refresh(Request())
            print("[constants] get_google_credentials : refresh_token .env OK",
                  file=sys.stderr)
            return creds
        except Exception as e:
            print(f"[constants] get_google_credentials refresh_token failed : {e}",
                  file=sys.stderr)
            # Ne pas retourner None tout de suite : essayer token.json en fallback

    # ── Priorité 2 : token.json sur disque ────────────────────────────────────
    _BASE  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _DATA  = os.path.abspath(os.getenv("GED_DATA_DIR", os.path.join(_BASE, "data")))

    candidates = [
        os.path.abspath(os.getenv("GOOGLE_TOKEN_PATH",
                                   os.path.join(_DATA, "token.json"))),
        os.path.join(os.path.expanduser("~"), ".gmail-mcp", "token.json"),
        os.path.abspath(os.getenv("GMAIL_CREDENTIALS_PATH", "")),
    ]

    token_path = next((p for p in candidates if p and os.path.exists(p)), None)

    if not token_path:
        print(
            f"[constants] Aucun token.json trouvé. Chemins essayés : {candidates}",
            file=sys.stderr,
        )
        return None

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        creds = Credentials.from_authorized_user_file(token_path)

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, "w") as f:
                f.write(creds.to_json())

        if creds.valid:
            print(f"[constants] get_google_credentials : token.json OK ({token_path})",
                  file=sys.stderr)
            return creds

        print(f"[constants] token.json invalide et non rafraîchissable ({token_path})",
              file=sys.stderr)
        return None

    except Exception as e:
        print(f"[constants] get_google_credentials error ({token_path}): {e}",
              file=sys.stderr)
        return None