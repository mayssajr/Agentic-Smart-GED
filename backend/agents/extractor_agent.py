"""
agents/extractor_agent.py — Extraction d'informations

Skills : EXTRACT_FIELDS + EXTRACT_FORM + EXTRACT_NER
LLM    : 1-2 appels, max 500 tokens
"""

from __future__ import annotations
import json
import re
from typing import Any, Dict, Optional
from agents.base_agent import BaseAgent
from core.constants import SkillID, MCP_LOCAL


class ExtractorAgent(BaseAgent):
    NAME   = "ExtractorAgent"
    SKILLS = [SkillID.EXTRACT_FIELDS.value, SkillID.EXTRACT_FORM.value, SkillID.EXTRACT_NER.value]
    SYSTEM_PROMPT = (
        "Tu es un agent expert en extraction d'informations GED. "
        "Tu extrais avec precision les informations demandees. "
        "Tu ne reformules pas, tu copies les valeurs exactes. "
        "Si une information est absente : 'Non trouve'. "
        "Format : - Libelle : valeur"
    )
    TOOL_SERVERS = [MCP_LOCAL["extractor"]]

    def run(self, text: str, extraction_request: Optional[str] = None,
            filename: str = "document", document_type: str = "", **_) -> dict:
        self._reset()

        if not extraction_request or not extraction_request.strip():
            self._step("thought", "Aucune extraction demandee → skip")
            return {"extraction": "", "form_fields": {},
                    "processing_ms": 0, "react_trace": self.trace}

        self._step("thought",
            f"skill:{SkillID.EXTRACT_FIELDS.value} | '{filename}' | '{extraction_request[:60]}'")

        extraction = ""
        self._step("action", "ExtractorServer.extract_information()")
        try:
            raw = self._call_tool(MCP_LOCAL["extractor"], "extract_information", {
                "text": text, "extraction_request": extraction_request,
            })
            extraction = str(raw).strip() if raw else ""
            self._step("observe", f"MCP OK: {len(extraction)} car.")
        except Exception as e:
            self._step("observe", f"MCP failed ({e}) → Groq direct")
            try:
                from services.llm_client import extract_info
                extraction = extract_info(text, extraction_request, system=self.SYSTEM_PROMPT)
            except Exception as e2:
                self._step("observe", f"Groq extraction failed: {e2}")

        # Skill EXTRACT_FORM : champs JSON structurés
        form_fields: Dict[str, Any] = {}
        self._step("action", f"skill:{SkillID.EXTRACT_FORM.value} → JSON fields")
        try:
            from services.llm_client import generate
            raw = generate(
                "Extrais les champs en JSON compact "
                "(nom, prenom, date, montant, adresse, societe, poste, salaire, parties, duree).\n"
                "JSON uniquement.\n"
                f"Document :\n{text[:1500]}",
                max_tokens=300,
            )
            raw = re.sub(r"```(?:json)?\s*|```\s*", "", raw).strip()
            m   = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                form_fields = json.loads(m.group(0))
                self._step("observe", f"Champs: {list(form_fields.keys())[:5]}")
        except Exception as e:
            self._step("observe", f"Form extract (non bloquant): {e}")

        ms = self._elapsed_ms()
        self._step("answer", f"{len(extraction)} car. | {ms}ms")
        return {"extraction": extraction, "form_fields": form_fields,
                "processing_ms": ms, "react_trace": self.trace}