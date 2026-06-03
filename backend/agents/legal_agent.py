"""
agents/legal_agent.py
Skills : LEGAL_SCORE (0 LLM) + LEGAL_REFS (Groq) + LEGIFRANCE (OpenLegi SSE)

Flux :
  1. Score juridique par mots-clés (0 LLM, < 1ms)
  2. Si score > 0.3 → extraction obligations via Groq
  3. Si score > 0.5 → recherche OpenLegi SSE via MCP_SPECS["openlegi"]
"""
from __future__ import annotations
from agents.base_agent import BaseAgent
from core.constants import MCP_SPECS, SkillID

_LEGAL_KW = [
    "non-concurrence", "clause", "résiliation", "tribunal",
    "convention collective", "obligations", "responsabilité",
    "indemnité", "clause pénale", "force majeure", "licenciement",
    "procuration", "prud'hommes", "rupture conventionnelle",
]


class LegalAgent(BaseAgent):
    NAME   = "LegalAgent"
    SKILLS = [SkillID.LEGAL_SCORE.value, SkillID.LEGAL_REFS.value,
              SkillID.LEGIFRANCE_CODE.value]
    SYSTEM_PROMPT = (
        "Tu es un expert juridique GED. "
        "Identifie les obligations contractuelles clés en français. "
        "Liste concise, une obligation par ligne, max 5."
    )
    TOOL_SERVERS = []   # MCP_SPECS["openlegi"] — déclaré dans constants.py

    def run(self, text: str, filename: str = "", **_) -> dict:
        self._reset()
        self._step("thought", f"Analyse juridique '{filename}'")

        # Skill LEGAL_SCORE — 0 LLM
        t     = text.lower()
        found = [kw for kw in _LEGAL_KW if kw in t]
        score = round(min(1.0, len(found) / 5), 2)
        self._step("observe", f"Score={score:.0%} | {len(found)} mots-clés")

        obligations   = []
        legal_summary = ""
        legifrance    = []
        piste_ok      = False

        # Skill LEGAL_REFS — Groq (seulement si score significatif)
        if score > 0.3:
            self._step("action", f"skill:{SkillID.LEGAL_REFS.value} → Groq")
            try:
                from services.llm_client import generate
                raw = generate(
                    f"Document : {filename}\n\nTexte :\n{text[:2000]}\n\n"
                    "Liste les obligations contractuelles (max 5, une par ligne) :",
                    max_tokens=300, system=self.SYSTEM_PROMPT,
                )
                obligations   = [l.strip() for l in raw.split("\n") if l.strip()][:5]
                legal_summary = raw.strip()
                self._step("observe", f"{len(obligations)} obligation(s)")
            except Exception as e:
                self._step("observe", f"Groq legal failed: {e}")

        # Skill LEGIFRANCE — OpenLegi SSE (seulement si score élevé)
        if score > 0.5:
            self._step("action",
                f"skill:{SkillID.LEGIFRANCE_CODE.value} → MCP_SPECS['openlegi']")
            try:
                query = " ".join(found[:3]) or filename
                raw   = self._call_tool(MCP_SPECS["openlegi"],
                                         "rechercher_jurisprudence", {"query": query})
                if raw and len(str(raw).strip()) > 20:
                    legifrance = [str(raw)[:500]]
                    piste_ok   = True
                    self._step("observe", f"OpenLegi OK: {len(legifrance[0])} car.")
            except Exception as e:
                self._step("observe", f"OpenLegi failed (non bloquant): {e}")

        ms = self._elapsed_ms()
        self._step("answer", f"score={score:.0%} | {ms}ms")
        return {
            "legal_score":        score,
            "obligations":        obligations,
            "legal_summary":      legal_summary,
            "legifrance_results": legifrance,
            "piste_available":    piste_ok,
            "processing_ms":      ms,
            "react_trace":        self.trace,
        }

    def query_legifrance_chat(self, question: str) -> dict:
        """
        Recherche Légifrance pour l'AssistantAgent.
        Retourne {"context": str, "found": bool}.
        """
        self._reset()
        try:
            raw   = self._call_tool(MCP_SPECS["openlegi"],
                                     "rechercher_jurisprudence", {"query": question[:200]})
            found = bool(raw and len(str(raw).strip()) > 20)
            return {"context": str(raw)[:600] if found else "", "found": found}
        except Exception as e:
            return {"context": "", "found": False, "error": str(e)}