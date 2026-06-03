from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator
from core.constants import DocType, WorkflowID


# ── Entités MiniGED ───────────────────────────────────────────────────────────

class MiniGedFile(BaseModel):
    file_id:      str
    filename:     str
    content_type: str = "application/octet-stream"
    size_bytes:   int = 0
    text_content: str = ""
    content_hash: str = ""
    page_count:   int = 0


class MiniGedDocument(BaseModel):
    document_id:   str
    document_name: str
    owner_id:      str = ""
    owner_name:    str = ""
    files:         List[MiniGedFile] = []
    tags:          List[str]         = []
    folder_path:   str               = ""
    created_at:    str               = ""
    miniged_token: str               = ""


# ── Tâches et suggestions ─────────────────────────────────────────────────────

class TaskItem(BaseModel):
    title:           str
    description:     str   = ""
    priority:        str   = "Moyenne"
    due_date:        str   = ""
    source:          str   = ""
    miniged_task_id: Optional[str] = None


class SuggestionItem(BaseModel):
    label:    str
    action:   str
    score:    int            = 0
    prefill:  str            = ""
    workflow: Optional[str]  = None
    icon:     str            = ""


# ── Chat / Infer ──────────────────────────────────────────────────────────────

class HistoryItem(BaseModel):
    role:    str
    content: str


class ChatRequest(BaseModel):
    message:       str
    document_type: str               = ""
    filename:      str               = ""
    document_id:   str               = ""
    history:       List[HistoryItem] = []
    miniged_token: str               = ""
    skills:        List[str]         = []
    conv_id:       str               = ""
    user_id:       str               = ""


class InferRequest(BaseModel):
    model_config = {"populate_by_name": True}

    message:      Optional[str] = None
    user_message: Optional[str] = None

    miniged_token: str = Field(default="", alias="minigedToken")
    document_id:   str = Field(default="", alias="documentId")
    document_type: str = Field(default="", alias="documentType")
    filename:      str = Field(default="", alias="filename")

    session_id:    str               = ""
    conv_id:       str               = ""
    user_id:       str               = ""
    document_text: str               = ""
    history:       List[HistoryItem] = []

    @model_validator(mode="after")
    def resolve_message(self) -> "InferRequest":
        if not self.user_message:
            self.user_message = self.message or ""
        return self

    @property
    def resolved(self) -> str:
        return self.user_message or self.message or ""


class InferResponse(BaseModel):
    tool_name:       str
    arguments:       Dict[str, Any]        = {}
    needs_more_info: bool                  = False
    direct_answer:   str                   = ""
    suggestions:     List[SuggestionItem]  = []


# ── Actions HITL ──────────────────────────────────────────────────────────────

class ConfirmActionRequest(BaseModel):
    action_id:        str
    confirmed:        bool = True
    payload_override: dict = {}
 
 
class SignRequest(BaseModel):
    pdf_base64:    str
    signature_png: str
    signer_name:   str   = "Signataire"
    filename:      str   = ""
    document_id:   str   = ""
    page:          int   = -1      # -1 = dernière page (défaut SignatureAgent)
    x:             float = 80.0
    y:             float = 60.0
    width:         float = 200.0   # aligné avec SignatureAgent
    height:        float = 60.0    # aligné avec SignatureAgent
    user_id:       str   = ""    # pour apprentissage profil
    document_type: str   = ""    # pour apprentissage profil
 
 
class SendSignedRequest(BaseModel):
    to:          str
    subject:     str
    body:        str
    pdf_base64:  str
    filename:    str = "document_signe.pdf"
    document_id: str = ""


class ScheduleUpdateRequest(BaseModel):
    hour:         int
    minute:       int
    folder_path:  str
    notify_email: str


class RetryFilesRequest(BaseModel):
    folder_path:    str
    selected_files: Optional[List[str]] = None


class FolderAnalysisRequest(BaseModel):
    folder_path: str
    objective:   str           = "Analyse tous les documents de ce dossier"
    file_filter: Optional[str] = None
    output_file: Optional[str] = None


# ── Conversations persistantes ────────────────────────────────────────────────

class NewConversationRequest(BaseModel):
    user_id:       str
    first_message: Optional[str] = None


class ContinueConversationRequest(BaseModel):
    conv_id:       str
    user_id:       str
    message:       str
    miniged_token: str = ""
    document_id:   str = ""


class ConversationListResponse(BaseModel):
    conversations: List[dict]
    total:         int


# ── RAG ───────────────────────────────────────────────────────────────────────

class RagIndexRequest(BaseModel):
    miniged_token: str = ""
    user_id:       str = ""


class RagSearchRequest(BaseModel):
    query:   str
    user_id: str
    top_k:   int = 5


class FileSummarizeRequest(BaseModel):
    miniged_token: str = ""


# ── Recrutement ───────────────────────────────────────────────────────────────

class RecruitmentDecisionRequest(BaseModel):
    candidate_id: int
    document_id:  str = ""
    decision:     str           # "Accepte" ou "Refuse"
    notes:        str = ""


