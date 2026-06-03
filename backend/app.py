import hashlib
import os
import re
import sys
import uuid
import logging
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import httpx

load_dotenv()

class _SilentPollFilter(logging.Filter):
    _SILENT = ("/pending-actions", "/health")
    def filter(self, record):
        msg = record.getMessage()
        return not any(ep in msg for ep in self._SILENT)

logging.getLogger("uvicorn.access").addFilter(_SilentPollFilter())

from core.schemas import (
    ChatRequest, ConfirmActionRequest, InferRequest,
    RetryFilesRequest, ScheduleUpdateRequest, SendSignedRequest, SignRequest,
    NewConversationRequest, ContinueConversationRequest,
    RagIndexRequest, RagSearchRequest, FileSummarizeRequest,
)
from services.folder_scheduler import SCAN_PATH, start_scheduler, stop_scheduler
from memory.long_term           import get_long_term_memory, DB_PATH
from memory.short_term          import get_short_term_memory
from orchestrator import (
    run_chat, run_sign, run_send_signed,
    execute_pending, list_pending_actions, get_reminders,
    summarize_document_files, summarize_specific_file, analyze_document_files, execute_recruitment_decision,  execute_schedule_interview,
    execute_simple_refusal,
)

from ace.ace_router import ace_router


_PREFIX_RE = re.compile(r"^You are helping .+?\. User request:\s*", re.IGNORECASE)

def _clean_message(raw: str) -> str:
    return _PREFIX_RE.sub("", raw).strip()

_whisper_model   = None
_whisper_backend = None   # "faster_whisper" | "openai_whisper" | "openai_api" | "unavailable"
 
 
def _get_whisper_model():
    """Charge le modèle Whisper une seule fois (singleton process-level)."""
    global _whisper_model, _whisper_backend
 
    if _whisper_backend is not None:          # déjà tenté
        return _whisper_model, _whisper_backend
 
    size   = os.getenv("WHISPER_MODEL_SIZE", "small")
    device = os.getenv("WHISPER_DEVICE", "cpu")
 
    # ── Option A : faster-whisper (prioritaire) ───────────────────────────────
    try:
        from faster_whisper import WhisperModel
        compute = "float16" if device == "cuda" else "int8"
        _whisper_model   = WhisperModel(size, device=device, compute_type=compute)
        _whisper_backend = "faster_whisper"
        print(f"[Whisper] faster-whisper chargé | modèle={size} | device={device}",
              file=sys.stderr)
        return _whisper_model, _whisper_backend
    except ImportError:
        print("[Whisper] faster-whisper absent → essai openai-whisper", file=sys.stderr)
    except Exception as e:
        print(f"[Whisper] faster-whisper erreur: {e}", file=sys.stderr)
 
    # ── Option B : openai-whisper ─────────────────────────────────────────────
    try:
        import whisper as _ow
        _whisper_model   = _ow.load_model(size)
        _whisper_backend = "openai_whisper"
        print(f"[Whisper] openai-whisper chargé | modèle={size}", file=sys.stderr)
        return _whisper_model, _whisper_backend
    except ImportError:
        print("[Whisper] openai-whisper absent → essai API OpenAI", file=sys.stderr)
    except Exception as e:
        print(f"[Whisper] openai-whisper erreur: {e}", file=sys.stderr)
 
    # ── Option C : API OpenAI (cloud) ─────────────────────────────────────────
    if os.getenv("OPENAI_API_KEY", ""):
        _whisper_backend = "openai_api"
        print("[Whisper] API OpenAI Whisper activée", file=sys.stderr)
        return None, "openai_api"
 
    # ── Aucune option disponible ──────────────────────────────────────────────
    _whisper_backend = "unavailable"
    print(
        "[Whisper] ⚠ Aucun backend disponible.\n"
        "  → pip install faster-whisper\n"
        "  → pip install openai-whisper\n"
        "  → ou OPENAI_API_KEY=... dans .env",
        file=sys.stderr,
    )
    return None, "unavailable"
 
 
@asynccontextmanager
async def lifespan(app):
    start_scheduler()
    
    # import threading
    # from agents.visual_watcher_agent import VisualWatcherAgent

    # def _start_watcher():
    #     try:
    #         VisualWatcherAgent(debug=False).run_forever()
    #     except Exception as e:
    #         print(f"[VisualWatcherAgent] Arrêt inattendu : {e}", file=sys.stderr)

    # watcher_thread = threading.Thread(target=_start_watcher, daemon=True, name="VisualWatcher")
    # watcher_thread.start()
    # print("[VisualWatcherAgent] Démarré en arrière-plan", file=sys.stderr)

    from ace.playbook_store import load_playbook as _ace_init
    _ace_init()
    print("[ACE] Playbook chargé", file=sys.stderr)
    try:
        _get_whisper_model()
    except Exception as e:
        print(f"[Whisper] Pré-chargement non-bloquant: {e}", file=sys.stderr)
    
    yield
    stop_scheduler()


app = FastAPI(
    title       = "GED Multi-Agents Backend",
    version     = "2.0.0",
    lifespan    = lifespan,
    description = "Backend IA agentique GED ",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:53582",
        "https://localhost:53581",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ace_router)

@app.get("/")
def root():
    return {
        "service": "GED Multi-Agents Backend",
        "version": "2.0.0",
        "docs":    "/docs",
        "features": ["RAG", "conversations", "gmail", "calendar", "legifrance"],
    }

# ── /transcribe — Whisper STT ─────────────────────────────────────────────────
 
@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcrit un audio (webm/ogg/mp4/wav) en texte français via Whisper.
 
    Backends essayés dans l'ordre :
      1. faster-whisper (local, léger, recommandé)
      2. openai-whisper  (local, plus lourd)
      3. API OpenAI Whisper (cloud, nécessite OPENAI_API_KEY)
 
    Corps multipart :
      file: Blob audio
 
    Retourne :
      { text: str, language: str, backend: str }
    """
    model, backend = _get_whisper_model()
 
    if backend == "unavailable":
        raise HTTPException(
            503,
            detail=(
                "Aucun backend Whisper disponible. "
                "Installez faster-whisper (pip install faster-whisper) "
                "ou définissez OPENAI_API_KEY dans .env."
            ),
        )
 
    audio_bytes = await file.read()
    if len(audio_bytes) < 500:
        raise HTTPException(400, detail="Fichier audio vide ou trop court.")
 
    # Déduire l'extension
    ext = ".webm"
    if file.filename:
        _, _ext = os.path.splitext(file.filename)
        if _ext: ext = _ext
    elif file.content_type:
        _ct_map = {
            "audio/webm": ".webm", "audio/webm;codecs=opus": ".webm",
            "audio/ogg": ".ogg", "audio/ogg;codecs=opus": ".ogg",
            "audio/mp4": ".mp4", "audio/mpeg": ".mp3",
            "audio/wav": ".wav", "audio/x-wav": ".wav",
        }
        ext = _ct_map.get(file.content_type, ".webm")
 
    language = os.getenv("WHISPER_LANGUAGE", "fr")
    tmp_path = None
 
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
 
        text = ""
 
        if backend == "faster_whisper":
            segments, _ = model.transcribe(
                tmp_path,
                language=language,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 400},
            )
            text = " ".join(seg.text for seg in segments).strip()
 
        elif backend == "openai_whisper":
            result = model.transcribe(tmp_path, language=language, fp16=False)
            text   = (result.get("text") or "").strip()
 
        elif backend == "openai_api":
            import openai
            openai.api_key = os.getenv("OPENAI_API_KEY", "")
            with open(tmp_path, "rb") as f_audio:
                resp = openai.audio.transcriptions.create(
                    model="whisper-1", file=f_audio, language=language,
                )
            text = (resp.text or "").strip()
 
        if not text:
            return {"text": "", "language": language, "backend": backend,
                    "warning": "Aucune parole détectée — réessayez."}
 
        return {"text": text, "language": language, "backend": backend}
 
    except Exception as e:
        raise HTTPException(500, detail=f"Erreur transcription ({backend}): {str(e)}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.unlink(tmp_path)
            except Exception: pass
 

@app.post("/infer")
def infer(req: InferRequest):
    import sys
    print(f"[DEBUG /infer] resolved='{req.resolved}' | miniged_token={'oui' if req.miniged_token else 'non'}", file=sys.stderr)
    stm = get_short_term_memory()
    if req.document_text:
        stm.set_current_document(
            filename = req.filename or "document",
            text     = req.document_text,
            doc_type = req.document_type or "",
        )
    if req.user_id:
        stm.set_user_id(req.user_id)
    if req.conv_id:
        stm.set_conv_id(req.conv_id)

    effective_doc_id = req.document_id or stm.get_current_miniged_id()
    if req.document_id and req.document_id != stm.get_current_miniged_id():
        stm.set_current_miniged_document(req.document_id, req.filename or "")
    clean_msg = _clean_message(req.resolved)
    history   = [{"role": h.role, "content": h.content} for h in (req.history or [])]

    result = run_chat(
        message       = req.resolved,
        document_type = req.document_type or "",
        filename      = req.filename      or "",
        document_id   = effective_doc_id,
        history       = history,
        miniged_token = req.miniged_token  or "",
        conv_id       = req.conv_id        or stm.get_conv_id(),
        user_id       = req.user_id        or stm.get_user_id(),
    )

    reply  = result.get("reply", "")
    action = result.get("action_done")
    
    _common = {
        "skills_used":      result.get("skills_used", []),
        "ged_search_used":  result.get("ged_search_used", False),
        "web_search_used":  result.get("web_search_used", False),
        "legifrance_used":  result.get("legifrance_used", False),
        "cross_doc_used":   result.get("cross_doc_used", False),
        "quick_commands":   result.get("quick_commands", []),
    }

    if action == "email_draft_ready":
        return {
            "tool_name":       "send_email",
            "action_done":     "email_draft_ready",
            "email_action_id": result.get("email_action_id", ""),
            "email_draft":     result.get("email_draft"),
            "direct_answer":   reply or "Voici le brouillon d'email.",
            "needs_more_info": False,
            "arguments":       {},
            "suggestions":     result.get("proactive_suggestions", [])[:3],
        }

    if action == "summarize":
        return {
            "tool_name":       "summarize",
            "arguments":       {"document_id": effective_doc_id},
            "needs_more_info": False,
            "direct_answer":   result.get("summary") or reply or "Résumé non disponible.",
            "suggestions":     result.get("proactive_suggestions", [])[:3],
        }

    if action in ("sign_requested", "already_signed"):
        return {
            "tool_name":       "sign_document",
            "arguments":       {"filename": req.filename,
                                 "sign_action_id": result.get("sign_action_id", "")},
            "needs_more_info": False,
            "direct_answer":   reply,
            "suggestions":     [],
        }

    if action in ("email_requested", "email_pending_confirm"):
        email_to = result.get("email_to", "")
        filename = req.filename or stm.get_last_filename() or ""
        summary  = stm.get_result("summary") or ""
        if not reply or len(reply) < 50:
            try:
                from services.llm_client import generate_email_body
                reply = generate_email_body(
                    filename=filename, document_type=req.document_type or "",
                    summary=summary, extraction=stm.get_result("extraction") or "")
            except Exception:
                reply = f"Bonjour,\n\nConcernant le document '{filename}'.\n\n{summary[:300]}\n\nCordialement,"
        return {
            "tool_name": "send_email",
            "arguments": {"to": email_to, "filename": filename,
                          "email_action_id": result.get("email_action_id", "")},
            "needs_more_info": not bool(email_to),
            "direct_answer":   reply,
            "suggestions":     result.get("proactive_suggestions", [])[:3],
        }

    if action == "legal_check":
        return {
            "tool_name": "legal_analysis", "arguments": {"document_id": req.document_id},
            "needs_more_info": False, "direct_answer": reply,
            "suggestions": result.get("proactive_suggestions", [])[:3],
        }

    if action == "extract":
        return {
            "tool_name": "extract_fields", "arguments": {"document_id": req.document_id},
            "needs_more_info": False, "direct_answer": reply,
            "suggestions": result.get("proactive_suggestions", [])[:3],
        }

    msg_lower  = clean_msg.lower()
    _search_kw = ["cherche","trouve","recherche","liste-moi","montre-moi",
                  "tous les documents","tous les contrats","quel document","quels documents"]
    if (result.get("ged_search_used") or any(k in msg_lower for k in _search_kw)) \
            and req.miniged_token:
        _stop = {"une","un","des","de","la","le","les","sur","dans","pour","avec",
                 "document","documents","fichier","fichiers","trouve","cherche","recherche",
                 "tous","toutes","moi"}
        words = [w for w in re.sub(r'[^\w\s]', ' ', msg_lower).split()
                 if w not in _stop and len(w) > 2]
        return {
            "tool_name": "search_documents",
            "arguments": {"keyword": " ".join(words[:4]) or clean_msg[:60]},
            "needs_more_info": False, "direct_answer": reply,
            "suggestions": result.get("proactive_suggestions", [])[:3],
        }

    return {
        "tool_name":       "answer",
        "arguments":       {"text": reply},
        "needs_more_info": False,
        "direct_answer":   reply or "Je suis prêt à vous aider.",
        "doc_type": stm.summary().get("current_type", ""),
        "suggestions":     result.get("proactive_suggestions", [])[:3],
    }


@app.post("/chat")
def chat(req: ChatRequest):
    history = [{"role": h.role, "content": h.content} for h in (req.history or [])]
    return run_chat(
        message=req.message, document_type=req.document_type or "",
        filename=req.filename or "", document_id=req.document_id or "",
        history=history, miniged_token=req.miniged_token or "",
        skills=req.skills or [],
        conv_id=req.conv_id or "",
        user_id=req.user_id or "",
    )


@app.post("/conversations/new")
def new_conversation(req: NewConversationRequest):
    conv_id = str(uuid.uuid4())
    stm     = get_short_term_memory()
    stm.set_user_id(req.user_id)
    stm.set_conv_id(conv_id)
    stm.clear_chat_history()

    ltm = get_long_term_memory()
    ltm.save_conversation_message(conv_id, req.user_id, "system",
                                   "Nouvelle conversation démarrée.")
    ltm.update_conversation_session(conv_id, title="Nouvelle conversation")

    result = {"conv_id": conv_id, "user_id": req.user_id, "status": "created"}

    if req.first_message:
        chat_result = run_chat(
            message=req.first_message,
            miniged_token="",
            conv_id=conv_id,
            user_id=req.user_id,
        )
        result["first_reply"] = chat_result.get("reply", "")
        result["suggestions"] = chat_result.get("proactive_suggestions", [])

    return result


@app.post("/conversations/{conv_id}/continue")
def continue_conversation(conv_id: str, req: ContinueConversationRequest):
    if req.conv_id != conv_id:
        raise HTTPException(400, "conv_id mismatch")

    stm = get_short_term_memory()
    stm.set_user_id(req.user_id)
    stm.set_conv_id(conv_id)

    return run_chat(
        message=req.message,
        document_id=req.document_id or "",
        miniged_token=req.miniged_token or "",
        conv_id=conv_id,
        user_id=req.user_id,
    )


@app.get("/conversations")
def list_conversations(user_id: str, limit: int = 20):
    ltm   = get_long_term_memory()
    convs = ltm.list_conversations(user_id, limit=limit)
    return {
        "conversations": convs,
        "total":         len(convs),
        "user_id":       user_id,
    }


@app.get("/conversations/{conv_id}")
def get_conversation(conv_id: str, user_id: str, limit: int = 50):
    ltm      = get_long_term_memory()
    messages = ltm.get_conversation(conv_id, limit=limit)
    if not messages:
        raise HTTPException(404, f"Conversation {conv_id} introuvable")
    return {
        "conv_id":  conv_id,
        "messages": messages,
        "count":    len(messages),
    }


@app.delete("/conversations/{conv_id}")
def delete_conversation(conv_id: str, user_id: str):
    ltm = get_long_term_memory()
    ok  = ltm.delete_conversation(conv_id, user_id)
    if not ok:
        raise HTTPException(404, "Conversation introuvable ou accès refusé")
    return {"deleted": True, "conv_id": conv_id}


@app.post("/rag/index/{document_id}")
def rag_index_document(document_id: str, req: RagIndexRequest):
    try:
        from rag_pipeline import get_rag_pipeline
        from mcp_client   import call_mcp_tool
        from core.constants import MCP_LOCAL
        import json

        raw   = call_mcp_tool(MCP_LOCAL["miniged"], "get_document_text",
                               {"document_id": int(document_id)})
        data  = json.loads(raw)
        files = [
            {
                "file_id":     f.get("fileId"),
                "filename":    f.get("filename"),
                "textContent": f.get("textContent", ""),
            }
            for f in data.get("files", []) if f.get("hasText")
        ]

        if not files:
            return {"status": "skipped", "reason": "no_text", "document_id": document_id}

        user_id = req.user_id or "default"
        result  = get_rag_pipeline().index_multiple_files(
            doc_id=document_id, user_id=user_id, files=files
        )
        return {"status": "ok", "document_id": document_id, **result}

    except Exception as e:
        raise HTTPException(500, f"Erreur indexation RAG: {e}")


@app.post("/rag/index-all")
def rag_index_all(req: RagIndexRequest):
    try:
        from rag_pipeline       import get_rag_pipeline
        from services.miniged_client import list_recent_documents, get_file_text
        from mcp_client         import call_mcp_tool
        from core.constants     import MCP_LOCAL
        import json

        user_id = req.user_id or "default"
        docs    = list_recent_documents(req.miniged_token, limit=100)
        rag     = get_rag_pipeline()
        indexed = 0
        skipped = 0

        for doc in docs:
            doc_id = str(doc.get("id") or doc.get("Id", ""))
            if not doc_id:
                continue
            try:
                raw   = call_mcp_tool(MCP_LOCAL["miniged"], "get_document_text",
                                       {"document_id": int(doc_id)})
                data  = json.loads(raw)
                files = [
                    {
                        "file_id":     f.get("fileId"),
                        "filename":    f.get("filename"),
                        "textContent": f.get("textContent", ""),
                    }
                    for f in data.get("files", []) if f.get("hasText")
                ]
                if files:
                    rag.index_multiple_files(doc_id=doc_id, user_id=user_id, files=files)
                    indexed += 1
                else:
                    skipped += 1
            except Exception:
                skipped += 1

        return {
            "status":  "ok",
            "indexed": indexed,
            "skipped": skipped,
            "user_id": user_id,
            **rag.get_stats(),
        }
    except Exception as e:
        raise HTTPException(500, f"Erreur indexation RAG globale: {e}")


@app.post("/rag/search")
def rag_search(req: RagSearchRequest):
    try:
        from rag_pipeline import get_rag_pipeline
        results = get_rag_pipeline().search(
            query=req.query, user_id=req.user_id, top_k=req.top_k
        )
        return {"query": req.query, "results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(500, f"Erreur recherche RAG: {e}")


@app.get("/rag/stats")
def rag_stats():
    try:
        from rag_pipeline import get_rag_pipeline
        return get_rag_pipeline().get_stats()
    except Exception as e:
        return {"status": f"error: {e}"}


class DocRequest(BaseModel):
    miniged_token: str  = ""
    force:         bool = False
    user_id:       str  = ""


@app.post("/summarize/{document_id}")
def summarize_document(document_id: str, req: DocRequest):
    return summarize_document_files(
        document_id=document_id, miniged_token=req.miniged_token, force=req.force)


@app.post("/summarize/{document_id}/file/{file_id}")
def summarize_file(document_id: str, file_id: str, req: FileSummarizeRequest):
    return summarize_specific_file(
        document_id=document_id, file_id=file_id,
        miniged_token=req.miniged_token,
    )


@app.post("/analyze-document/{document_id}")
def analyze_document_by_id(document_id: str, req: DocRequest):
    if req.user_id:
        get_short_term_memory().set_user_id(req.user_id)
    return analyze_document_files(
        document_id=document_id, miniged_token=req.miniged_token, force=req.force)


class RecruitmentDecisionRequest(BaseModel):
    candidate_id: int
    document_id:  str = ""
    decision:     str      
    notes:        str = ""
 
 
@app.post("/recruitment/decision")
def recruitment_decision(req: RecruitmentDecisionRequest):

    if req.decision not in ("Accepte", "Refuse"):
        raise HTTPException(400, f"Décision invalide : '{req.decision}'. Valeurs : Accepte, Refuse")
 
    result = execute_recruitment_decision(
        candidate_id = req.candidate_id,
        document_id  = req.document_id,
        decision     = req.decision,
        notes        = req.notes,
    )
 
    if not result.get("success"):
        raise HTTPException(500, result.get("error", "Erreur inconnue"))
 
    return result
 
class RhNote(BaseModel):
    sign: str = "+"   # "+" ou "-"
    text: str = ""
 
class ScheduleInterviewRequest(BaseModel):
    candidate_id: int
    document_id:  str
    notes:        str       = ""    # ← NOUVEAU : texte formaté "+/-"
    rh_notes:     List[RhNote] = [] # ← NOUVEAU : structuré pour ACE
 
class SimpleRefusalRequest(BaseModel):
    candidate_id: int
    document_id:  str
    notes:        str       = ""    # ← NOUVEAU
    rh_notes:     List[RhNote] = [] # ← NOUVEAU
 
 
# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.post("/recruitment/schedule-interview")
def schedule_interview(req: ScheduleInterviewRequest):
    return execute_schedule_interview(
        candidate_id = req.candidate_id,
        document_id  = req.document_id,
        notes        = req.notes,
        rh_notes     = [n.dict() for n in req.rh_notes],
    )

@app.post("/recruitment/simple-refusal")
def simple_refusal(req: SimpleRefusalRequest):
    return execute_simple_refusal(
        candidate_id = req.candidate_id,
        document_id  = req.document_id,
        notes        = req.notes,
        rh_notes     = [n.dict() for n in req.rh_notes],
    )

@app.post("/recruitment/restore-pending/{document_id}")
def restore_pending_action(document_id: str):
    """
    Recrée la pending_action 'send_score_email' depuis les données persistées
    en DB .NET (AiScore, AiRecommendation, candidat, résumé).
 
    Appelé par ScoreValidationBanner quand la STM a été vidée (ex: reload backend)
    mais que le candidat est encore en statut 'ATraiter'.
    """
    import uuid, json, requests as req_lib
    from memory.short_term import get_short_term_memory
    from mcp_client        import call_mcp_tool
    from core.constants    import MCP_LOCAL
 
    stm          = get_short_term_memory()
    miniged_base = os.getenv("MINIGED_API_URL", "http://localhost:5092")
 
    try:
        # 1. Récupérer les données AI du document depuis .NET
        doc_resp = req_lib.get(
            f"{miniged_base}/api/dashboard/document/{document_id}", timeout=8)
        if doc_resp.status_code != 200:
            raise HTTPException(404, "Document non trouvé")
        doc_data = doc_resp.json()
 
        ai = doc_data.get("ai", {})
        if not ai.get("isAnalyzed"):
            return {"restored": False, "reason": "not_analyzed"}
 
        # 2. Récupérer les infos candidat depuis MiniGED MCP
        try:
            raw  = call_mcp_tool(MCP_LOCAL["miniged"], "get_candidate",
                                  {"document_id": int(document_id)})
            cand = json.loads(raw) if isinstance(raw, str) else (raw or {})
        except Exception:
            cand = {}
 
        candidate_email = cand.get("email", "")
        candidate_name  = cand.get("name",  "")
        position        = cand.get("position", "")
        candidate_id    = cand.get("candidateId", 0)
        ai_score        = int(cand.get("aiScore") or 0)
        ai_rec          = cand.get("aiRecommendation", "") or ai.get("recommendation", "")
 
        if not candidate_email:
            return {"restored": False, "reason": "no_email"}
 
        # Ne restaurer que si le candidat est encore en ATraiter
        cand_status = cand.get("status", "")
        if cand_status not in ("ATraiter", "Recu", "EnAnalyse"):
            return {"restored": False, "reason": f"status={cand_status} — déjà traité"}
 
        # 3. Reconstruire le corps de l'email depuis EmailAgent
        body_preview    = ""
        subject_preview = ""
        try:
            from agents.email_agent import EmailAgent as _EA
            _ea = _EA()
            _subject, _body = _ea._write_score_email(
                candidate_name = candidate_name,
                position       = position,
                recommendation = ai_rec,
                score          = ai_score,
                strengths      = [],
                gaps           = [],
                summary        = ai.get("summary", ""),
                slot_formatted = "",
                meet_link      = "",
                event_link     = "",
            )
            body_preview    = _body
            subject_preview = _subject
        except Exception:
            pass  # non bloquant
 
        # 4. Reconstruire la suggestion ACE
        ace_suggestion = None
        try:
            from agents.ace_decision_agent import AceDecisionAgent
            ace_result     = AceDecisionAgent().run(
                score          = ai_score,
                recommendation = ai_rec,
                position       = position,
            )
            ace_suggestion = ace_result.get("suggestion")
        except Exception:
            pass
 
        # 5. Recréer la pending_action en STM
        action_id = str(uuid.uuid4())
        stm.add_pending_action(action_id, "send_score_email", {
            "to":             candidate_email,
            "candidate_name": candidate_name,
            "position":       position,
            "score":          ai_score,
            "recommendation": ai_rec,
            "strengths":      [],
            "gaps":           [],
            "summary":        ai.get("summary", ""),
            "slot_formatted": "",
            "meet_link":      "",
            "event_link":     "",
            "ace_suggestion": ace_suggestion,
            "document_id":    document_id,
            "candidate_id":   candidate_id,
            "body_sent":      body_preview,
            "subject_sent":   subject_preview,
        })
 
        return {
            "restored":    True,
            "action_id":   action_id,
            "candidate":   candidate_name,
            "email":       candidate_email,
            "score":       ai_score,
            "reco":        ai_rec,
        }
 
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erreur restauration pending: {e}")

@app.get("/document/{document_id}/ai")
def get_document_ai(document_id: str, authorization: str = Header(default="")):
    try:
        import requests as req_lib
        miniged_base = os.getenv("MINIGED_API_URL", "http://localhost:5092")
        headers = {"Authorization": authorization} if authorization else {}
        resp = req_lib.get(f"{miniged_base}/api/dashboard/document/{document_id}",
                           headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            ai   = data.get("ai", {})
            return {
                "document_id": document_id, "analyzed": ai.get("isAnalyzed", False),
                "document_type": ai.get("documentType", ""), "summary": ai.get("summary", ""),
                "analyzed_at": ai.get("analyzedAt", ""),
                "files": [{"id": f.get("id"), "filename": f.get("filename"),
                           "aiFileType": f.get("aiFileType"), "aiSummary": f.get("aiSummary"),
                           "isAnalyzed": f.get("isAnalyzed", False)}
                          for f in data.get("files", [])],
            }
        return {"document_id": document_id, "analyzed": False, "document_type": "",
                "summary": "", "analyzed_at": "", "files": []}
    except Exception as e:
        raise HTTPException(503, f"MiniGED indisponible : {e}")

@app.get("/trace/{document_id}")
def get_trace(document_id: str):
    """Retourne la dernière trace ReAct pour un document."""
    try:
        import pathlib
        trace_file = pathlib.Path(f"/tmp/ace_traces/trace_{document_id}.json")
        if trace_file.exists() and trace_file.stat().st_size > 10:
            raw = json.loads(trace_file.read_text(encoding="utf-8"))
            # Nouveau format : {steps, processing_ms} — ancien format : liste directe
            if isinstance(raw, dict):
                return {
                    "trace":         raw.get("steps", []),
                    "processing_ms": raw.get("processing_ms", 0),
                    "found":         True,
                }
            return {"trace": raw, "processing_ms": 0, "found": True}
    except Exception:
        pass
    return {"trace": [], "processing_ms": 0, "found": False}

@app.get("/documents/ai-enriched")
def get_documents_ai_enriched(authorization: str = Header(default="")):
    try:
        import requests as req_lib
        resp = req_lib.get(
            f"{os.getenv('MINIGED_API_URL','http://localhost:5092')}/api/dashboard/documents",
            headers={"Authorization": authorization} if authorization else {}, timeout=8)
        return resp.json() if resp.status_code == 200 else {"total": 0, "by_type": {}, "documents": []}
    except Exception as e:
        raise HTTPException(503, f"MiniGED indisponible : {e}")


@app.get("/dashboard/stats")
def get_dashboard_stats(authorization: str = Header(default="")):
    try:
        import requests as req_lib
        resp = req_lib.get(
            f"{os.getenv('MINIGED_API_URL','http://localhost:5092')}/api/dashboard/stats",
            headers={"Authorization": authorization} if authorization else {}, timeout=8)
        return resp.json() if resp.status_code == 200 else \
               {"totalDocuments": 0, "analyzedCount": 0, "byType": {}, "recentAnalyzed": []}
    except Exception as e:
        raise HTTPException(503, f"MiniGED indisponible : {e}")


@app.post("/confirm-action")
def confirm_action(req: ConfirmActionRequest):
    # FIX : on passe payload_override en argument nommé
    # (l'attribut peut être absent dans les anciens schemas — on défend avec getattr)
    payload_override = getattr(req, "payload_override", None) or {}
    return execute_pending(req.action_id, req.confirmed, payload_override)

@app.get("/pending-actions")
def get_pending_actions():
    actions = list_pending_actions()
    # S'assurer que chaque action expose son payload
    # (certaines implémentations short_term le stripent)
    stm = get_short_term_memory()
    enriched = []
    for a in actions:
        action_id = a.get("action_id", "")
        full = stm.get_pending_action(action_id)
        if full:
            enriched.append(full)
        else:
            enriched.append(a)
    return {"actions": enriched}

@app.get("/pending-actions/latest")
def get_latest_pending_action():
    actions = list_pending_actions()
    pending = [a for a in actions if a.get("status") == "pending"]
    if not pending:
        return {"action": None, "message": "Aucune pending_action en attente"}
    latest = sorted(pending, key=lambda a: a.get("created_at", ""), reverse=True)[0]
    return {
        "action":    latest,
        "action_id": latest.get("action_id"),
        "type":      latest.get("action_type"),
        "to":        latest.get("payload", {}).get("to"),
    }

@app.get("/unanalyzed-documents")
def get_unanalyzed_documents():
    """Retourne les documents GED sans analyse IA via l'API .NET directement."""
    try:
        import requests as req_lib
        miniged_base = os.getenv("MINIGED_API_URL", "http://localhost:5092")

        # Appel direct .NET — plus rapide que MCP
        resp = req_lib.get(
            f"{miniged_base}/api/dashboard/documents",
            timeout=8,
        )
        if resp.status_code != 200:
            return {"documents": [], "count": 0}

        data = resp.json()
        all_docs = data.get("documents", data) if isinstance(data, dict) else data

        unanalyzed = [
            {
                "documentId": d.get("id") or d.get("documentId"),
                "title":      d.get("title", ""),
                "id":         d.get("id") or d.get("documentId"),
            }
            for d in all_docs
            if not d.get("aiAnalyzedAt") and not d.get("isAnalyzed")
            and (d.get("id") or d.get("documentId"))
        ]
        return {"documents": unanalyzed, "count": len(unanalyzed)}
    except Exception as e:
        return {"documents": [], "count": 0, "error": str(e)}

@app.post("/sign")
def sign(req: SignRequest):
    # Résoudre user_id depuis STM si non fourni dans la requête
    _user_id = req.user_id or get_short_term_memory().get_user_id()
    result = run_sign(
        pdf_base64    = req.pdf_base64,
        signature_png = req.signature_png,
        signer_name   = req.signer_name,
        page          = req.page,
        x             = req.x,
        y             = req.y,
        width         = req.width,
        height        = req.height,
        filename      = req.filename,
        user_id       = _user_id,
        document_type = req.document_type,
    )
    if not result.get("signed") and not result.get("already_signed"):
        raise HTTPException(500, result.get("error", "Erreur signature"))
    return result
 
 
@app.get("/signature/profile")
def get_signature_profile(user_id: str = ""):
    """
    Retourne le profil de signature mémorisé d'un utilisateur.
    Utile pour le frontend : afficher le nombre de confirmations,
    si le mode automatique est actif, et quel signataire est enregistré.
    """
    _uid = user_id or get_short_term_memory().get_user_id()
    if not _uid:
        return {"user_id": "", "confirmations": 0, "auto_enabled": False,
                "signer_name": "", "doc_types": []}
    from agents.signature_agent import SignatureAgent
    profile = SignatureAgent().get_profile(_uid)
    # Ne pas exposer la PNG base64 dans l'API (données sensibles)
    return {k: v for k, v in profile.items() if k != "signature_png"}
 
 
@app.post("/send-signed")
def send_signed(req: SendSignedRequest):
    result = run_send_signed(req.to, req.subject, req.body, req.pdf_base64, req.filename)
    if not result.get("success"):
        raise HTTPException(500, result.get("error", "Erreur envoi email"))
    return result

@app.get("/history")
def get_history(limit: int = 100):
    docs = get_long_term_memory().get_recent_documents(limit)
    return {"documents": docs, "count": len(docs)}


@app.get("/reminders")
def get_reminders_endpoint(days_ahead: int = 30):
    return get_reminders(days_ahead)


@app.get("/stats")
def get_stats():
    stats = get_long_term_memory().get_stats()

    # ── Temps moyen réel depuis les traces sur disque ─────────────────────────
    avg_processing_ms = 0
    try:
        import pathlib, json as _json
        trace_dir = pathlib.Path("/tmp/ace_traces")
        ms_values = []
        if trace_dir.exists():
            for f in trace_dir.glob("trace_*.json"):
                try:
                    data = _json.loads(f.read_text(encoding="utf-8"))
                    # Nouveau format : {steps: [...], processing_ms: N}
                    if isinstance(data, dict) and "processing_ms" in data:
                        ms_values.append(data["processing_ms"])
                    # Ancien format : liste de steps avec champ ms sur le dernier
                    elif isinstance(data, list) and data:
                        last_ms = next((s.get("ms", 0) for s in reversed(data) if s.get("ms")), 0)
                        if last_ms:
                            ms_values.append(last_ms)
                except Exception:
                    pass
        if ms_values:
            avg_processing_ms = int(sum(ms_values) / len(ms_values))
    except Exception:
        pass

    # ── signed_count depuis la LTM ────────────────────────────────────────────
    signed_count = stats.get("signed_docs", 0) or stats.get("signed_count", 0)

    return {
        "total_docs":        stats.get("total", 0),
        "avg_processing_ms": avg_processing_ms,
        "type_distribution": stats.get("by_type", {}),
        "signed_count":      signed_count,
        "conversations":     stats.get("conversations", 0),
        "total_messages":    stats.get("total_messages", 0),
    }

@app.get("/health")
def health():
    try:
        from rag_pipeline import get_rag_pipeline
        rag_stats = get_rag_pipeline().get_stats()
    except Exception:
        rag_stats = {"status": "not_initialized"}

    return {
        "status": "ok", "version": "2.0.0", "port": 8000,
        "llm": {
            "provider": "Groq",
            "model":    os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
            "key_set":  bool(os.getenv("GROQ_API_KEY")),
        },
        "db":  DB_PATH,
        "rag": rag_stats,
        "gmail_token":    os.path.exists(os.getenv("GOOGLE_TOKEN_PATH", "./data/token.json")),
        "gmail_creds":    os.path.exists(os.getenv("GOOGLE_CREDENTIALS_PATH", "./data/credentials.json")),
    }


import uvicorn
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)