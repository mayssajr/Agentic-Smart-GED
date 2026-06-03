import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("summarizer-server")

_DEFAULT_SYSTEM = (
    "Tu es un agent expert en synthèse documentaire pour la GED. "
    "Ta seule responsabilité est de produire des résumés professionnels, "
    "précis et concis en français. "
    "Tu adaptes ton résumé au type de document fourni. "
    "Tu n'inventes aucune information absente du document source. "
    "Tu rédiges en prose fluide, sans listes ni tirets."
)


@mcp.tool()
def summarize_document(
    text:          str,
    filename:      str,
    document_type: str,
    extraction:    str = "",
    system_prompt: str = "",
) -> str:

    if not text or not text.strip():
        print(f"[SummarizerServer] WARN: texte vide pour '{filename}'", file=sys.stderr)
        return json.dumps({"summary": ""}, ensure_ascii=False)

    text_clean = text.strip()
    system     = system_prompt.strip() if system_prompt.strip() else _DEFAULT_SYSTEM

    print(
        f"[SummarizerServer] Début résumé | '{filename}' | type={document_type} | "
        f"{len(text_clean)} car.",
        file=sys.stderr,
    )

    summary = ""

    try:
        from services.llm_client import summarize as llm_summarize
        summary = llm_summarize(text_clean, document_type, system=system)
        if summary:
            summary = summary.strip()
        print(
            f"[SummarizerServer] llm_summarize OK: {len(summary)} car.",
            file=sys.stderr,
        )
    except Exception as e:
        print(f"[SummarizerServer] llm_summarize FAILED: {e}", file=sys.stderr)
        summary = ""

    if not summary:
        print(
            f"[SummarizerServer] llm_summarize vide → fallback generate()",
            file=sys.stderr,
        )
        try:
            from services.llm_client import generate
            type_hint = f" (type : {document_type})" if document_type else ""
            prompt = (
                f"Résume ce document{type_hint} en 4-6 phrases "
                f"claires et professionnelles en français :\n\n"
                f"{text_clean[:3000]}"
            )
            summary = generate(prompt, max_tokens=400, system=system).strip()
            print(
                f"[SummarizerServer] generate() OK: {len(summary)} car.",
                file=sys.stderr,
            )
        except Exception as e2:
            print(f"[SummarizerServer] generate() FAILED: {e2}", file=sys.stderr)
            summary = ""

    if not summary:
        print(
            f"[SummarizerServer] Tout a échoué → extrait brut",
            file=sys.stderr,
        )
        summary = f"[Extrait automatique — résumé IA indisponible]\n{text_clean[:600]}"

    if extraction and extraction.strip() and summary:
        summary = f"{summary}\n\nInformations extraites :\n{extraction.strip()}"

    print(
        f"[SummarizerServer] Résumé final : {len(summary)} car. | type={document_type}",
        file=sys.stderr,
    )

    return json.dumps({"summary": summary}, ensure_ascii=False)


if __name__ == "__main__":
    try:
        mcp.run(transport="stdio")
    except Exception as e:
        print(f"[SummarizerServer] erreur démarrage : {e}", file=sys.stderr)
        sys.exit(1)