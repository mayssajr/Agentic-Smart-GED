from __future__ import annotations

import io
import os
import sys


def _log(msg: str) -> None:
    print(f"[DocumentParser] {msg}", file=sys.stderr)


def _extract_pdf_native(content: bytes) -> str:
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(content))
        text   = "\n".join(p.extract_text() or "" for p in reader.pages).strip()
        if text:
            _log(f"pypdf OK: {len(text)} car.")
        return text
    except ImportError:
        return ""
    except Exception as e:
        _log(f"pypdf: {e}")
        return ""


def _extract_pdf_pdfminer(content: bytes) -> str:
    try:
        from pdfminer.high_level import extract_text_to_fp
        from pdfminer.layout    import LAParams
        buf = io.StringIO()
        extract_text_to_fp(io.BytesIO(content), buf,
                           laparams=LAParams(), output_type="text", codec="utf-8")
        text = buf.getvalue().strip()
        if text:
            _log(f"pdfminer OK: {len(text)} car.")
        return text
    except ImportError:
        return ""
    except Exception as e:
        _log(f"pdfminer: {e}")
        return ""


def _ocr_tesseract(content: bytes) -> str:
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
        tesseract_cmd = os.getenv("TESSERACT_CMD",
                                  r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if os.path.exists(tesseract_cmd):
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        poppler_path = os.getenv("POPPLER_PATH", None)
        kwargs = {"dpi": 200}
        if poppler_path and os.path.exists(poppler_path):
            kwargs["poppler_path"] = poppler_path
        _log("Tesseract OCR en cours...")
        images = convert_from_bytes(content, **kwargs)
        text   = "\n".join(
            pytesseract.image_to_string(img, lang="fra+eng").strip()
            for img in images
        )
        if text.strip():
            _log(f"Tesseract OK: {len(text)} car.")
        return text
    except ImportError:
        return ""
    except Exception as e:
        _log(f"Tesseract: {e}")
        return ""


def _ocr_easyocr(content: bytes) -> str:
    try:
        from pdf2image import convert_from_bytes
        import easyocr
        import numpy as np
        poppler_path = os.getenv("POPPLER_PATH", None)
        kwargs = {"dpi": 150}
        if poppler_path and os.path.exists(poppler_path):
            kwargs["poppler_path"] = poppler_path
        _log("EasyOCR en cours...")
        reader = easyocr.Reader(["fr", "en"], gpu=False, verbose=False)
        images = convert_from_bytes(content, **kwargs)
        texts  = []
        for img in images:
            texts.extend(reader.readtext(np.array(img), detail=0))
        text = " ".join(texts).strip()
        if text:
            _log(f"EasyOCR OK: {len(text)} car.")
        return text
    except ImportError:
        return ""
    except Exception as e:
        _log(f"EasyOCR: {e}")
        return ""


def _ocr_image(content: bytes) -> str:
    try:
        from PIL import Image
        import pytesseract
        tesseract_cmd = os.getenv("TESSERACT_CMD",
                                  r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if os.path.exists(tesseract_cmd):
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        img  = Image.open(io.BytesIO(content))
        text = pytesseract.image_to_string(img, lang="fra+eng").strip()
        return text
    except Exception:
        pass
    try:
        import easyocr
        import numpy as np
        from PIL import Image
        reader = easyocr.Reader(["fr", "en"], gpu=False, verbose=False)
        img    = Image.open(io.BytesIO(content))
        result = reader.readtext(np.array(img), detail=0)
        return " ".join(result).strip()
    except Exception:
        return ""


def _extract_docx(content: bytes) -> str:
    try:
        from docx import Document
        doc   = Document(io.BytesIO(content))
        text  = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
        _log(f"python-docx OK: {len(text)} car.")
        return text
    except ImportError:
        return ""
    except Exception as e:
        _log(f"DOCX: {e}")
        return ""


def extract_text(filename: str, content: bytes) -> str:
    """
    Extrait le texte d'un document.
    Cascade complète avec fallback OCR automatique si texte natif vide.
    """
    ext = os.path.splitext(filename.lower())[1]

    if ext == ".pdf":
        text = _extract_pdf_native(content)
        if text and len(text.strip()) > 30:
            return text
        text = _extract_pdf_pdfminer(content)
        if text and len(text.strip()) > 30:
            return text
        _log("Texte natif vide → OCR")
        text = _ocr_tesseract(content)
        if text and len(text.strip()) > 30:
            return text
        return _ocr_easyocr(content)

    if ext in (".docx", ".doc"):
        return _extract_docx(content)

    if ext in (".txt", ".md", ".csv"):
        try:
            return content.decode("utf-8", errors="replace").strip()
        except Exception:
            return ""

    if ext in (".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"):
        return _ocr_image(content)

    _log(f"Format non supporte: {ext}")
    return ""