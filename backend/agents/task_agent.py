"""
TaskAgent — Responsabilités UNIQUES :
  1. Générer des tâches MiniGED via LLM
  2. Mettre à jour le statut d'un candidat dans MiniGED
  3. Trouver un créneau Calendar et créer l'événement

Ce que TaskAgent NE FAIT PLUS (supprimé) :
  - Coordonner scoring + statut post-score → orchestrateur
  - Calculer le score CV                   → ScoreAgent
  - Décider selon les phases ACE           → AceDecisionAgent
  - Envoyer des emails de convocation      → EmailAgent
  - Exécuter _execute_ace_action()         → orchestrateur
"""
from __future__ import annotations
import json, os
from datetime import datetime, timedelta, timezone

from agents.base_agent import BaseAgent
from core.constants import MCP_LOCAL, MCP_SPECS, SkillID

# ── Constantes métier ─────────────────────────────────────────────────────────

RH_DOCUMENT_TYPES               = {"CV", "Lettre de motivation", "Candidature",
                                    "Dossier RH", "Dossier RH complet"}
SCORING_DOCUMENT_TYPES          = {"CV", "Candidature", "Dossier RH complet"}
CANDIDATE_STATUS_AFTER_ANALYSIS = "ATraiter"
INTERVIEW_DURATION_MINUTES      = 60
WORK_HOUR_START                 = 9
WORK_HOUR_END                   = 15
INTERVIEW_DAYS                  = {0, 1, 2}
DAYS_AHEAD                      = 7

_TASK_SYSTEM_PROMPT = """Tu es un expert RH et gestionnaire de documents.
Tu analyses un document GED et tu génères les tâches RH les plus pertinentes.
- Génère UNIQUEMENT du JSON valide, sans texte avant ni après, sans markdown.
- Entre 2 et 5 tâches maximum. Chaque tâche doit être SPÉCIFIQUE au contenu.
- priority : "Low" | "Medium" | "High" | "Urgent"
- due_days : nombre de jours à partir d'aujourd'hui (entier, 1-30)
Format : [{"title":"...","description":"...","priority":"High","due_days":3}]"""


class TaskAgent(BaseAgent):
    """
    Responsable UNIQUEMENT de :
      - Créer des tâches MiniGED pour un document (LLM)
      - Mettre à jour le statut candidat dans MiniGED
      - Trouver un créneau Calendar et créer l'événement Google Meet

    NE FAIT PAS :
      - Scoring CV               → ScoreAgent
      - Décision phases ACE      → AceDecisionAgent
      - Coordination post-score  → orchestrateur
      - Envoi d'emails           → EmailAgent (appelé directement par l'orchestrateur)
    """

    NAME         = "TaskAgent"
    SKILLS       = [SkillID.TASK_LLM.value, SkillID.TASK_RULES.value]
    TOOL_SERVERS = []

    # ═══════════════════════════════════════════════════════════════════════
    # CONTRAT BaseAgent
    # ═══════════════════════════════════════════════════════════════════════

    def run(self, **kwargs) -> dict:
        """
        Implémentation requise par BaseAgent (méthode abstraite).
        TaskAgent n'a pas de point d'entrée unique — l'orchestrateur appelle
        directement create_tasks_for_document(), update_candidate_status()
        et create_calendar_event() selon le besoin.
        """
        raise NotImplementedError(
            "TaskAgent.run() ne doit pas être appelé directement. "
            "Utilisez create_tasks_for_document(), update_candidate_status() "
            "ou create_calendar_event() via l'orchestrateur."
        )

    # ═══════════════════════════════════════════════════════════════════════
    # 1. TÂCHES MINIGED
    # ═══════════════════════════════════════════════════════════════════════

    def create_tasks_for_document(
        self,
        document_id: str | int,
        doc_type: str,
        summary: str = "",
    ) -> dict:
        """
        Génère et pousse des tâches MiniGED pour un document donné.
        Idempotent : skip si des tâches existent déjà pour ce document.

        Retourne :
          {"tasks_created": int, "tasks": list, "skipped": bool, "reason": str}
        """
        self._reset()
        self._step("thought",
            f"create_tasks_for_document | doc_id={document_id} | type={doc_type}")

        existing_titles = self._get_existing_task_titles(document_id)
        if existing_titles:
            self._step("observe",
                f"{len(existing_titles)} tâche(s) déjà présentes → skip création")
            return {
                "tasks_created": 0, "tasks": [],
                "skipped": True, "reason": "tasks_already_exist",
            }

        tasks_to_create = self._generate_tasks_with_llm(doc_type, summary)
        if not tasks_to_create:
            return {
                "tasks_created": 0, "tasks": [],
                "skipped": True, "reason": "no_tasks_generated",
            }

        self._step("action",
            f"MCP create_tasks → {len(tasks_to_create)} tâche(s) générées par LLM")
        try:
            from mcp_client import call_mcp_tool
            raw    = call_mcp_tool(
                MCP_LOCAL["miniged"], "create_tasks",
                {"document_id": int(document_id),
                 "tasks_json": json.dumps(tasks_to_create)},
            )
            result = json.loads(raw)
            n      = result.get("tasksCreated", 0)
            self._step("observe", f"Tâches créées : {n}")
            return {"tasks_created": n, "tasks": result.get("tasks", []), "skipped": False}
        except Exception as e:
            self._step("observe", f"create_tasks MCP failed: {e}")
            return {"tasks_created": 0, "tasks": [], "skipped": True, "error": str(e)}

    # ═══════════════════════════════════════════════════════════════════════
    # 2. STATUT CANDIDAT
    # ═══════════════════════════════════════════════════════════════════════

    def update_candidate_status(
        self,
        document_id: str | int,
        doc_type: str,
        status: str,
        notes: str = "",
    ) -> dict:
        """
        Met à jour le statut d'un candidat dans MiniGED.
        Guard : n'agit que sur les types RH si status == CANDIDATE_STATUS_AFTER_ANALYSIS.

        Retourne :
          {"updated": bool, "old_status": str, "new_status": str}
        """
        if doc_type not in RH_DOCUMENT_TYPES and status == CANDIDATE_STATUS_AFTER_ANALYSIS:
            return {"updated": False, "reason": "type non RH"}

        self._step("action", f"MCP update_candidate_status → {status}")
        try:
            from mcp_client import call_mcp_tool
            raw    = call_mcp_tool(
                MCP_LOCAL["miniged"], "update_candidate_status",
                {"document_id": int(document_id), "status": status, "notes": notes},
            )
            result = json.loads(raw)
            if result.get("success"):
                self._step("observe",
                    f"Statut : {result.get('oldStatus')} → {result.get('newStatus')}")
                return {
                    "updated":    True,
                    "old_status": result.get("oldStatus"),
                    "new_status": result.get("newStatus"),
                }
            return {"updated": False, "reason": result.get("error", "")}
        except Exception as e:
            self._step("observe", f"update_candidate_status failed: {e}")
            return {"updated": False, "error": str(e)}

    # ═══════════════════════════════════════════════════════════════════════
    # 3. CALENDAR — trouver un créneau et créer l'événement
    #    L'email de convocation est envoyé par l'orchestrateur via EmailAgent.
    # ═══════════════════════════════════════════════════════════════════════

    def create_calendar_event(
        self,
        candidate_name:  str,
        candidate_email: str,
        position:        str,
        document_id:     str | int,
    ) -> dict:
        """
        Trouve un créneau libre et crée l'événement Google Calendar avec Meet.

        NE ENVOIE PAS d'email — c'est la responsabilité de EmailAgent.

        Retourne :
          {
            "event_created": bool,
            "event_id":      str,
            "html_link":     str,
            "meet_link":     str,
            "slot_start":    str,
            "slot_end":      str,
            "slot_formatted":str,
            "calendar_error":str,
          }
        """
        self._step("action",
            f"create_calendar_event → {candidate_name} ({candidate_email})")

        cal_spec          = MCP_SPECS["google_calendar"]
        interviewer_email = os.getenv("INTERVIEWER_EMAIL", "")

        slot       = self._find_free_slot(cal_spec, interviewer_email) \
                     or self._default_slot()
        slot_label = self._format_slot(slot["start"], slot["end"])
        self._step("observe", f"Créneau retenu : {slot_label}")

        attendees = [{"email": candidate_email}]
        if interviewer_email:
            attendees.append({"email": interviewer_email})

        event_id = html_link = meet_link = ""
        event_created  = False
        calendar_error = ""
        try:
            raw = self._call_tool(cal_spec, "create-event", {
                "calendarId":  os.getenv("GOOGLE_CALENDAR_ID", "primary"),
                "summary":     f"Entretien — {candidate_name} — {position}",
                "description": (
                    f"Candidat : {candidate_name}\n"
                    f"Poste : {position}\n"
                    f"Document : {document_id}"
                ),
                "start":     slot["start"],
                "end":       slot["end"],
                "attendees": attendees,
                "sendUpdates": "all",
                "conferenceData": {"createRequest": {
                    "requestId": f"entretien-{document_id}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }},
            })
            raw_data  = json.loads(raw) if isinstance(raw, str) and raw.strip() else {}
            data      = raw_data.get("event", raw_data)
            event_id  = data.get("id", "")
            html_link = data.get("htmlLink", "")
            meet_link = (
                data.get("conferenceData", {})
                    .get("entryPoints", [{}])[0]
                    .get("uri", "")
            )
            event_created = bool(event_id)
            self._step("observe",
                f"Événement {'créé' if event_created else 'non créé'} | "
                f"meet_link={'oui' if meet_link else 'non'}")
        except Exception as e:
            calendar_error = str(e)
            self._step("observe", f"Calendar MCP failed: {calendar_error[:150]}")

        # Tâche MiniGED de suivi (non bloquant)
        try:
            from mcp_client import call_mcp_tool
            call_mcp_tool(MCP_LOCAL["miniged"], "create_tasks", {
                "document_id": int(document_id),
                "tasks_json": json.dumps([{
                    "title":       f"Entretien planifié — {candidate_name}",
                    "description": f"Créneau : {slot_label}\nMeet : {meet_link}",
                    "priority":    "High",
                    "due_days":    3,
                }]),
            })
        except Exception:
            pass

        return {
            "event_created":  event_created,
            "event_id":       event_id,
            "html_link":      html_link,
            "meet_link":      meet_link,
            "slot_start":     slot["start"],
            "slot_end":       slot["end"],
            "slot_formatted": slot_label,
            "calendar_error": calendar_error,
        }

    # ═══════════════════════════════════════════════════════════════════════
    # INTERNALS — LLM task generation
    # ═══════════════════════════════════════════════════════════════════════

    def _generate_tasks_with_llm(self, doc_type: str, summary: str) -> list[dict]:
        self._step("action", f"LLM → génération de tâches | type={doc_type}")
        content = summary.strip() if summary.strip() else f"Document de type : {doc_type}"
        prompt  = (
            f"Voici le résumé d'un document de type « {doc_type} » :\n\n"
            f"{content[:1500]}\n\n"
            "Génère les tâches RH les plus pertinentes et urgentes. Sois précis."
        )
        try:
            import re
            from services.llm_client import generate
            raw   = generate(prompt, max_tokens=600, system=_TASK_SYSTEM_PROMPT).strip()
            raw   = re.sub(r"```json|```", "", raw).strip()
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if not match:
                return []
            tasks = json.loads(match.group())
            valid_prios = {"Low", "Medium", "High", "Urgent"}
            valid_tasks = []
            for t in tasks:
                if not isinstance(t, dict) or not t.get("title"):
                    continue
                valid_tasks.append({
                    "title":       str(t.get("title", ""))[:200],
                    "description": str(t.get("description", ""))[:1000],
                    "priority":    t.get("priority", "Medium")
                                   if t.get("priority") in valid_prios else "Medium",
                    "due_days":    max(1, min(30, int(t.get("due_days", 3)))),
                })
            self._step("observe",
                f"LLM a généré {len(valid_tasks)} tâche(s) : "
                + " | ".join(t["title"][:40] for t in valid_tasks))
            return valid_tasks
        except Exception as e:
            self._step("observe", f"LLM task generation failed: {e}")
            return []

    def _get_existing_task_titles(self, document_id: str | int) -> list[str]:
        try:
            from mcp_client import call_mcp_tool
            raw  = call_mcp_tool(
                MCP_LOCAL["miniged"], "get_document",
                {"document_id": int(document_id)},
            )
            data = json.loads(raw) if isinstance(raw, str) else raw or {}
            return [t.get("title", "") for t in data.get("tasks", [])]
        except Exception:
            return []

    # ═══════════════════════════════════════════════════════════════════════
    # INTERNALS — Slot Calendar
    # ═══════════════════════════════════════════════════════════════════════

    def _find_free_slot(self, cal_spec, interviewer_email: str = "") -> dict | None:
        try:
            now = datetime.now(timezone.utc)

            def _fmt(dt):
                return dt.strftime("%Y-%m-%dT%H:%M:%S")

            cals = [{"id": "primary"}]
            if interviewer_email:
                cals.append({"id": interviewer_email})

            raw  = self._call_tool(cal_spec, "get-freebusy", {
                "calendars": cals,
                "timeMin":   _fmt(now),
                "timeMax":   _fmt(now + timedelta(days=DAYS_AHEAD)),
            })
            data = json.loads(raw) if isinstance(raw, str) and raw.strip() else {}
            busy = (
                data.get("busy")
                or data.get("calendars", {}).get("primary", {}).get("busy", [])
            )
            return self._compute_free_slot(busy, now)
        except Exception as e:
            self._step("observe", f"freebusy failed: {e}")
            return None

    def _compute_free_slot(self, busy_slots: list, from_dt: datetime) -> dict | None:
        occupied = []
        for b in busy_slots:
            try:
                s = datetime.fromisoformat(b["start"].replace("Z", "+00:00"))
                e = datetime.fromisoformat(b["end"].replace("Z", "+00:00"))
                occupied.append((s, e))
            except Exception:
                pass

        duration = timedelta(minutes=INTERVIEW_DURATION_MINUTES)
        current  = from_dt.replace(
            hour=WORK_HOUR_START, minute=0, second=0, microsecond=0)
        if current < from_dt:
            current += timedelta(days=1)

        for _ in range(DAYS_AHEAD * 8):
            if current.weekday() not in INTERVIEW_DAYS:
                current = (current + timedelta(days=1)).replace(
                    hour=WORK_HOUR_START, minute=0)
                continue
            if current.hour >= WORK_HOUR_END:
                current = (current + timedelta(days=1)).replace(
                    hour=WORK_HOUR_START, minute=0)
                continue
            slot_end = current + duration
            if not any(not (slot_end <= s or current >= e) for s, e in occupied):
                return {"start": current.isoformat(), "end": slot_end.isoformat()}
            current += timedelta(hours=1)
        return None

    def _default_slot(self) -> dict:
        s = (datetime.now(timezone.utc) + timedelta(days=2)).replace(
            hour=9, minute=0, second=0, microsecond=0)

        def _fmt(dt):
            return dt.strftime("%Y-%m-%dT%H:%M:%S")

        return {
            "start": _fmt(s),
            "end":   _fmt(s + timedelta(minutes=INTERVIEW_DURATION_MINUTES)),
        }

    def _format_slot(self, start: str, end: str) -> str:
        try:
            JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
            MOIS  = ["", "janvier", "février", "mars", "avril", "mai", "juin", "juillet",
                     "août", "septembre", "octobre", "novembre", "décembre"]
            s = datetime.fromisoformat(start.replace("Z", "+00:00"))
            e = datetime.fromisoformat(end.replace("Z", "+00:00"))
            return (
                f"{JOURS[s.weekday()]} {s.day} {MOIS[s.month]} {s.year} "
                f"de {s.strftime('%H:%M')} à {e.strftime('%H:%M')} (heure de Paris)"
            )
        except Exception:
            return f"{start} → {end}"