from __future__ import annotations
import json
from agents.base_agent import BaseAgent
from core.constants import SkillID, MCP_LOCAL


class SummarizerAgent(BaseAgent):
    NAME   = "SummarizerAgent"
    SKILLS = [SkillID.SUMMARIZE_DOC.value]
    SYSTEM_PROMPT = (
        "Tu es un agent expert en synthese documentaire GED. "
        "Tu produis des resumes professionnels precis en francais. "
        "Tu n'inventes aucune information absente du document. "
        "Tu rediges en prose fluide, sans tirets ni listes."
    )
    TOOL_SERVERS = [MCP_LOCAL["summarizer"]]

    def run(self, text: str, filename: str = "document",
            document_type: str = "", **_) -> dict:
        self._reset()
        self._step("thought",
            f"skill:{SkillID.SUMMARIZE_DOC.value} | '{filename}' (type={document_type})")

        if not text or not text.strip():
            self._step("observe", "Texte vide → résumé impossible")
            return {"summary": "", "processing_ms": 0, "react_trace": self.trace}

        summary = ""

        self._step("action", "SummarizerServer.summarize_document()")
        try:
            raw = self._call_tool(MCP_LOCAL["summarizer"], "summarize_document", {
                "text":          text,
                "filename":      filename,
                "document_type": document_type,
                "system_prompt": self.SYSTEM_PROMPT,
            })

            if isinstance(raw, str) and raw.strip().startswith("{"):
                parsed  = json.loads(raw)
                summary = parsed.get("summary", "").strip()
            elif isinstance(raw, str):
                summary = raw.strip()
            else:
                summary = ""

            self._step("observe", f"MCP OK: {len(summary)} car.")

        except Exception as e:
            self._step("observe", f"MCP failed: {e}")
            summary = ""

        if not summary:
            self._step("observe", "MCP vide → fallback Groq direct")
            try:
                from services.llm_client import generate
                type_hint = f" de type '{document_type}'" if document_type else ""
                prompt = (
                    f"Résume ce document{type_hint} en 4-6 phrases "
                    f"claires et professionnelles en français :\n\n"
                    f"{text[:3000]}"
                )
                summary = generate(
                    prompt,
                    max_tokens = 400,
                    system     = self.SYSTEM_PROMPT,
                ).strip()
                self._step("observe", f"Groq direct OK: {len(summary)} car.")
            except Exception as e2:
                self._step("observe", f"Groq direct failed: {e2}")
                summary = f"Résumé non disponible : {e2}"

        ms = self._elapsed_ms()
        self._step("answer", f"{len(summary)} car. | {ms}ms")
        return {"summary": summary, "processing_ms": ms, "react_trace": self.trace}