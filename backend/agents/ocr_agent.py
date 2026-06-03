import os
import sys

from agents.base_agent import BaseAgent, BASE_DIR

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


class OCRAgent(BaseAgent):
    NAME         = "OCRAgent"
    TOOL_SERVERS = []  # extraction en process, pas de MCP

    def run(self, filename: str, content: bytes, **_) -> dict:
        self._reset()
        ext = filename.rsplit(".", 1)[-1].upper() if "." in filename else "INCONNU"

        self._step("thought",
            f"Extraction depuis '{filename}' ({len(content):,} octets, {ext}). "
            "Cascade : pypdf → Tesseract → EasyOCR.")

        text = ""

        # ── Étape 1 : extraction texte normale ───────────────────────
        self._step("action", f"document_parser.extract_text('{filename}')")
        try:
            from services.document_parser import extract_text
            text = extract_text(filename, content)
            if text.strip():
                self._step("observe",
                    f"Extraction texte OK : {len(text.strip()):,} car.")
            else:
                self._step("observe",
                    "Texte vide après extraction — déclenchement OCR cascade.")
        except Exception as exc:
            self._step("observe", f"extract_text failed : {exc} → OCR cascade")

        # ── Étape 2 : OCR cascade si texte vide ──────────────────────
        if not text.strip():
            self._step("action", "document_parser._ocr_pdf() — cascade Tesseract→EasyOCR")
            try:
                from services.document_parser import _ocr_pdf
                text = _ocr_pdf(content)
                if text.strip():
                    self._step("observe",
                        f"OCR cascade OK : {len(text.strip()):,} car.")
                else:
                    self._step("observe",
                        "OCR n'a produit aucun texte lisible.")
            except Exception as exc:
                self._step("observe", f"OCR cascade failed : {exc}")

        ms = self._elapsed_ms()
        self._step("answer", f"Texte prêt : {len(text):,} car. en {ms}ms.")

        return {
            "text":          text,
            "char_count":    len(text),
            "processing_ms": ms,
            "react_trace":   self.trace,
        }