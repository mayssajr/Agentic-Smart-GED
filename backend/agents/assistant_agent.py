from __future__ import annotations
import json
import os
import re
import uuid
from typing import List, Optional, Set

from agents.base_agent import BaseAgent
from core.constants import MCP_SPECS, SkillID

_PREFIX_RE = re.compile(r"^You are helping .+?\. User request:\s*", re.IGNORECASE)

_TRIGGERS: dict[SkillID, list[str]] = {
    SkillID.TIME_GET: [
        r"\bheure\b", r"\baujourd'?hui\b", r"\bquel\s+jour\b",
        r"\bdate\s+(?:du\s+jour|actuelle)\b",
    ],
    SkillID.CALENDAR_READ: [
        r"\bagenda\b", r"\bcalendrier\b",
        r"\bprochains?\s+(?:rendez[-\s]?vous|événements?)\b",
    ],
    SkillID.CALENDAR_WRITE: [
        r"\bcréer?\s+(?:un\s+)?rappel\b", r"\bplanifier?\b",
        r"\bajouter?\s+au\s+(?:calendrier|agenda)\b",
        r"\borganiser?\s+(?:un\s+)?(?:rendez[-\s]?vous|réunion|entretien)\b",
    ],
    SkillID.FILESYSTEM_LIST: [
        r"\b(?:liste[rz]?|affiche[rz]?|montre[rz]?)\s+fichiers?\s+(?:locaux?|du\s+dossier)\b",
    ],
    SkillID.FILESYSTEM_READ: [
        r"\b\w[\w\s\-]*\.(?:pdf|docx?|txt|xlsx?)\b",
    ],
    SkillID.MEMORY_READ: [
        r"\btu\s+(?:te\s+)?souviens\b", r"\bprécédemment\b",
        r"\bla\s+derni(?:ère|er)\s+fois\b",
    ],
    SkillID.WEB_FETCH: [
        r"\brecherche\b", r"\btrouve[r]?\b", r"https?://",
        r"\bsur\s+(?:internet|le\s+web)\b",
    ],
    SkillID.GED_SEARCH: [
        r"\btous\s+les\s+documents?\b",
        r"\bdans\s+(?:le\s+)?ged\b",
        r"\btrouv(?:e|er)\s+(?:le\s+)?(?:document|contrat|fichier)\b",
        r"\bcombien\s+(?:de\s+)?(?:documents?|fichiers?|contrats?|candidatures?)\b",
        r"\bnombre\s+(?:de\s+)?(?:documents?|fichiers?)\b",
        r"\bliste[rz]?\s+(?:les?\s+)?(?:documents?|contrats?|candidatures?)\b",
        r"\bmes\s+documents?\b",
    ],
    SkillID.LEGIFRANCE_CODE: [
        r"\barticle\s+[LRD]?\s*\d+", r"\bcode\s+du\s+travail\b",
        r"\bjurisprudence\b", r"\blegifrance\b",
        r"\bdroit\s+(?:du\s+travail|civil|pénal|français)\b",
    ],
    SkillID.EMAIL_REPORT: [
        r"\benvoie[rz]?\b", r"\bmail\b", r"\bemail\b",
        r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}",
    ],
    SkillID.EMAIL_ATTACHMENT: [
        r"\benvoie[rz]?\s+(?:le\s+)?(?:document|fichier|pdf|cv|candidature|contrat)\b",
        r"\bjoindre?\b", r"\bpièce\s+jointe\b",
        r"\benvoyer?\s+(?:avec|en\s+pièce)\b",
    ],
}

_EMAIL_RE  = re.compile(r'[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}')
_STOP_WDS  = {"une","un","des","de","la","le","les","sur","en","dans",
              "pour","avec","par","que","qui","est","sont"}
_GREETINGS = re.compile(
    r"^(bonjour|bonsoir|salut|hello|hi|hey|coucou|merci|ok|oui|non|"
    r"d'accord|parfait|super|génial|ça\s+va)\W*$",
    re.IGNORECASE,
)

_SKILL_DESCRIPTIONS = {
    SkillID.TIME_GET:         "obtenir l'heure ou la date actuelle",
    SkillID.CALENDAR_READ:    "consulter l'agenda ou les événements à venir",
    SkillID.CALENDAR_WRITE:   "créer un rappel ou planifier un événement",
    SkillID.FILESYSTEM_LIST:  "lister les fichiers locaux du dossier GED",
    SkillID.FILESYSTEM_READ:  "lire le contenu d'un fichier local",
    SkillID.MEMORY_READ:      "rappeler une information mémorisée précédemment",
    SkillID.WEB_FETCH:        "rechercher sur internet",
    SkillID.GED_SEARCH:       "chercher ou lister des documents dans le GED",
    SkillID.LEGIFRANCE_CODE:  "chercher une information juridique française",
    SkillID.EMAIL_REPORT:     "envoyer un email à un destinataire",
    SkillID.EMAIL_ATTACHMENT: "envoyer un email avec une pièce jointe PDF du GED",
    SkillID.MEMORY_WRITE:     "mémoriser une information",
    SkillID.RAG_SEARCH: "recherche transversale dans tous les documents indexés",
}


class AssistantAgent(BaseAgent):
    NAME = "AssistantAgent"
    SKILLS = [s.value for s in [
        SkillID.GED_SEARCH, SkillID.WEB_FETCH, SkillID.TIME_GET,
        SkillID.CALENDAR_READ, SkillID.CALENDAR_WRITE,
        SkillID.MEMORY_READ, SkillID.MEMORY_WRITE,
        SkillID.FILESYSTEM_LIST, SkillID.FILESYSTEM_READ,
        SkillID.EMAIL_REPORT, SkillID.EMAIL_ATTACHMENT,
        SkillID.RAG_SEARCH,
    ]]
    SYSTEM_PROMPT = (
        "Tu es l'assistant GED intelligent de MiniGED, destiné aux équipes RH et aux gestionnaires de documents. "
        "Tu parles TOUJOURS à un utilisateur RH (recruteur, responsable RH), JAMAIS au candidat. "
        "Quand un [CONTEXTE CANDIDATURE] est présent, tu parles du candidat à la troisième personne : "
        "'ce candidat', 'il/elle', 'son score', 'sa candidature' — jamais 'vous' en référence au candidat. "
        "Tu réponds aux questions du RH sur les documents, les candidatures, les scores IA, et le GED. "
        "Tu utilises le RAG pour répondre précisément à partir du contenu des documents. "
        "Tu cites tes sources (nom du document). Tu n'inventes pas de données. "
        "Tu peux envoyer des emails, créer des événements calendrier. "
        "Tu réponds TOUJOURS en français."
    )

    def _clean(self, text: str) -> str:
        return _PREFIX_RE.sub("", text).strip()

    def _is_trivial(self, msg: str) -> bool:
        return len(msg.strip().split()) <= 2 and bool(_GREETINGS.match(msg.strip()))

    def _detect_skills(self, message: str, explicit: list) -> Set[SkillID]:
        active: Set[SkillID] = set()
        for s in explicit:
            try: active.add(SkillID(s))
            except ValueError: pass

        if len(message.strip().split()) <= 3:
            for skill, patterns in _TRIGGERS.items():
                if any(re.search(p, message, re.IGNORECASE) for p in patterns):
                    active.add(skill)
            if SkillID.EMAIL_ATTACHMENT in active:
                active.discard(SkillID.EMAIL_REPORT)
            return active

        try:
            from services.llm_client import generate
            skill_list = "\n".join(f"- {s.value}: {d}" for s, d in _SKILL_DESCRIPTIONS.items())
            raw = generate(
                f"Message: \"{message[:300]}\"\n\nSkills:\n{skill_list}\n\n"
                "Réponds UNIQUEMENT avec les skills nécessaires séparés par virgules. "
                "Si aucun: none",
                max_tokens=60,
                system="Routeur de skills. Réponds en anglais avec les noms exacts.",
            ).strip()
            if raw.lower() != "none":
                for name in raw.replace(" ", "").split(","):
                    try: active.add(SkillID(name.strip()))
                    except ValueError: pass
        except Exception:
            pass

        for skill, patterns in _TRIGGERS.items():
            if any(re.search(p, message, re.IGNORECASE) for p in patterns):
                active.add(skill)

        if SkillID.EMAIL_ATTACHMENT in active:
            active.discard(SkillID.EMAIL_REPORT)
            
        _CROSS_DOC = [
            r"\bmeilleur\s+candidat\b", r"\bcompar(?:er?|aison)\b",
            r"\bparmi\s+(?:tous|les)\b", r"\btous\s+les\s+(?:cv|candidats|dossiers)\b",
            r"\bclasser\b", r"\bclassement\b",
        ]
        if any(re.search(p, message, re.IGNORECASE) for p in _CROSS_DOC):
            active.add(SkillID.GED_SEARCH)
            active.add(SkillID.RAG_SEARCH)

        return active


    def _skill_time(self, message: str) -> str:
        try:
            raw = self._call_tool(MCP_SPECS["time"], "get_current_time", {})
            return f"[Heure]\n{str(raw)[:200]}" if raw else ""
        except Exception:
            from datetime import datetime
            return f"[Heure] {datetime.now().strftime('%d/%m/%Y %H:%M')}"

    def _skill_ged_search(self, message: str, miniged_token: str = "", user_id: str = "") -> str:
        self._step("action", "GED_SEARCH → RAG + MiniGED API")
        parts    = []
        rag_found = False

        # ── Extraire le nom propre pour une query RAG plus précise ───────────────
        rag_query = message  # query par défaut = message complet
        name_match = re.search(
            r'\b([A-ZÀÂÉÈÊËÎÏÔÙÛÜ][a-zàâéèêëîïôùûü]+(?:\s+[A-ZÀÂÉÈÊËÎÏÔÙÛÜ][a-zàâéèêëîïôùûü]+)+)\b',
            message
        )
        if name_match:
            rag_query = name_match.group(1)  # ex: "Lucas Bernard"
            self._step("observe", f"RAG query épurée → '{rag_query}'")

        if user_id:
            try:
                from rag_pipeline import get_rag_pipeline
                rag_pipeline = get_rag_pipeline()

                rag_results = rag_pipeline.search(
                    query=rag_query,  # ← nom propre seul, pas toute la phrase
                    user_id=user_id,
                    top_k=5
                )

                if rag_results:
                    rag_found = True

                    # Mettre à jour la STM avec le doc le plus pertinent
                    first         = rag_results[0]
                    rag_doc_id    = str(first.get("doc_id", ""))
                    rag_doc_title = first.get("filename", "")
                    if rag_doc_id:
                        try:
                            from memory.short_term import get_short_term_memory
                            get_short_term_memory().set_current_miniged_document(
                                rag_doc_id, rag_doc_title
                            )
                            self._step("observe",
                                f"RAG STM: doc_id={rag_doc_id} '{rag_doc_title}'")
                        except Exception:
                            pass

                    # Formater pour le prompt LLM
                    seen_docs = set()
                    rag_parts = ["=== RECHERCHE SÉMANTIQUE (RAG) ==="]
                    for r in rag_results:
                        doc_key = r["doc_id"]
                        header  = f"[{r['filename']}]" if r["filename"] else f"[Doc {r['doc_id']}]"
                        if r.get("doc_type"):
                            header += f" ({r['doc_type']})"
                        if doc_key not in seen_docs:
                            rag_parts.append(f"\n{header}")
                            seen_docs.add(doc_key)
                        rag_parts.append(r["text"][:500])
                    rag = "\n".join(rag_parts)
                    parts.append(rag)
                    self._step("observe", f"RAG: {len(rag)} chars | {len(seen_docs)} docs")

            except Exception as e:
                self._step("observe", f"RAG failed: {e}")

        if miniged_token:
            try:
                from services.miniged_client import search_documents, list_recent_documents
                results = search_documents(message[:200], miniged_token, limit=8)
                self._step("observe", f"MiniGED search: {len(results)} résultats")

                if results:
                    first = results[0]
                    doc_id = str(first.get("documentId") or first.get("id") or "")
                    if doc_id:
                        try:
                            from memory.short_term import get_short_term_memory
                            get_short_term_memory().set_current_miniged_document(
                                doc_id,
                                first.get("documentTitle") or first.get("title") or "",
                            )
                        except Exception:
                            pass
                    for r in results:
                        title = (r.get("documentTitle") or r.get("title")
                                or r.get("fileName", "Doc"))
                        snippet = (r.get("snippet", "") or r.get("documentDescription", ""))[:400]
                        parts.append(f"[{title}]\n{snippet}" if snippet else f"[{title}]")

                elif not rag_found:
                    # ← Liste récente SEULEMENT si le RAG n'a rien trouvé non plus
                    self._step("observe", "0 résultats MiniGED ET RAG vide → liste récente")
                    recent = list_recent_documents(miniged_token, limit=20)
                    if recent:
                        lines = [f"Le GED contient {len(recent)} document(s) :"]
                        for d in recent[:10]:
                            t = d.get("title") or d.get("Title") or d.get("name", "Document")
                            lines.append(f"• {t}")
                        if len(recent) > 10:
                            lines.append(f"... et {len(recent) - 10} autre(s)")
                        parts.append("\n".join(lines))

            except Exception as e:
                self._step("observe", f"MiniGED ERREUR: {e}")

        # Cross-doc (inchangé)
        _CROSS = [r"\bmeilleur\b", r"\bcompar", r"\bparmi\s+tous\b", r"\bclasse"]
        if user_id and any(re.search(p, message, re.IGNORECASE) for p in _CROSS):
            try:
                from rag_pipeline import get_rag_pipeline
                cross = get_rag_pipeline().search(query=message, user_id=user_id, top_k=10)
                if cross:
                    seen = {}
                    for r in cross:
                        did = r.get("doc_id", "")
                        if did not in seen:
                            seen[did] = r
                    lines = ["[COMPARAISON MULTI-DOCUMENTS]"]
                    for r in list(seen.values())[:6]:
                        lines.append(
                            f"• {r.get('filename', '?')} (score={r.get('score', 0):.2f}) :\n"
                            f"  {r.get('text', '')[:300]}"
                        )
                    parts.append("\n".join(lines))
                    self._step("observe", f"Cross-doc RAG: {len(seen)} documents distincts")
            except Exception as e:
                self._step("observe", f"Cross-doc RAG failed: {e}")

        return "\n\n".join(parts) if parts else ""

    def _skill_web_fetch(self, message: str) -> tuple[str, str]:
        query = self._build_query(message)
        self._step("action", f"fetch → '{query[:50]}'")
        return self._fetch_cascade(query)

    def _build_query(self, message: str) -> str:
        url = re.search(r'https?://[^\s<>"{}|\\^`\[\]]+', message)
        if url: return url.group(0).rstrip(".,;)")
        
        legal = re.search(r'(article\s+l?\d+|code\s+du\s+travail|code\s+civil)',
                        message, re.IGNORECASE)
        if legal: return legal.group(0)

        # ← Nouveau : détecter les noms propres (Prénom Nom en majuscule)
        name_match = re.search(r'\b([A-ZÀÂÉÈÊËÎÏÔÙÛÜ][a-zàâéèêëîïôùûü]+(?:\s+[A-ZÀÂÉÈÊËÎÏÔÙÛÜ][a-zàâéèêëîïôùûü]+)+)\b', message)
        if name_match:
            return name_match.group(1)  # ex: "Thomas Bellegarde"

        words = [w for w in re.sub(r'[^\w\s]', ' ', message.lower()).split()
                if w not in _STOP_WDS and len(w) > 3]
        return " ".join(words[:6]) if words else message.strip()[:60]

    def _fetch_cascade(self, query: str) -> tuple[str, str]:
        if query.startswith("http"):
            c = self._mcp_fetch(query)
            if c: return c, query
        wiki = f"https://fr.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ','_')}"
        raw  = self._mcp_fetch(wiki)
        if raw and len(raw) > 50:
            m = re.search(r'extract["\s:]+([^{}\[\]]{50,})', raw, re.DOTALL)
            return (f"Wikipedia:\n{m.group(1)[:2000]}" if m else raw[:2000]), wiki
        ddg = "https://lite.duckduckgo.com/lite/?q=" + query.replace(" ", "+") + "&kl=fr-fr"
        c   = self._mcp_fetch(ddg)
        return (c, ddg) if c and len(c) > 100 else ("", "")

    def _mcp_fetch(self, url: str) -> str:
        try:
            raw = self._call_tool(MCP_SPECS["fetch"], "fetch",
                                   {"url": url, "max_length": 3000, "raw": False})
            return re.sub(r'\n{3,}', '\n\n', str(raw).strip())[:2500] if raw else ""
        except Exception:
            return ""

    def _skill_legifrance(self, message: str) -> tuple[str, bool]:
        try:
            from agents.legal_agent import LegalAgent
            r = LegalAgent().query_legifrance_chat(message)
            return r.get("context", ""), r.get("found", False)
        except Exception as e:
            self._step("observe", f"Légifrance failed: {e}")
        return "", False

    def _skill_memory_read(self, query: str) -> str:
        try:
            raw = self._call_tool(MCP_SPECS["memory"], "search_nodes", {"query": query[:200]})
            return f"[Mémoire]\n{str(raw)[:500]}" if raw and len(str(raw)) > 20 else ""
        except Exception:
            return ""

    def _skill_memory_write(self, query: str, content: str) -> None:
        if not content or len(content) < 100: return
        try:
            self._call_tool(MCP_SPECS["memory"], "create_entities", {
                "entities": [{"name": query[:80], "entityType": "Research",
                               "observations": [content[:400]]}]
            })
        except Exception:
            pass

    def _skill_filesystem(self, message: str, list_only: bool) -> str:
        docs_dir = os.path.abspath(os.getenv("DOCS_DIR", "./documents"))
        if list_only:
            try:
                raw = self._call_tool(MCP_SPECS["filesystem"], "list_directory", {"path": docs_dir})
                return f"[Fichiers GED]\n{str(raw)[:2000]}" if raw else ""
            except Exception:
                return ""
        m = re.search(r'(\w[\w\-\.]*\.(?:pdf|docx?|txt|xlsx?))', message, re.IGNORECASE)
        if m:
            fname = m.group(1)
            fpath = self._find_file(fname, docs_dir) or os.path.join(docs_dir, fname)
            try:
                raw = self._call_tool(MCP_SPECS["filesystem"], "read_file", {"path": fpath})
                return f"[{fname}]\n{str(raw)[:3000]}" if raw else ""
            except Exception:
                pass
        return ""

    def _find_file(self, name: str, docs_dir: str) -> str:
        for root, _, files in os.walk(docs_dir):
            for f in files:
                if f.lower() == name.lower():
                    return os.path.join(root, f)
        return ""

    def _skill_calendar(self, message: str, write: bool = False) -> str:
        if write:
            try:
                raw = self._call_tool(MCP_SPECS["google_calendar"], "create_event", {
                    "calendarId": os.getenv("GOOGLE_CALENDAR_ID", "primary"),
                    "summary": message[:100], "start": {"dateTime": ""}, "end": {"dateTime": ""},
                })
                if raw: return f"[Événement créé]\n{str(raw)[:300]}"
            except Exception as e:
                self._step("observe", f"Calendar MCP failed: {e}")
            return self._create_calendar_event_native(message)
        else:
            try:
                raw = self._call_tool(MCP_SPECS["google_calendar"], "list_events", {
                    "calendarId": os.getenv("GOOGLE_CALENDAR_ID", "primary"), "maxResults": 5,
                })
                if raw: return f"[Agenda]\n{str(raw)[:800]}"
            except Exception:
                return self._list_calendar_events_native()
        return ""

    def _create_calendar_event_native(self, message: str) -> str:
        try:
            from googleapiclient.discovery import build
            from core.constants import get_google_credentials
            from datetime import datetime, timedelta
            creds = get_google_credentials()
            if not creds: return "[Calendar] token.json absent."
            service = build("calendar", "v3", credentials=creds)
            now = datetime.utcnow()
            start = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0)
            end   = start + timedelta(hours=1)
            event = service.events().insert(
                calendarId="primary",
                body={"summary": message[:100],
                      "start": {"dateTime": start.isoformat()+"Z", "timeZone": "Europe/Paris"},
                      "end":   {"dateTime": end.isoformat()+"Z",   "timeZone": "Europe/Paris"}}
            ).execute()
            return f"[Événement créé] {event.get('summary','')} — {event.get('htmlLink','')}"
        except Exception as e:
            return f"[Calendar] Erreur: {e}"

    def _list_calendar_events_native(self) -> str:
        try:
            from googleapiclient.discovery import build
            from core.constants import get_google_credentials
            from datetime import datetime, timezone
            creds = get_google_credentials()
            if not creds: return ""
            service = build("calendar", "v3", credentials=creds)
            result  = service.events().list(
                calendarId="primary", timeMin=datetime.now(timezone.utc).isoformat(),
                maxResults=5, singleEvents=True, orderBy="startTime",
            ).execute()
            events = result.get("items", [])
            if not events: return "[Agenda] Aucun événement à venir."
            lines = ["[Agenda]"]
            for e in events:
                start = e.get("start", {}).get("dateTime", e.get("start", {}).get("date", ""))
                lines.append(f"• {e.get('summary','?')} — {start}")
            return "\n".join(lines)
        except Exception as e:
            return f"[Agenda] Erreur: {e}"


    def _prepare_email_draft_with_attachment(
        self, message: str, filename: str, miniged_token: str = "", summary: str = "",
    ) -> dict:
        """
        Prépare un brouillon d'email avec la pièce jointe déjà récupérée.
        Stocke le PDF en base64 dans la pending action.
        NE PAS envoyer ici — l'utilisateur confirme via /confirm-action.
        """
        m = _EMAIL_RE.search(message)
        if not m:
            return {"error": "Adresse email non détectée. Précisez le destinataire."}

        email_to     = m.group(0)
        doc_filename = filename or "document.pdf"
        pdf_b64      = ""

        try:
            import base64
            from memory.short_term import get_short_term_memory
            from services.miniged_client import get_file_bytes, get_document_files_info

            stm    = get_short_term_memory()
            doc_id = stm.get_current_miniged_id()

            if doc_id and miniged_token:
                files = get_document_files_info(doc_id, miniged_token)
                if files:
                    file_id      = str(files[0]["id"])
                    doc_filename = files[0].get("filename", doc_filename)
                    pdf_bytes    = get_file_bytes(doc_id, miniged_token, file_id)
                    if pdf_bytes:
                        pdf_b64 = base64.b64encode(pdf_bytes).decode()
                        self._step("observe",
                            f"PDF récupéré: {len(pdf_bytes)} bytes | "
                            f"b64: {len(pdf_b64)} chars | fichier: {doc_filename}")
                    else:
                        self._step("observe", "PDF vide retourné par MiniGED")
                else:
                    self._step("observe", "Aucun fichier trouvé pour ce document")
            else:
                self._step("observe", f"doc_id={doc_id!r} miniged_token={'présent' if miniged_token else 'absent'}")
        except Exception as e:
            self._step("observe", f"Récupération PDF failed: {e}")

        subject = f"[GED] {doc_filename}"
        body    = summary or (
            f"Bonjour,\n\n"
            f"Veuillez trouver ci-joint le document '{doc_filename}'.\n\n"
            f"Cordialement,"
        )

        action_id = str(uuid.uuid4())
        try:
            from memory.short_term import get_short_term_memory
            get_short_term_memory().add_pending_action(
                action_id,
                "send_email_with_attachment",
                {
                    "to":             email_to,
                    "subject":        subject,
                    "body":           body,
                    "filename":       doc_filename,
                    "pdf_base64":     pdf_b64,
                    "has_attachment": bool(pdf_b64),
                }
            )
            self._step("observe", f"Pending action créée: {action_id}")
        except Exception as e:
            self._step("observe", f"add_pending_action failed: {e}")

        return {
            "action_id":      action_id,
            "email_to":       email_to,
            "subject":        subject,
            "body":           body,
            "filename":       doc_filename,
            "has_attachment": bool(pdf_b64),
        }

    def _send_gmail_native(
        self,
        to: str, subject: str, body: str,
        attachment_bytes: Optional[bytes] = None,
        attachment_filename: Optional[str] = None,
    ) -> tuple[bool, str]:
        try:
            import base64
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            from email.mime.application import MIMEApplication
            from googleapiclient.discovery import build
            from core.constants import get_google_credentials

            creds = get_google_credentials()
            if not creds:
                self._step("observe", "Gmail natif: token.json absent")
                return False, "Gmail non configuré."

            service = build("gmail", "v1", credentials=creds)
            msg = MIMEMultipart()
            msg["To"]      = to
            msg["Subject"] = subject
            sender = os.getenv("GMAIL_USER", "")
            if sender: msg["From"] = sender
            msg.attach(MIMEText(body, "plain", "utf-8"))

            if attachment_bytes and attachment_filename:
                part = MIMEApplication(attachment_bytes, Name=attachment_filename)
                part["Content-Disposition"] = f'attachment; filename="{attachment_filename}"'
                msg.attach(part)
                self._step("observe", f"PJ: {attachment_filename} ({len(attachment_bytes)} bytes)")

            raw_b64 = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            service.users().messages().send(userId="me", body={"raw": raw_b64}).execute()
            self._step("observe", f"Gmail natif OK → {to}")
            return True, to
        except ImportError:
            return False, "pip install google-api-python-client"
        except Exception as e:
            self._step("observe", f"Gmail natif failed: {e}")
            return False, str(e)

    def _skill_send_email_simple(self, message: str, filename: str, summary: str = "") -> tuple[bool, str]:
        """Email simple sans pièce jointe."""
        m = _EMAIL_RE.search(message)
        if not m: return False, "Adresse email non détectée."
        email_to = m.group(0)
        subject  = f"[GED] {filename}" if filename else "[GED] Votre demande"
        body     = summary or f"Informations concernant {filename}."
        try:
            raw    = self._call_tool(MCP_SPECS["gmail"], "send_email",
                                     {"to": [email_to], "subject": subject, "body": body, "mimeType": "text/plain"})
            result = json.loads(raw) if isinstance(raw, str) and raw.strip() else (raw or {})
            if "id" in result or "threadId" in result or result.get("success"):
                self._step("observe", f"Gmail MCP OK → {email_to}")
                return True, email_to
        except Exception as e:
            self._step("observe", f"Gmail MCP failed: {e} → fallback natif")
        return self._send_gmail_native(email_to, subject, body)


    def _build_prompt(self, message: str, document_text: str, document_type: str,
                       filename: str, history: list, sig_alert: bool, contexts: dict, candidate_context: str = "", ace_context="") -> str:
        parts = []
        if candidate_context:
            parts.append(candidate_context)
        if ace_context:                          # ← ajouter ici
            parts.append(ace_context)
        if document_text and filename:
            parts.append(f"=== DOCUMENT : {filename} (type : {document_type}) ===\n"
                          f"{document_text[:2000]}")
            if sig_alert:
                parts.append("⚠ Ce document contient des zones de signature vides.")
        for key, val in contexts.items():
            if val: parts.append(f"=== {key.upper()} ===\n{val}")
        if history:
            hist = "\n".join(
                f"{'Utilisateur' if h.get('role')=='user' else 'Assistant'}: {h.get('content','')[:200]}"
                for h in history[-6:]
            )
            parts.append(f"Historique:\n{hist}")
        parts.append(f"Utilisateur : {message}\nAssistant :")
        return "\n\n".join(parts)

    def run(self, message: str, document_text: str = "", document_type: str = "",
            filename: str = "", history: Optional[list] = None,
            skills: List[str] = None, miniged_token: str = "",
            user_id: str = "", **_) -> dict:
        self._reset()
        history  = history or []
        user_msg = self._clean(message)
        active   = self._detect_skills(user_msg, skills or [])
        self._step("thought", f"'{user_msg[:80]}' | doc='{filename}' | skills={[s.value for s in active]}")

        # ── Contexte candidature ─────────────────────────────────────────────────
        candidate_context = ""
        cand_name_for_ace = ""
        if miniged_token and user_id:
            try:
                import requests as _rq
                miniged_base = os.getenv("MINIGED_API_URL", "http://localhost:5092")
                try:
                    from memory.short_term import get_short_term_memory
                    current_doc_id = get_short_term_memory().get_current_miniged_id()
                except Exception:
                    current_doc_id = ""
                if current_doc_id:
                    r = _rq.get(
                        f"{miniged_base}/api/recruitment/application-by-document/{current_doc_id}",
                        headers={"Authorization": f"Bearer {miniged_token}"},
                        timeout=4,
                    )
                    if r.status_code == 200:
                        cand   = r.json()
                        score  = cand.get("aiScore") or 0
                        rec    = cand.get("aiRecommendation") or ""
                        status = cand.get("status") or ""
                        name   = cand.get("name") or ""
                        pos    = cand.get("position") or ""
                        cand_name_for_ace = name
                        if score or rec:
                            candidate_context = (
                                f"\n[CONTEXTE CANDIDATURE]\n"
                                f"Candidat : {name} | Poste : {pos}\n"
                                f"Score IA : {score}/100 | Recommandation : {rec} | Statut : {status}\n"
                                f"Le RH peut poser des questions sur ce scoring.\n"
                            )
                            self._step("observe", f"Contexte candidature chargé: {name} score={score}")
            except Exception as _e:
                self._step("observe", f"Contexte candidature non-bloquant: {_e}")

        # ── Contexte ACE playbook ────────────────────────────────────────────────
        ace_context = ""
        if candidate_context:
            try:
                from ace.playbook_store import render_playbook, get_override_log
                if cand_name_for_ace:
                    overrides = get_override_log(limit=100)
                    cand_overrides = [
                        o for o in overrides
                        if cand_name_for_ace.lower() in o.get("candidate_name", "").lower()
                    ]
                    if cand_overrides:
                        last       = cand_overrides[-1]
                        rh_notes   = last.get("rh_notes", [])
                        notes_text = last.get("notes", "")
                        if rh_notes:
                            lines = ["\n[JUSTIFICATION RH DE LA DÉCISION]"]
                            for n in rh_notes:
                                lines.append(f"  {n.get('sign','')} {n.get('text','')}")
                            ace_context = "\n".join(lines)
                            self._step("observe", f"ACE: {len(rh_notes)} notes RH chargées pour {cand_name_for_ace}")
                        elif notes_text:
                            ace_context = f"\n[JUSTIFICATION RH DE LA DÉCISION]\n{notes_text[:600]}"
                            self._step("observe", f"ACE: notes texte chargées pour {cand_name_for_ace}")

                pb_render = render_playbook()
                if pb_render and len(pb_render) > 100 and "vide" not in pb_render:
                    ace_context += f"\n\n[RÈGLES APPRISES PAR ACE]\n{pb_render[:1200]}"
                    self._step("observe", "ACE: playbook injecté dans le contexte")
            except Exception as _e:
                self._step("observe", f"ACE context non-bloquant: {_e}")

        # ── Signature ────────────────────────────────────────────────────────────
        sig_alert = False
        if document_text:
            try:
                from agents.signature_agent import SignatureAgent
                _det = SignatureAgent().detect(document_text, document_type, filename)
                sig_alert = _det.get("needs_signature", False)
            except Exception:
                pass

        # ── Email avec pièce jointe ──────────────────────────────────────────────
        if SkillID.EMAIL_ATTACHMENT in active and _EMAIL_RE.search(user_msg):
            stm_summary = ""
            try:
                from memory.short_term import get_short_term_memory
                stm_summary = get_short_term_memory().get_result("summary") or ""
            except Exception:
                pass
            draft = self._prepare_email_draft_with_attachment(
                user_msg, filename, miniged_token, stm_summary
            )
            if "error" in draft:
                return {"reply": draft["error"], "action_done": None, "action_result": {},
                        "suggestions": [], "skills_used": [s.value for s in active],
                        "email_sent": False, "react_trace": self.trace,
                        "processing_ms": self._elapsed_ms()}
            attach_label = " avec pièce jointe" if draft["has_attachment"] else "⚠️ sans pièce jointe (fichier non trouvé)"
            ms = self._elapsed_ms()
            self._step("answer", f"email_draft_ready | {draft['email_to']} | {attach_label} | {ms}ms")
            return {
                "reply": f"Voici le brouillon d'email pour **{draft['email_to']}** ({attach_label}). Modifiez si besoin puis cliquez **Envoyer**.",
                "action_done":     "email_draft_ready",
                "action_result":   {"email_to": draft["email_to"]},
                "email_action_id": draft["action_id"],
                "email_draft": {
                    "to": draft["email_to"], "subject": draft["subject"],
                    "body": draft["body"], "filename": draft["filename"],
                    "has_attachment": draft["has_attachment"],
                },
                "needs_signature_alert": sig_alert,
                "suggestions": [], "skills_used": [s.value for s in active],
                "email_sent": False, "react_trace": self.trace, "processing_ms": ms,
            }

        # ── Skills ───────────────────────────────────────────────────────────────
        ctx: dict = {}
        if SkillID.TIME_GET in active:
            ctx["heure"] = self._skill_time(user_msg)
        if SkillID.FILESYSTEM_LIST in active:
            ctx["fichiers_ged"] = self._skill_filesystem(user_msg, list_only=True)
        elif SkillID.FILESYSTEM_READ in active:
            ctx["fichiers_ged"] = self._skill_filesystem(user_msg, list_only=False)
        if SkillID.CALENDAR_WRITE in active:
            ctx["calendrier"] = self._skill_calendar(user_msg, write=True)
        elif SkillID.CALENDAR_READ in active:
            ctx["calendrier"] = self._skill_calendar(user_msg, write=False)
        if SkillID.MEMORY_READ in active:
            ctx["memoire"] = self._skill_memory_read(user_msg)

        if not self._is_trivial(user_msg) and (
            SkillID.GED_SEARCH in active or
            (not document_text.strip() and not any(ctx.values()))
        ):
            ctx["ged"] = self._skill_ged_search(user_msg, miniged_token, user_id)

        legi_ok = False
        if SkillID.LEGIFRANCE_CODE in active:
            ctx["legifrance"], legi_ok = self._skill_legifrance(user_msg)

        if SkillID.WEB_FETCH in active or (SkillID.LEGIFRANCE_CODE in active and not legi_ok):
            web, _ = self._skill_web_fetch(user_msg)
            if web:
                ctx["web"] = web
                self._skill_memory_write(user_msg, web)

        if not any(ctx.values()) and len(user_msg.split()) > 4 and not self._is_trivial(user_msg):
            web, _ = self._skill_web_fetch(user_msg)
            if web:
                ctx["web"] = web

        # ── Email simple (sans pièce jointe) ────────────────────────────────────
        email_draft_info = {}
        if (SkillID.EMAIL_REPORT in active
                and SkillID.EMAIL_ATTACHMENT not in active
                and _EMAIL_RE.search(user_msg)):
            m        = _EMAIL_RE.search(user_msg)
            email_to = m.group(0) if m else ""
            if email_to:
                try:
                    from memory.short_term import get_short_term_memory
                    stm_local = get_short_term_memory()
                    summary   = stm_local.get_result("summary") or ""
                    fname     = filename or stm_local.get_last_filename() or ""
                except Exception:
                    summary, fname = "", filename or ""
                subject  = f"[GED] {fname}" if fname else "[GED] Votre demande"
                body     = summary or f"Bonjour,\n\nVeuillez trouver ci-joint les informations concernant '{fname}'.\n\nCordialement,"
                action_id = str(uuid.uuid4())
                try:
                    from memory.short_term import get_short_term_memory
                    get_short_term_memory().add_pending_action(
                        action_id, "send_email",
                        {"to": email_to, "subject": subject, "body": body,
                        "filename": fname, "document_type": document_type or "",
                        "summary": summary, "extraction": ""},
                    )
                    self._step("observe", f"Pending action email simple créée: {action_id}")
                except Exception as e:
                    self._step("observe", f"add_pending_action simple failed: {e}")
                email_draft_info = {
                    "action_id": action_id, "email_to": email_to,
                    "subject": subject, "body": body,
                    "filename": fname, "has_attachment": False,
                }

        # ── Message enrichi pour salutation avec contexte candidature ───────────
        effective_msg = user_msg
        if self._is_trivial(user_msg) and candidate_context:
            effective_msg = (
                f"{user_msg} — "
                f"[Note interne : tu parles à un RH qui consulte le dossier de ce candidat. "
                f"Présente-toi en mentionnant le candidat à la 3ème personne (son nom, son score IA, "
                f"son statut), et propose des actions RH pertinentes comme analyser ses compétences, "
                f"comparer avec l'offre, ou poser des questions sur le scoring.]"
            )

        # ── Appel LLM ────────────────────────────────────────────────────────────
        self._step("action", "Groq → réponse enrichie")
        reply = ""
        try:
            from services.llm_client import generate
            reply = generate(
                self._build_prompt(
                    effective_msg, document_text, document_type,
                    filename, history, sig_alert, ctx,
                    candidate_context=candidate_context,
                    ace_context=ace_context,
                ),
                max_tokens=700, system=self.SYSTEM_PROMPT,
            ).strip()
        except Exception as e:
            self._step("observe", f"Groq failed: {e}")
            reply = "Je rencontre une difficulté technique. Veuillez reformuler."

        # ── Retour email simple ──────────────────────────────────────────────────
        if email_draft_info:
            if reply and len(reply) > 50 and any(
                kw in reply.lower() for kw in ["bonjour", "cordialement", "objet", "madame", "monsieur"]
            ):
                email_draft_info["body"] = reply
            attach_label = "sans pièce jointe"
            ms = self._elapsed_ms()
            self._step("answer", f"email_draft_ready (simple) | {email_draft_info['email_to']} | {attach_label} | {ms}ms")
            return {
                "reply": f"Voici le brouillon d'email pour **{email_draft_info['email_to']}** ({attach_label}). Modifiez si besoin puis cliquez **Envoyer**.",
                "action_done":     "email_draft_ready",
                "action_result":   {"email_to": email_draft_info["email_to"]},
                "email_action_id": email_draft_info["action_id"],
                "email_draft": {
                    "to": email_draft_info["email_to"], "subject": email_draft_info["subject"],
                    "body": email_draft_info["body"], "filename": email_draft_info["filename"],
                    "has_attachment": False,
                },
                "needs_signature_alert": sig_alert,
                "suggestions": [], "skills_used": [s.value for s in active],
                "email_sent": False, "react_trace": self.trace, "processing_ms": ms,
            }

        # ── Retour final ─────────────────────────────────────────────────────────
        action_done   = self._detect_action(user_msg, history)
        action_result = self._build_action_result(action_done, user_msg, filename, ctx)
        suggestions   = self._build_suggestions(action_done, document_type, sig_alert)

        if ctx.get("ged") and not any(
            s.get("action") == "Résume le document actuel" for s in suggestions
        ):
            suggestions.append({
                "label": "Résumer ce document",
                "action": "Résume le document actuel",
                "icon": "pi pi-file-edit",
            })

        ms = self._elapsed_ms()
        self._step("answer", f"{len(reply)} chars | action={action_done} | {ms}ms")

        return {
            "reply":                 reply,
            "action_done":           action_done,
            "action_result":         action_result,
            "needs_signature_alert": sig_alert,
            "suggestions":           suggestions,
            "proactive_suggestions": suggestions,
            "skills_used":           [s.value for s in active],
            "ged_search_used":       bool(ctx.get("ged")),
            "cross_doc_used":        bool(ctx.get("ged")) and bool(user_id),
            "web_search_used":       bool(ctx.get("web")),
            "legifrance_used":       legi_ok,
            "email_sent":            False,
            "react_trace":           self.trace,
            "processing_ms":         ms,
        }
        
    def _detect_action(self, message: str, history: list = None) -> Optional[str]:
        history = history or []
        m = message.strip().lower()
        if any(k in m for k in ["signer", "signature", "signe "]):
            return "sign_requested"
        if _EMAIL_RE.search(message) or self._is_email_followup(message, history):
            return "email_requested"
        if any(k in m for k in ["juridique", "legal", "clause", "obligation"]):
            return "legal_check"
        if any(k in m for k in ["resume", "resumer", "synthese", "résumé", "résumer",
                                "résume", "summarize", "résumez"]):
            return "summarize"
        if any(k in m for k in ["extraire", "extraction", "extrais"]):
            return "extract"
        # ← NOUVEAU
        if any(k in m for k in ["ouvre", "ouvrir", "accède", "accéder", "affiche",
                                "montre", "navigue", "va vers", "consulte"]):
            return "open_document"
        return None

    def _is_email_followup(self, message: str, history: list) -> bool:
        m2 = message.strip().lower()
        if not any(k in m2 for k in ["mail", "email", "envoie", "envoyer"]):
            return False
        for h in reversed(history[-3:]):
            if h.get("role") == "assistant":
                c = h.get("content", "").lower()
                if any(k in c for k in ["email", "mail", "adresse", "destinataire"]):
                    return True
        return False

    def _build_action_result(self, action_done: Optional[str], message: str,
                          filename: str, ctx: dict = None) -> dict:
        ctx = ctx or {}
        if action_done == "email_requested":
            m = _EMAIL_RE.search(message)
            return {"email_to": m.group(0) if m else ""}
        if action_done == "open_document":
            # Récupérer le doc_id mis en STM par _skill_ged_search
            try:
                from memory.short_term import get_short_term_memory
                doc_id = get_short_term_memory().get_current_miniged_id()
                doc_title = get_short_term_memory().get_last_filename() or ""
                if doc_id:
                    return {"document_id": doc_id, "document_title": doc_title}
            except Exception:
                pass
        return {}

    def _build_suggestions(self, action_done, document_type, sig_alert: bool) -> list:
        suggestions = []
        if sig_alert:
            suggestions.append({"label": "Signer le document", "action": "sign", "icon": "pi pi-pen-to-square"})
        if document_type in ("CV", "Candidature", "Lettre de motivation"):
            suggestions.append({"label": "Comparer avec l'offre DevOps", "action": "Compare ce candidat avec l'offre d'emploi", "icon": "pi pi-chart-bar"})
            suggestions.append({"label": "Points forts et lacunes", "action": "Liste les points forts et les lacunes de ce candidat", "icon": "pi pi-list"})
        if document_type in ("Contrat de travail", "Juridique"):
            suggestions.append({"label": "Analyse juridique", "action": "legal", "icon": "pi pi-balance-scale"})
        if action_done == "summarize":
            suggestions.append({"label": "Envoyer le résumé", "action": "email_report", "icon": "pi pi-send"})
        return suggestions[:3]