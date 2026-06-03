import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("metadata-server")

# Chemin SQLite local — crée le dossier si nécessaire
_RAW_DB  = os.getenv("GED_DB_PATH", "./data/ged.db")
DB_PATH  = os.path.abspath(_RAW_DB)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            filename      TEXT    NOT NULL,
            document_type TEXT    NOT NULL DEFAULT 'Autre',
            confidence    REAL    NOT NULL DEFAULT 0.0,
            summary       TEXT    NOT NULL DEFAULT '',
            keywords      TEXT    NOT NULL DEFAULT '[]',
            agents_used   TEXT    NOT NULL DEFAULT '[]',
            signed        INTEGER NOT NULL DEFAULT 0,
            signer        TEXT    NOT NULL DEFAULT '',
            email_sent    INTEGER NOT NULL DEFAULT 0,
            email_to      TEXT    NOT NULL DEFAULT '',
            processing_ms INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT    NOT NULL,
            updated_at    TEXT    NOT NULL
        )
    """)
    conn.commit()
    return conn


@mcp.tool()
def save_document_metadata(
    filename:      str,
    document_type: str   = "Autre",
    confidence:    float = 0.0,
    summary:       str   = "",
    keywords:      str   = "[]",
    agents_used:   str   = "[]",
    processing_ms: int   = 0,
) -> str:
    """Insère un enregistrement de document dans la base SQLite locale."""
    now = datetime.now(timezone.utc).isoformat()
    try:
        conn = _get_conn()
        cur  = conn.execute(
            """INSERT INTO documents
               (filename, document_type, confidence, summary, keywords,
                agents_used, processing_ms, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (filename, document_type, confidence, summary,
             keywords, agents_used, processing_ms, now, now),
        )
        conn.commit()
        doc_id = cur.lastrowid
        conn.close()
        print(f"[MetadataServer] saved id={doc_id} file={filename!r}", file=sys.stderr)
        return json.dumps({"success": True, "id": doc_id, "error": None})
    except Exception as exc:
        print(f"[MetadataServer] save error: {exc}", file=sys.stderr)
        return json.dumps({"success": False, "id": None, "error": str(exc)})


@mcp.tool()
def update_signature_status(
    filename:    str,
    signed:      bool = True,
    signer_name: str  = "",
) -> str:
    """Marque un document comme signé dans la base locale."""
    now = datetime.now(timezone.utc).isoformat()
    try:
        conn = _get_conn()
        conn.execute(
            "UPDATE documents SET signed=?, signer=?, updated_at=? WHERE filename=?",
            (1 if signed else 0, signer_name, now, filename),
        )
        conn.commit()
        conn.close()
        return json.dumps({"success": True, "error": None})
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


@mcp.tool()
def update_email_status(filename: str, email_to: str) -> str:
    """Marque un document comme envoyé par email."""
    now = datetime.now(timezone.utc).isoformat()
    try:
        conn = _get_conn()
        conn.execute(
            "UPDATE documents SET email_sent=1, email_to=?, updated_at=? WHERE filename=?",
            (email_to, now, filename),
        )
        conn.commit()
        conn.close()
        return json.dumps({"success": True, "error": None})
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


@mcp.tool()
def list_documents(limit: int = 50, offset: int = 0) -> str:
    """Retourne les documents récents depuis la base locale (les plus récents en premier)."""
    try:
        conn = _get_conn()
        rows = conn.execute(
            """SELECT id, filename, document_type, confidence, summary,
                      signed, signer, email_sent, email_to,
                      processing_ms, created_at
               FROM documents
               ORDER BY id DESC
               LIMIT ? OFFSET ?""",
            (limit, offset),
        ).fetchall()
        conn.close()
        docs = [dict(r) for r in rows]
        return json.dumps({"documents": docs, "count": len(docs)})
    except Exception as exc:
        return json.dumps({"documents": [], "count": 0, "error": str(exc)})


@mcp.tool()
def get_stats() -> str:
    """Retourne les statistiques agrégées depuis la base locale."""
    try:
        conn  = _get_conn()
        total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

        by_type_rows = conn.execute(
            "SELECT document_type, COUNT(*) as cnt FROM documents GROUP BY document_type"
        ).fetchall()
        by_type = {r["document_type"]: r["cnt"] for r in by_type_rows}

        avgs = conn.execute(
            "SELECT AVG(confidence) as ac, AVG(processing_ms) as ap FROM documents"
        ).fetchone()
        signed  = conn.execute("SELECT COUNT(*) FROM documents WHERE signed=1").fetchone()[0]
        emailed = conn.execute("SELECT COUNT(*) FROM documents WHERE email_sent=1").fetchone()[0]
        conn.close()

        return json.dumps({
            "total":              total,
            "by_type":            by_type,
            "avg_confidence":     round(avgs["ac"] or 0.0, 3),
            "avg_processing_ms":  int(avgs["ap"] or 0),
            "signed_count":       signed,
            "emailed_count":      emailed,
        })
    except Exception as exc:
        return json.dumps({"total": 0, "error": str(exc)})


if __name__ == "__main__":
    mcp.run(transport="stdio")