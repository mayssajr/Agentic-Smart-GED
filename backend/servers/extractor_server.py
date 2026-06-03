import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("extractor-server")


def _keyword_fallback(text: str, request: str) -> str:
    """
    Extraction par règles locales — utilisée si le LLM est indisponible.
    Cible : dates, montants, emails, noms propres.
    """
    lines         = []
    request_lower = request.lower()

    # Dates
    if any(w in request_lower for w in ["date", "dates"]):
        for m in re.finditer(r'\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})\b', text):
            lines.append(f"• Date : {m.group(1)}")

    # Montants
    if any(w in request_lower for w in ["montant", "salaire", "rémunération", "prix"]):
        for m in re.finditer(
            r'\b(\d[\d\s]*(?:[,\.]\d{1,2})?)\s*(€|EUR|euros?)\b',
            text, re.IGNORECASE,
        ):
            lines.append(f"• Montant : {m.group(1).strip()} {m.group(2)}")

    # Emails
    if any(w in request_lower for w in ["email", "mail", "courriel"]):
        for m in re.finditer(r'[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}', text):
            lines.append(f"• Email : {m.group(0)}")

    # Noms propres
    if any(w in request_lower for w in ["nom", "signataire", "parties", "personne"]):
        seen = set()
        for m in re.finditer(
            r'\b([A-ZÉÈÊÀÙÎ][a-zéèêàùî]+(?:\s[A-ZÉÈÊÀÙÎ][a-zéèêàùî]+)+)\b', text
        ):
            n = m.group(1)
            if n not in seen:
                seen.add(n)
                lines.append(f"• Nom : {n}")
            if len(seen) >= 5:
                break

    return "\n".join(lines) if lines else ""


@mcp.tool()
def extract_information(text: str, extraction_request: str) -> str:
    """
    Extrait les informations demandées depuis le texte du document.

    Utilise llm_client.extract_info() (prompt user défini dans llm_client).
    Fallback par règles regex si LLM indisponible.
    """
    if not extraction_request.strip():
        return ""
    if not text.strip():
        return "• Aucun contenu de document disponible pour l'extraction."

    # ── Tentative LLM ─────────────────────────────────────────────────
    llm_result = ""
    try:
        from services.llm_client import extract_info
        llm_result = extract_info(text, extraction_request)
    except Exception as e:
        print(f"[ExtractorServer] LLM extract_info échoué : {e}", file=sys.stderr)

    if (
        llm_result
        and llm_result.strip()
        and llm_result.strip() != "Aucune information extraite."
        and "•" in llm_result
    ):
        return llm_result

    # ── Fallback par règles ───────────────────────────────────────────
    print(
        "[ExtractorServer] Fallback règles activé "
        f"(llm_result={repr(llm_result[:60])})",
        file=sys.stderr,
    )
    rule_result = _keyword_fallback(text, extraction_request)
    if rule_result:
        return rule_result

    # ── Dernier recours : premières lignes du document ────────────────
    lines = [l.strip() for l in text.split("\n") if l.strip()][:5]
    if lines:
        return (
            "• Informations de référence trouvées dans le document :\n"
            + "\n".join(f"  {l}" for l in lines)
        )

    return "• Aucune information pertinente trouvée pour : " + extraction_request


if __name__ == "__main__":
    mcp.run(transport="stdio")