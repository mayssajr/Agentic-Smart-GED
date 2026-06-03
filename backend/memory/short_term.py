from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class ShortTermMemory:

    def __init__(self) -> None:
        self._lock             = threading.Lock()
        self._current_doc:     Dict[str, Any]  = {}
        self._results:         Dict[str, Any]  = {}
        self._chat_history:    List[Dict]      = []
        self._pending_actions: Dict[str, Dict] = {}
        self._signed_docs:     Dict[str, Dict] = {}
        self._conv_id:         str             = ""   
        self._user_id:         str             = ""   


    def set_current_document(self, filename: str, text: str = "",
                              doc_type: str = "", confidence: float = 0.0,
                              content_hash: str = "") -> None:
        with self._lock:
            self._current_doc = {
                "filename":     filename,
                "text":         text,
                "doc_type":     doc_type,
                "confidence":   confidence,
                "content_hash": content_hash,
                "set_at":       datetime.now(timezone.utc).isoformat(),
            }

    def set_current_miniged_document(self, document_id: str,
                                     doc_title: str = "",
                                     doc_type: str = "") -> None:
        with self._lock:
            self._current_doc.update({
                "miniged_document_id": document_id,
                "filename":            doc_title or self._current_doc.get("filename", ""),
                "doc_type":            doc_type or self._current_doc.get("doc_type", ""),
                "set_at":              datetime.now(timezone.utc).isoformat(),
            })

    def get_current_miniged_id(self) -> str:
        with self._lock:
            return self._current_doc.get("miniged_document_id", "")

    def get_document_text(self, filename: str = "") -> str:
        with self._lock:
            if filename and self._current_doc.get("filename") != filename:
                return ""
            return self._current_doc.get("text", "")

    def get_last_filename(self) -> str:
        with self._lock:
            return self._current_doc.get("filename", "")

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "current_filename":    self._current_doc.get("filename", ""),
                "current_type":        self._current_doc.get("doc_type", ""),
                "current_confidence":  self._current_doc.get("confidence", 0.0),
                "miniged_document_id": self._current_doc.get("miniged_document_id", ""),
                "pending_count":       len(self._pending_actions),
                "chat_turns":          len(self._chat_history),
                "conv_id":             self._conv_id,
                "user_id":             self._user_id,
            }


    def set_result(self, key: str, value: Any) -> None:
        with self._lock:
            self._results[key] = value

    def get_result(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._results.get(key, default)

    def add_chat_message(self, role: str, content: str) -> None:
        with self._lock:
            self._chat_history.append({
                "role":    role,
                "content": content,
                "at":      datetime.now(timezone.utc).isoformat(),
            })
            if len(self._chat_history) > 30:
                self._chat_history = self._chat_history[-30:]

    def get_chat_history(self, last_n: int = 10) -> List[Dict[str, str]]:
        with self._lock:
            return [
                {"role": m["role"], "content": m["content"]}
                for m in self._chat_history[-last_n:]
            ]

    def clear_chat_history(self) -> None:
        with self._lock:
            self._chat_history = []
            self._results      = {}
            self._current_doc  = {}


    def set_conv_id(self, conv_id: str) -> None:
        with self._lock:
            self._conv_id = conv_id

    def get_conv_id(self) -> str:
        with self._lock:
            return self._conv_id

    def set_user_id(self, user_id: str) -> None:
        with self._lock:
            self._user_id = user_id

    def get_user_id(self) -> str:
        with self._lock:
            return self._user_id

    def add_pending_action(self, action_id: str, action_type: str,
                            payload: Dict[str, Any]) -> None:
        with self._lock:
            self._pending_actions[action_id] = {
                "action_id":   action_id,
                "action_type": action_type,
                "payload":     payload,
                "status":      "pending",
                "created_at":  datetime.now(timezone.utc).isoformat(),
            }

    def get_pending_action(self, action_id: str) -> Optional[Dict]:
        with self._lock:
            return self._pending_actions.get(action_id)

    def update_action_status(self, action_id: str, status: str) -> None:
        with self._lock:
            if action_id in self._pending_actions:
                self._pending_actions[action_id]["status"] = status

    def list_pending_actions(self) -> List[Dict]:
        with self._lock:
            return [
                {k: v for k, v in a.items() if k != "payload"}
                for a in self._pending_actions.values()
                if a["status"] == "pending"
            ]


    def mark_signed(self, filename: str, signer_name: str) -> None:
        with self._lock:
            self._signed_docs[filename] = {
                "filename":  filename,
                "signer":    signer_name,
                "signed_at": datetime.now(timezone.utc).isoformat(),
            }

    def is_signed(self, filename: str) -> bool:
        with self._lock:
            return filename in self._signed_docs

    def get_signature_info(self, filename: str) -> Optional[Dict]:
        with self._lock:
            return self._signed_docs.get(filename)


_instance: Optional[ShortTermMemory] = None


def get_short_term_memory() -> ShortTermMemory:
    global _instance
    if _instance is None:
        _instance = ShortTermMemory()
    return _instance