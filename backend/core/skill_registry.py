from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from core.constants import SkillID, WorkflowID


@dataclass
class SkillDefinition:
    """Capacité atomique déclarée par un agent."""
    skill_id:     SkillID
    agent_class:  str
    description:  str
    requires_llm: bool = False
    cost_estimate: str = "free"   


@dataclass
class WorkflowDefinition:
    """Workflow = liste ordonnée de skills. Sert à estimer les coûts LLM."""
    workflow_id: WorkflowID
    skills:      List[SkillID]
    description: str
    parallel_ok: bool = False
    llm_calls:   int  = 0


class SkillRegistry:
    _instance: Optional["SkillRegistry"] = None

    def __init__(self) -> None:
        self._skills:    Dict[SkillID,    SkillDefinition]   = {}
        self._workflows: Dict[WorkflowID, WorkflowDefinition] = {}
        self._register_all()

    @classmethod
    def get_instance(cls) -> "SkillRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _reg(self, s: SkillDefinition) -> None:
        self._skills[s.skill_id] = s

    def _regw(self, w: WorkflowDefinition) -> None:
        self._workflows[w.workflow_id] = w

    def _register_all(self) -> None:

        # ClassifierAgent 
        self._reg(SkillDefinition(
            SkillID.CLASSIFY_LLM, "ClassifierAgent",
            "Classification RH/Juridique/Technique/Autre via Groq",
            requires_llm=True, cost_estimate="low"))

        # SummarizerAgent 
        self._reg(SkillDefinition(
            SkillID.SUMMARIZE_DOC, "SummarizerAgent",
            "Résumé professionnel adapté au type de document",
            requires_llm=True, cost_estimate="medium"))

        # ── ExtractorAgent ────────────────────────────────────────────
        self._reg(SkillDefinition(
            SkillID.EXTRACT_FIELDS, "ExtractorAgent",
            "Extraction d'informations demandées depuis le texte",
            requires_llm=True, cost_estimate="medium"))
        self._reg(SkillDefinition(
            SkillID.EXTRACT_FORM, "ExtractorAgent",
            "Extraction champs formulaire en JSON structuré",
            requires_llm=True, cost_estimate="low"))
        self._reg(SkillDefinition(
            SkillID.EXTRACT_NER, "ExtractorAgent",
            "Entités nommées (personnes, dates, montants)",
            requires_llm=True, cost_estimate="low"))

        # ── LegalAgent ────────────────────────────────────────────────
        self._reg(SkillDefinition(
            SkillID.LEGAL_SCORE, "LegalAgent",
            "Score complexité juridique par mots-clés (0 LLM)",
            requires_llm=False, cost_estimate="free"))
        self._reg(SkillDefinition(
            SkillID.LEGAL_REFS, "LegalAgent",
            "Extraction références légales via Groq",
            requires_llm=True, cost_estimate="low"))
        self._reg(SkillDefinition(
            SkillID.LEGIFRANCE_CODE, "LegalAgent",
            "Codes juridiques via OpenLegi SSE",
            requires_llm=False, cost_estimate="free"))
        self._reg(SkillDefinition(
            SkillID.LEGIFRANCE_JURIS, "LegalAgent",
            "Jurisprudence via OpenLegi SSE",
            requires_llm=False, cost_estimate="free"))
        self._reg(SkillDefinition(
            SkillID.LEGIFRANCE_LODA, "LegalAgent",
            "Textes de loi via OpenLegi SSE",
            requires_llm=False, cost_estimate="free"))

        # ── SignatureAgent ────────────────────────────────────────────
        # Agent unique : détection + apprentissage + apposition
        self._reg(SkillDefinition(
            SkillID.SIGN_PDF, "SignatureAgent",
            "Détection zones manquantes + apprentissage profil + apposition PDF (0 LLM)",
            requires_llm=False, cost_estimate="free"))
        self._reg(SkillDefinition(
            SkillID.SIGN_DETECT, "SignatureAgent",
            "Détection seule des zones de signature vides (0 LLM)",
            requires_llm=False, cost_estimate="free"))

        # ── EmailAgent ────────────────────────────────────────────────
        self._reg(SkillDefinition(
            SkillID.EMAIL_REPORT, "EmailAgent",
            "Envoi rapport via Gmail MCP officiel → fallback SMTP",
            requires_llm=True, cost_estimate="medium"))
        self._reg(SkillDefinition(
            SkillID.EMAIL_SIGNED, "EmailAgent",
            "Envoi PDF signé via Gmail MCP officiel → fallback SMTP",
            requires_llm=False, cost_estimate="free"))

        # ── TaskAgent ─────────────────────────────────────────────────
        self._reg(SkillDefinition(
            SkillID.TASK_RULES, "TaskAgent",
            "Tâches déterministes (0 LLM)",
            requires_llm=False, cost_estimate="free"))
        self._reg(SkillDefinition(
            SkillID.TASK_LLM, "TaskAgent",
            "Tâches supplémentaires via Groq (conditionnel > 2 obligations)",
            requires_llm=True, cost_estimate="low"))

        # ── AssistantAgent ────────────────────────────────────────────
        self._reg(SkillDefinition(
            SkillID.GED_SEARCH, "AssistantAgent",
            "Recherche cross-document MiniGED API + ChromaDB",
            requires_llm=False, cost_estimate="free"))
        self._reg(SkillDefinition(
            SkillID.WEB_FETCH, "AssistantAgent",
            "Fetch URL via mcp-server-fetch",
            requires_llm=False, cost_estimate="free"))
        self._reg(SkillDefinition(
            SkillID.TIME_GET, "AssistantAgent",
            "Heure actuelle via mcp-server-time",
            requires_llm=False, cost_estimate="free"))
        self._reg(SkillDefinition(
            SkillID.CALENDAR_READ, "AssistantAgent",
            "Lecture agenda Google Calendar",
            requires_llm=False, cost_estimate="free"))
        self._reg(SkillDefinition(
            SkillID.CALENDAR_WRITE, "AssistantAgent",
            "Création événement Google Calendar",
            requires_llm=False, cost_estimate="free"))
        self._reg(SkillDefinition(
            SkillID.MEMORY_READ, "AssistantAgent",
            "Lecture knowledge graph persistant",
            requires_llm=False, cost_estimate="free"))
        self._reg(SkillDefinition(
            SkillID.MEMORY_WRITE, "AssistantAgent",
            "Écriture knowledge graph persistant",
            requires_llm=False, cost_estimate="free"))
        self._reg(SkillDefinition(
            SkillID.FILESYSTEM_LIST, "AssistantAgent",
            "Liste des fichiers du dossier GED",
            requires_llm=False, cost_estimate="free"))
        self._reg(SkillDefinition(
            SkillID.FILESYSTEM_READ, "AssistantAgent",
            "Lecture d'un fichier du dossier GED",
            requires_llm=False, cost_estimate="free"))

        # ── Workflows ─────────────────────────────────────────────────

        self._regw(WorkflowDefinition(
            WorkflowID.CLASSIFY,
            [SkillID.CLASSIFY_LLM],
            "Classification (toujours exécuté)", llm_calls=1))

        self._regw(WorkflowDefinition(
            WorkflowID.SUMMARIZE,
            [SkillID.SUMMARIZE_DOC],
            "Résumé à la demande", parallel_ok=True, llm_calls=1))

        self._regw(WorkflowDefinition(
            WorkflowID.EXTRACT,
            [SkillID.EXTRACT_FIELDS, SkillID.EXTRACT_FORM],
            "Extraction à la demande", parallel_ok=True, llm_calls=2))

        self._regw(WorkflowDefinition(
            WorkflowID.LEGAL,
            [SkillID.LEGAL_SCORE, SkillID.LEGAL_REFS,
             SkillID.LEGIFRANCE_CODE, SkillID.LEGIFRANCE_JURIS, SkillID.LEGIFRANCE_LODA],
            "Analyse juridique + OpenLegi SSE", parallel_ok=True, llm_calls=2))

        self._regw(WorkflowDefinition(
            WorkflowID.SIGN,
            [SkillID.SIGN_PDF],
            "Signature PDF (0 LLM)", llm_calls=0))

        self._regw(WorkflowDefinition(
            WorkflowID.EMAIL,
            [SkillID.EMAIL_REPORT],
            "Envoi rapport Gmail MCP → SMTP fallback", llm_calls=1))

        self._regw(WorkflowDefinition(
            WorkflowID.TASKS,
            [SkillID.TASK_RULES, SkillID.TASK_LLM],
            "Tâches MiniGED (0 LLM → Groq conditionnel)", llm_calls=1))

        self._regw(WorkflowDefinition(
            WorkflowID.COMPARE,
            [SkillID.EXTRACT_FIELDS],
            "Comparaison versions", llm_calls=1))

        self._regw(WorkflowDefinition(
            WorkflowID.REDACT,
            [SkillID.EXTRACT_NER],
            "Anonymisation RGPD", llm_calls=1))

        self._regw(WorkflowDefinition(
            WorkflowID.FOLDER_SCAN,
            [SkillID.FILESYSTEM_LIST, SkillID.FILESYSTEM_READ,
             SkillID.CLASSIFY_LLM, SkillID.SUMMARIZE_DOC],
            "Scan dossier entier", parallel_ok=True, llm_calls=0))

    # ── API publique ──────────────────────────────────────────────────

    def get_skill(self, skill_id: SkillID) -> Optional[SkillDefinition]:
        return self._skills.get(skill_id)

    def get_workflow(self, workflow_id: WorkflowID) -> Optional[WorkflowDefinition]:
        return self._workflows.get(workflow_id)

    def estimate_llm_calls(self, workflow_ids: list) -> int:
        return sum(
            self._workflows[wid].llm_calls
            for wid in workflow_ids
            if wid in self._workflows
        )

    def get_skills_info(self) -> List[dict]:
        return [
            {
                "skill_id":     s.skill_id.value,
                "agent":        s.agent_class,
                "description":  s.description,
                "requires_llm": s.requires_llm,
                "cost":         s.cost_estimate,
            }
            for s in self._skills.values()
        ]

    def get_workflows_info(self) -> List[dict]:
        return [
            {
                "workflow_id": w.workflow_id.value,
                "description": w.description,
                "skills":      [s.value for s in w.skills],
                "llm_calls":   w.llm_calls,
                "parallel":    w.parallel_ok,
            }
            for w in self._workflows.values()
        ]


def get_skill_registry() -> SkillRegistry:
    return SkillRegistry.get_instance()