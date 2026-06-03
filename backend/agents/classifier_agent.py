from __future__ import annotations
from agents.base_agent import BaseAgent
from core.constants import DocType, DocumentCategory, SkillID

# Labels utilisés pour classifier UN fichier individuel
_LABELS = [
    DocType.CV,
    DocType.LETTRE_MOTIVATION,
    DocType.OFFRE_EMPLOI,
    DocType.CONTRAT_TRAVAIL,
    DocType.JURIDIQUE,
    DocType.TECHNIQUE,
    DocType.AUTRE,
]


def aggregate_document_type(file_types: list[str]) -> str:

    if not file_types:
        return DocumentCategory.AUTRE.value

    types_set  = set(file_types)
    rh_types   = {DocType.CV.value, DocType.LETTRE_MOTIVATION.value,
                  DocType.OFFRE_EMPLOI.value, DocType.CONTRAT_TRAVAIL.value}
    rh_present = types_set & rh_types

    if (DocType.CV.value in types_set and
            DocType.LETTRE_MOTIVATION.value in types_set and
            DocType.CONTRAT_TRAVAIL.value in types_set):
        return DocumentCategory.DOSSIER_RH_COMPLET.value

    if (DocType.CV.value in types_set and
            DocType.LETTRE_MOTIVATION.value in types_set):
        return DocumentCategory.CANDIDATURE.value

    if len(rh_present) >= 2:
        return DocumentCategory.DOSSIER_RH.value

    if len(types_set) == 1:
        return file_types[0]

    from collections import Counter
    return Counter(file_types).most_common(1)[0][0]


class ClassifierAgent(BaseAgent):
    NAME         = "ClassifierAgent"
    SKILLS       = [SkillID.CLASSIFY_LLM.value]
    TOOL_SERVERS = [] 

    def run(self, text: str, filename: str = "document",
            context: dict = None, **_) -> dict:

        self._reset()

        self._step("thought", f"Classification '{filename}' ({len(text)} car.)")

        #Classification via llm
        label      = DocType.AUTRE.value
        confidence = 0.0
        method     = "unknown"

        self._step("action", f"skill:{SkillID.CLASSIFY_LLM.value} → Groq")
        try:
            from services.llm_client import classify
            result     = classify(
                text   = text,
                labels = [l.value for l in _LABELS],
            )
            label      = result.get("label",  DocType.AUTRE.value)
            confidence = result.get("scores", {}).get(label, 0.0)
            method     = result.get("method", "groq-llm")
            self._step("observe", f"Type={label}")
        except Exception as e:
            self._step("observe", f"LLM classify failed: {e} → keyword fallback")
            label, confidence, method = self._keyword_fallback(text, filename)

        ms = self._elapsed_ms()
        self._step("answer", f"{label} ({confidence:.0%}) | {ms}ms")

        return {
            "label":         label,
            "confidence":    round(confidence, 3),
            "method":        method,
            "processing_ms": ms,
            "react_trace":   self.trace,
        }

    def _keyword_fallback(self, text: str, filename: str = "") -> tuple:

        t    = text.lower()
        name = filename.lower()

        scores = {
            DocType.CV: sum(1 for k in [
                "expérience professionnelle", "formation", "diplôme",
                "compétences", "curriculum vitae", "profil",
                "années d'expérience", "master", "licence", "langues",
                "certifications", "parcours professionnel",
            ] if k in t),

            DocType.LETTRE_MOTIVATION: sum(1 for k in [
                "madame", "monsieur", "candidature", "motivation",
                "rejoindre", "je souhaite", "votre entreprise",
                "objet :", "je vous adresse", "intégrer votre",
            ] if k in t),

            DocType.OFFRE_EMPLOI: sum(1 for k in [
                "nous recrutons", "poste à pourvoir", "missions",
                "profil recherché", "rémunération", "postuler",
                "rejoignez-nous", "cdi à pourvoir",
            ] if k in t),

            DocType.CONTRAT_TRAVAIL: sum(1 for k in [
                "contrat de travail", "cdi", "cdd", "salarié",
                "employeur", "période d'essai", "préavis",
                "rémunération brute", "convention collective",
            ] if k in t),

            DocType.JURIDIQUE: sum(1 for k in [
                "tribunal", "clause", "responsabilité",
                "résiliation", "litige", "accord",
            ] if k in t),

            DocType.TECHNIQUE: sum(1 for k in [
                "api", "architecture", "logiciel", "serveur",
                "base de données", "backend", "frontend", "déploiement",
            ] if k in t),
        }

        # Bonus nom de fichier
        if "cv" in name or "curriculum" in name:
            scores[DocType.CV] += 3
        if "lettre" in name or "motivation" in name:
            scores[DocType.LETTRE_MOTIVATION] += 3
        if "offre" in name or "poste" in name:
            scores[DocType.OFFRE_EMPLOI] += 3
        if "contrat" in name:
            scores[DocType.CONTRAT_TRAVAIL] += 3

        best  = max(scores, key=scores.get)
        score = scores[best]
        total = sum(scores.values()) or 1

        if score > 0:
            return best.value, min(0.80, score / total), "keyword-fallback"
        return DocType.AUTRE.value, 0.35, "keyword-fallback-default"