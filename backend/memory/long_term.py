from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

# ── Path DB ───────────────────────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.abspath(os.getenv("GED_DATA_DIR", os.path.join(_BASE_DIR, "data")))
DB_PATH   = os.path.abspath(os.getenv("GED_DB_PATH",  os.path.join(_DATA_DIR, "ged.db")))
os.makedirs(_DATA_DIR, exist_ok=True)


@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def _init():
    with _conn() as con:
        con.executescript("""
            -- Tables existantes (inchangées)
            CREATE TABLE IF NOT EXISTS learning_store (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                key        TEXT NOT NULL,
                value      TEXT NOT NULL,
                updated_at TEXT DEFAULT (datetime('now')),
                UNIQUE(agent_name, key)
            );
            CREATE INDEX IF NOT EXISTS idx_ls_agent ON learning_store(agent_name);

            CREATE TABLE IF NOT EXISTS context_packs (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                pack_id      TEXT UNIQUE NOT NULL,
                doc_type     TEXT NOT NULL,
                pack_name    TEXT NOT NULL,
                content      TEXT NOT NULL,
                source       TEXT DEFAULT 'generator',
                validated    INTEGER DEFAULT 0,
                usage_count  INTEGER DEFAULT 0,
                avg_quality  REAL DEFAULT 0.0,
                updated_at   TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_cp_type ON context_packs(doc_type);

            CREATE TABLE IF NOT EXISTS signed_documents (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                filename        TEXT NOT NULL,
                content_hash    TEXT DEFAULT '',
                signer_name     TEXT DEFAULT '',
                pdf_size_bytes  INTEGER DEFAULT 0,
                signed_at       TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_sd_file ON signed_documents(filename);

            CREATE TABLE IF NOT EXISTS calendar_reminders (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                filename      TEXT NOT NULL,
                document_type TEXT DEFAULT '',
                reminder_date TEXT NOT NULL,
                notes         TEXT DEFAULT '',
                created_at    TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_cr_date ON calendar_reminders(reminder_date);

            CREATE TABLE IF NOT EXISTS reflections (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL,
                doc_type    TEXT DEFAULT '',
                file_count  INTEGER DEFAULT 1,
                quality     REAL DEFAULT 0.0,
                issues      TEXT DEFAULT '[]',
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_ref_type ON reflections(doc_type);

            CREATE TABLE IF NOT EXISTS user_interactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL,
                doc_type    TEXT DEFAULT '',
                action      TEXT NOT NULL,
                result      TEXT DEFAULT '',
                user_feedback TEXT DEFAULT '',
                created_at  TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_ui_type ON user_interactions(doc_type);

            -- NOUVELLE TABLE : conversations persistantes
            CREATE TABLE IF NOT EXISTS conversations (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                conv_id    TEXT NOT NULL,
                user_id    TEXT NOT NULL,
                role       TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
                content    TEXT NOT NULL,
                metadata   TEXT DEFAULT '{}',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_conv_id     ON conversations(conv_id);
            CREATE INDEX IF NOT EXISTS idx_conv_user   ON conversations(user_id);
            CREATE INDEX IF NOT EXISTS idx_conv_time   ON conversations(created_at);

            -- NOUVELLE TABLE : métadonnées des conversations
            CREATE TABLE IF NOT EXISTS conversation_sessions (
                conv_id     TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                title       TEXT DEFAULT '',
                summary     TEXT DEFAULT '',
                doc_context TEXT DEFAULT '',
                created_at  TEXT DEFAULT (datetime('now')),
                updated_at  TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_cs_user ON conversation_sessions(user_id);
        """)


_init()


class LongTermMemory:

    # ── Learning Store ────────────────────────────────────────────────────────

    def memorize(self, agent_name: str, key: str, value: Any) -> None:
        val = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
        with _conn() as con:
            con.execute(
                "INSERT OR REPLACE INTO learning_store (agent_name, key, value, updated_at) VALUES (?,?,?,datetime('now'))",
                (agent_name, key, val))

    def recall(self, agent_name: str, key: str) -> Optional[Any]:
        with _conn() as con:
            row = con.execute(
                "SELECT value FROM learning_store WHERE agent_name=? AND key=?",
                (agent_name, key)).fetchone()
        if not row: return None
        try: return json.loads(row[0])
        except: return row[0]

    def get_all_learning(self, agent_name: str = "") -> List[dict]:
        with _conn() as con:
            if agent_name:
                rows = con.execute("SELECT * FROM learning_store WHERE agent_name=? ORDER BY updated_at DESC", (agent_name,)).fetchall()
            else:
                rows = con.execute("SELECT * FROM learning_store ORDER BY agent_name, key").fetchall()
        return [dict(r) for r in rows]

    # ── Context Packs ACE ─────────────────────────────────────────────────────

    def save_context_pack(self, pack_id: str, doc_type: str, pack_name: str,
                           content: dict, source: str = "generator") -> None:
        with _conn() as con:
            con.execute(
                "INSERT OR REPLACE INTO context_packs (pack_id, doc_type, pack_name, content, source, updated_at) VALUES (?,?,?,?,?,datetime('now'))",
                (pack_id, doc_type, pack_name, json.dumps(content, ensure_ascii=False), source))

    def get_context_pack(self, doc_type: str, validated_only: bool = True) -> Optional[dict]:
        with _conn() as con:
            q = ("SELECT * FROM context_packs WHERE doc_type=? "
                 + ("AND validated=1 " if validated_only else "")
                 + "ORDER BY avg_quality DESC, usage_count DESC LIMIT 1")
            row = con.execute(q, (doc_type,)).fetchone()
        if not row: return None
        d = dict(row); d["content"] = json.loads(d["content"]); return d

    def get_context_pack_by_id(self, pack_id: str) -> Optional[dict]:
        with _conn() as con:
            row = con.execute("SELECT * FROM context_packs WHERE pack_id=?", (pack_id,)).fetchone()
        if not row: return None
        d = dict(row); d["content"] = json.loads(d["content"]); return d

    def get_all_context_packs(self, validated_only: bool = True) -> List[dict]:
        with _conn() as con:
            q = "SELECT * FROM context_packs " + ("WHERE validated=1 " if validated_only else "") + "ORDER BY doc_type, avg_quality DESC"
            rows = con.execute(q).fetchall()
        return [{**dict(r), "content": json.loads(r["content"])} for r in rows]

    def validate_context_pack(self, pack_id: str) -> None:
        with _conn() as con:
            con.execute("UPDATE context_packs SET validated=1, updated_at=datetime('now') WHERE pack_id=?", (pack_id,))

    def increment_pack_usage(self, pack_id: str) -> None:
        with _conn() as con:
            con.execute("UPDATE context_packs SET usage_count=usage_count+1 WHERE pack_id=?", (pack_id,))

    def update_pack_quality(self, pack_id: str, quality: float) -> None:
        with _conn() as con:
            con.execute("UPDATE context_packs SET avg_quality=?, updated_at=datetime('now') WHERE pack_id=?", (round(quality, 3), pack_id))

    # ── Réflexions ACE ────────────────────────────────────────────────────────

    def save_reflection(self, document_id: str, doc_type: str, quality: float,
                         issues: list, notes: str = "", file_count: int = 1) -> None:
        with _conn() as con:
            con.execute(
                "INSERT INTO reflections (document_id, doc_type, file_count, quality, issues, notes) VALUES (?,?,?,?,?,?)",
                (document_id, doc_type, file_count, quality, json.dumps(issues, ensure_ascii=False), notes))

    def get_reflections(self, doc_type: str = "", limit: int = 20) -> List[dict]:
        with _conn() as con:
            if doc_type:
                rows = con.execute("SELECT * FROM reflections WHERE doc_type=? ORDER BY created_at DESC LIMIT ?", (doc_type, limit)).fetchall()
            else:
                rows = con.execute("SELECT * FROM reflections ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [{**dict(r), "issues": json.loads(r["issues"] or "[]")} for r in rows]

    def get_avg_quality(self, doc_type: str = "") -> float:
        with _conn() as con:
            if doc_type:
                row = con.execute("SELECT AVG(quality) FROM reflections WHERE doc_type=?", (doc_type,)).fetchone()
            else:
                row = con.execute("SELECT AVG(quality) FROM reflections").fetchone()
        return round(row[0] or 0.0, 3)

    # ── Interactions ──────────────────────────────────────────────────────────

    def log_interaction(self, document_id: str, doc_type: str, action: str,
                         result: str = "", user_feedback: str = "") -> None:
        with _conn() as con:
            con.execute(
                "INSERT INTO user_interactions (document_id, doc_type, action, result, user_feedback) VALUES (?,?,?,?,?)",
                (document_id, doc_type, action, result[:200], user_feedback[:200]))

    def get_interaction_stats(self, doc_type: str = "") -> dict:
        with _conn() as con:
            by_action = con.execute("SELECT action, COUNT(*) as n FROM user_interactions" + (" WHERE doc_type=?" if doc_type else "") + " GROUP BY action ORDER BY n DESC", (doc_type,) if doc_type else ()).fetchall()
            by_type   = con.execute("SELECT doc_type, COUNT(*) as n FROM user_interactions GROUP BY doc_type ORDER BY n DESC").fetchall()
            total     = con.execute("SELECT COUNT(*) FROM user_interactions").fetchone()[0]
        return {"total": total, "by_action": {r[0]: r[1] for r in by_action}, "by_type": {r[0]: r[1] for r in by_type}}

    # ── Signatures ────────────────────────────────────────────────────────────

    def save_signed_document(self, filename: str, signer_name: str = "",
                              content_hash: str = "", pdf_size_bytes: int = 0) -> int:
        with _conn() as con:
            cur = con.execute(
                "INSERT INTO signed_documents (filename, content_hash, signer_name, pdf_size_bytes) VALUES (?,?,?,?)",
                (filename, content_hash, signer_name, pdf_size_bytes))
            return cur.lastrowid

    def is_document_signed(self, filename: str, content_hash: str = "") -> Optional[Dict[str, Any]]:
        with _conn() as con:
            if content_hash:
                row = con.execute("SELECT * FROM signed_documents WHERE filename=? AND content_hash=? ORDER BY signed_at DESC LIMIT 1", (filename, content_hash)).fetchone()
            else:
                row = con.execute("SELECT * FROM signed_documents WHERE filename=? ORDER BY signed_at DESC LIMIT 1", (filename,)).fetchone()
        return dict(row) if row else None

    # ── Rappels calendrier ────────────────────────────────────────────────────

    def save_calendar_reminder(self, filename: str, document_type: str,
                                reminder_date: str, notes: str = "") -> int:
        with _conn() as con:
            cur = con.execute(
                "INSERT INTO calendar_reminders (filename, document_type, reminder_date, notes) VALUES (?,?,?,?)",
                (filename, document_type, reminder_date, notes[:300]))
            return cur.lastrowid

    def get_upcoming_reminders(self, days_ahead: int = 30) -> List[dict]:
        with _conn() as con:
            rows = con.execute(
                "SELECT * FROM calendar_reminders WHERE reminder_date >= date('now') AND reminder_date <= date('now', ? || ' days') ORDER BY reminder_date ASC",
                (str(days_ahead),)).fetchall()
        return [dict(r) for r in rows]

    # ── CONVERSATIONS PERSISTANTES ────────────────────────────────────────────

    def save_conversation_message(
        self,
        conv_id:  str,
        user_id:  str,
        role:     str,
        content:  str,
        metadata: dict = None,
    ) -> None:
        """Sauvegarde un message dans une conversation persistante."""
        with _conn() as con:
            con.execute(
                "INSERT INTO conversations (conv_id, user_id, role, content, metadata) VALUES (?,?,?,?,?)",
                (conv_id, user_id, role, content,
                 json.dumps(metadata or {}, ensure_ascii=False))
            )
            # Mettre à jour la session
            con.execute("""
                INSERT INTO conversation_sessions (conv_id, user_id, updated_at)
                VALUES (?, ?, datetime('now'))
                ON CONFLICT(conv_id) DO UPDATE SET updated_at=datetime('now')
            """, (conv_id, user_id))

    def get_conversation(self, conv_id: str, limit: int = 50) -> List[dict]:
        """Récupère l'historique complet d'une conversation."""
        with _conn() as con:
            rows = con.execute(
                "SELECT role, content, created_at, metadata FROM conversations "
                "WHERE conv_id=? ORDER BY created_at ASC LIMIT ?",
                (conv_id, limit)
            ).fetchall()
        return [
            {
                "role":       r["role"],
                "content":    r["content"],
                "created_at": r["created_at"],
                "metadata":   json.loads(r["metadata"] or "{}"),
            }
            for r in rows
        ]

    def get_conversation_as_history(self, conv_id: str, last_n: int = 10) -> List[dict]:
        """
        Retourne l'historique au format {role, content} pour injection dans le prompt.
        Utilisé par run_chat() pour charger une conversation existante.
        """
        with _conn() as con:
            rows = con.execute(
                "SELECT role, content FROM conversations "
                "WHERE conv_id=? ORDER BY created_at DESC LIMIT ?",
                (conv_id, last_n)
            ).fetchall()
        # Remettre dans l'ordre chronologique
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    def list_conversations(self, user_id: str, limit: int = 20) -> List[dict]:
        """Liste les conversations d'un utilisateur, triées par date décroissante."""
        with _conn() as con:
            rows = con.execute("""
                SELECT
                    cs.conv_id,
                    cs.title,
                    cs.summary,
                    cs.doc_context,
                    cs.created_at,
                    cs.updated_at,
                    COUNT(c.id) as message_count,
                    (SELECT content FROM conversations
                     WHERE conv_id=cs.conv_id AND role='user'
                     ORDER BY created_at DESC LIMIT 1) as last_user_msg
                FROM conversation_sessions cs
                LEFT JOIN conversations c ON c.conv_id = cs.conv_id
                WHERE cs.user_id=?
                GROUP BY cs.conv_id
                ORDER BY cs.updated_at DESC
                LIMIT ?
            """, (user_id, limit)).fetchall()
        return [dict(r) for r in rows]

    def update_conversation_session(
        self,
        conv_id:     str,
        title:       str = "",
        summary:     str = "",
        doc_context: str = "",
    ) -> None:
        """Met à jour les métadonnées d'une session de conversation."""
        with _conn() as con:
            updates = []
            params  = []
            if title:
                updates.append("title=?"); params.append(title[:200])
            if summary:
                updates.append("summary=?"); params.append(summary[:500])
            if doc_context:
                updates.append("doc_context=?"); params.append(doc_context[:200])
            updates.append("updated_at=datetime('now')")
            params.append(conv_id)
            if updates:
                con.execute(
                    f"UPDATE conversation_sessions SET {', '.join(updates)} WHERE conv_id=?",
                    params
                )

    def delete_conversation(self, conv_id: str, user_id: str) -> bool:
        """Supprime une conversation (RGPD / demande utilisateur)."""
        with _conn() as con:
            # Vérifier que la conversation appartient à l'utilisateur
            row = con.execute(
                "SELECT conv_id FROM conversation_sessions WHERE conv_id=? AND user_id=?",
                (conv_id, user_id)
            ).fetchone()
            if not row:
                return False
            con.execute("DELETE FROM conversations WHERE conv_id=?", (conv_id,))
            con.execute("DELETE FROM conversation_sessions WHERE conv_id=?", (conv_id,))
        return True

    def get_conversation_count(self, user_id: str) -> int:
        """Nombre de conversations d'un utilisateur."""
        with _conn() as con:
            row = con.execute(
                "SELECT COUNT(*) FROM conversation_sessions WHERE user_id=?",
                (user_id,)
            ).fetchone()
        return row[0] if row else 0

    # ── Stats ─────────────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        with _conn() as con:
            learning  = con.execute("SELECT COUNT(*) FROM learning_store").fetchone()[0]
            packs     = con.execute("SELECT COUNT(*) FROM context_packs").fetchone()[0]
            validated = con.execute("SELECT COUNT(*) FROM context_packs WHERE validated=1").fetchone()[0]
            refs      = con.execute("SELECT COUNT(*) FROM reflections").fetchone()[0]
            avg_q     = round(con.execute("SELECT AVG(quality) FROM reflections").fetchone()[0] or 0.0, 3)
            signed    = con.execute("SELECT COUNT(*) FROM signed_documents").fetchone()[0]
            inter     = con.execute("SELECT COUNT(*) FROM user_interactions").fetchone()[0]
            convs     = con.execute("SELECT COUNT(*) FROM conversation_sessions").fetchone()[0]
            msgs      = con.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        return {
            "learning_entries": learning,
            "context_packs":    packs,
            "validated_packs":  validated,
            "reflections":      refs,
            "avg_quality":      avg_q,
            "signed_docs":      signed,
            "interactions":     inter,
            "conversations":    convs,
            "total_messages":   msgs,
        }

    def get_recent_documents(self, limit: int = 100) -> List[dict]:
        """Compatibilité — les docs sont dans PostgreSQL."""
        return []


_instance: Optional[LongTermMemory] = None


def get_long_term_memory() -> LongTermMemory:
    global _instance
    if _instance is None:
        _instance = LongTermMemory()
    return _instance