from __future__ import annotations

import hashlib
import os
import sqlite3
import sys
import threading
import time
from datetime import datetime, timezone
from typing import List, Optional

from core.constants import DB_PATH

# Parse FOLDER_SCAN_TIME=HH:MM
_raw       = os.getenv("FOLDER_SCAN_TIME", "08:00").split(":")
SCAN_HOUR  = int(_raw[0]) if len(_raw) >= 1 else 8
SCAN_MIN   = int(_raw[1]) if len(_raw) >= 2 else 0

SCAN_PATH  = os.path.abspath(os.getenv("FOLDER_SCAN_PATH", "./contrats"))
SCAN_EMAIL = os.getenv("FOLDER_SCAN_EMAIL", "")

_scheduler_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
_schedule   = {"hour": SCAN_HOUR, "minute": SCAN_MIN, "active": False}


def _conn():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""
        CREATE TABLE IF NOT EXISTS folder_file_states (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_path  TEXT NOT NULL,
            filename     TEXT NOT NULL,
            file_hash    TEXT DEFAULT '',
            last_processed TEXT DEFAULT '',
            status       TEXT DEFAULT 'pending',
            UNIQUE(folder_path, filename) ON CONFLICT REPLACE
        )
    """)
    con.commit()
    return con


def _file_hash(path: str) -> str:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()[:16]
    except Exception:
        return ""


def get_scheduler_status() -> dict:
    return {
        "active":   _schedule["active"],
        "hour":     _schedule["hour"],
        "minute":   _schedule["minute"],
        "next_run": f"{_schedule['hour']:02d}:{_schedule['minute']:02d}",
    }


def get_file_states(folder_path: str) -> List[dict]:
    con  = _conn()
    rows = con.execute(
        "SELECT * FROM folder_file_states WHERE folder_path=? ORDER BY last_processed DESC",
        (folder_path,)
    ).fetchall()
    cols = [d[0] for d in con.execute(
        "SELECT * FROM folder_file_states LIMIT 0"
    ).description or []]
    con.close()
    if not cols:
        return []
    return [dict(zip(cols, r)) for r in rows]


def get_last_run(folder_path: str) -> Optional[str]:
    con = _conn()
    row = con.execute(
        "SELECT MAX(last_processed) FROM folder_file_states WHERE folder_path=?",
        (folder_path,)
    ).fetchone()
    con.close()
    return row[0] if row and row[0] else None


def update_schedule(hour: int, minute: int,
                    folder_path: str, notify_email: str) -> bool:
    global SCAN_PATH, SCAN_EMAIL
    _schedule["hour"]   = hour
    _schedule["minute"] = minute
    SCAN_PATH  = folder_path
    SCAN_EMAIL = notify_email
    return True


def run_scheduled_scan(
    folder_path:    str           = SCAN_PATH,
    notify_email:   str           = SCAN_EMAIL,
    selected_files: Optional[List[str]] = None,
) -> dict:
    if not os.path.isdir(folder_path):
        return {"error": f"Dossier introuvable: {folder_path}"}

    _SUPPORTED = {".pdf", ".docx", ".doc", ".txt", ".md"}
    all_files  = [
        f for f in os.listdir(folder_path)
        if os.path.splitext(f.lower())[1] in _SUPPORTED
        and (not selected_files or f in selected_files)
    ]

    con = _conn()
    new_or_changed = []
    for fname in all_files:
        fhash = _file_hash(os.path.join(folder_path, fname))
        row   = con.execute(
            "SELECT file_hash FROM folder_file_states WHERE folder_path=? AND filename=?",
            (folder_path, fname)
        ).fetchone()
        if not row or row[0] != fhash:
            new_or_changed.append((fname, fhash))

    processed, errors = [], []

    from services.document_parser import extract_text
    from core.constants import WorkflowID

    for fname, fhash in new_or_changed:
        fpath = os.path.join(folder_path, fname)
        try:
            with open(fpath, "rb") as f:
                content = f.read()
            text = extract_text(fname, content)
            if text.strip():
                from orchestrator import run_analysis
                run_analysis(text=text, filename=fname,
                             workflows=[WorkflowID.CLASSIFY, WorkflowID.SUMMARIZE])
                con.execute(
                    "INSERT OR REPLACE INTO folder_file_states "
                    "(folder_path, filename, file_hash, last_processed, status) "
                    "VALUES (?,?,?,?,?)",
                    (folder_path, fname, fhash,
                     datetime.now(timezone.utc).isoformat(), "processed")
                )
                con.commit()
                processed.append(fname)
        except Exception as e:
            errors.append(fname)
            print(f"[Scheduler] Erreur '{fname}': {e}", file=sys.stderr)

    con.close()

    if processed and notify_email:
        try:
            from agents.email_agent import EmailAgent
            EmailAgent().run(
                mode    = "report",
                to      = notify_email,
                subject = f"GED — Scan dossier ({len(processed)} nouveaux)",
                body    = (
                    f"Scan de : {folder_path}\n\n"
                    f"Traites ({len(processed)}) :\n"
                    + "\n".join(f"  - {f}" for f in processed)
                    + (f"\n\nErreurs : {', '.join(errors)}" if errors else "")
                ),
            )
        except Exception as e:
            print(f"[Scheduler] Email notification failed: {e}", file=sys.stderr)

    return {
        "processed": processed,
        "errors":    errors,
        "total_new": len(new_or_changed),
        "folder":    folder_path,
    }


def _loop() -> None:
    _schedule["active"] = True
    print("[Scheduler] Demarre", file=sys.stderr, flush=True)
    while not _stop_event.is_set():
        now = datetime.now()
        if now.hour == _schedule["hour"] and now.minute == _schedule["minute"] \
                and now.second < 30:
            run_scheduled_scan()
            time.sleep(60)
        time.sleep(20)
    _schedule["active"] = False


def start_scheduler() -> bool:
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        return True
    _stop_event.clear()
    _scheduler_thread = threading.Thread(target=_loop, daemon=True)
    _scheduler_thread.start()
    return True


def stop_scheduler() -> None:
    _stop_event.set()