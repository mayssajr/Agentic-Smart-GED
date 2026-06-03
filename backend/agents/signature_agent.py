"""
SignatureAgent — version fusionnée
====================================
Prend le meilleur des deux versions :

  De l'ancien SignerAgent :
    ✅ Rendu visuel complet (zone grise, badge vert, ligne séparatrice)
    ✅ Conversion TXT → PDF automatique
    ✅ Hash SHA256 pour l'audit d'intégrité
    ✅ Placement sur la dernière page par défaut
    ✅ BaseAgent + trace ReAct complète
    ✅ register_signature() sur STM

  Du nouveau SignatureAgent :
    ✅ detect() — détection zones de signature manquantes
    ✅ get_profile() / learn() — profil utilisateur persistant
    ✅ Mode automatique après MIN_CONFIRMATIONS signatures
    ✅ check_and_auto_sign() — utilisable depuis analyze_document_files()
    ✅ Moyennage des préférences de position
"""
from __future__ import annotations

import base64
import hashlib
import io
import os
import re
import sys
from datetime import datetime, timezone
from typing import Optional

from agents.base_agent import BaseAgent
from memory.long_term  import get_long_term_memory
from memory.short_term import get_short_term_memory

# ── Seuil d'apprentissage ─────────────────────────────────────────────────────
MIN_CONFIRMATIONS: int = int(os.getenv("SIGNATURE_MIN_CONFIRMATIONS", "2"))

# ── Mots-clés de détection de zones vides ────────────────────────────────────
_SIG_KEYWORDS = [
    r"signature\s*:?\s*[_\.]{3,}",
    r"signé\s*(par|le|à)?\s*:?\s*[_\.]{3,}",
    r"cachet\s*(et\s*signature)?\s*:?\s*[_\.]{3,}",
    r"lu\s+et\s+approuvé\s*:?\s*[_\.]{3,}",
    r"bon\s+pour\s+accord\s*:?\s*[_\.]{3,}",
    r"paraphe\s*:?\s*[_\.]{3,}",
    r"(?<!\w)_{5,}",
    r"\.{5,}",
    r"\[\s*signature\s*\]",
    r"\[\s*signer\s+ici\s*\]",
    r"à\s+signer",
    r"signature\s+requise",
    r"signature\s+manquante",
    r"sign\s+here",
]
_SIG_RE = re.compile("|".join(_SIG_KEYWORDS), re.IGNORECASE)

_SIGNABLE_TYPES = {
    "Contrat de travail", "Juridique", "Contrat",
    "Accord", "Convention", "Avenant", "NDA", "Autre",
}


class SignatureAgent(BaseAgent):
    """
    Agent unique de gestion complète du cycle de vie de la signature.

    Responsabilités :
      1. detect()              — zones manquantes dans le texte ou AcroForm
      2. get_profile/learn()   — profil utilisateur persistant (LTM)
      3. _apply_signature()    — apposition physique PDF (reportlab + pypdf)
      4. run()                 — point d'entrée principal
      5. check_and_auto_sign() — mode automatique depuis analyze_document_files()
    """

    NAME          = "SignatureAgent"
    TOOL_SERVERS  = []
    SYSTEM_PROMPT = (
        "Tu es un agent de signature électronique sécurisé. "
        "Tu vérifies systématiquement que le document n'a pas déjà été signé. "
        "Tu crées une piste d'audit complète de chaque signature."
    )

    def __init__(self) -> None:
        super().__init__()
        self.ltm = get_long_term_memory()
        self.stm = get_short_term_memory()

    # ──────────────────────────────────────────────────────────────────────────
    # 1. DÉTECTION
    # ──────────────────────────────────────────────────────────────────────────

    def detect(
        self,
        document_text: str            = "",
        document_type: str            = "",
        filename:      str            = "",
        pdf_bytes:     Optional[bytes] = None,
    ) -> dict:
        """
        Détecte si un document nécessite une signature.

        Retourne :
          {
            "needs_signature": bool,
            "confidence":      float,
            "zones":           list[str],
            "method":          str,
          }
        """
        zones:  list[str] = []
        method: str       = "text"

        # Analyse textuelle
        if document_text:
            for m in _SIG_RE.finditer(document_text):
                start = max(0, m.start() - 40)
                end   = min(len(document_text), m.end() + 40)
                zones.append(document_text[start:end].strip())

        # Analyse AcroForm PDF
        if pdf_bytes and not zones:
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
                fields = reader.get_fields() or {}
                for name, field in fields.items():
                    ft = (field.get("/FT") or "").strip("/")
                    if ft == "Sig" and not field.get("/V"):
                        zones.append(f"Champ signature PDF vide : {name}")
                        method = "acroform"
            except Exception as e:
                self._step("detect", f"AcroForm parsing non-bloquant: {e}")

        type_hint  = document_type in _SIGNABLE_TYPES
        needs      = bool(zones) or (
            type_hint and bool(re.search(r"signature", document_text, re.IGNORECASE))
        )
        confidence = 0.0
        if zones:
            confidence = min(0.95, 0.5 + 0.15 * len(zones))
        elif type_hint:
            confidence = 0.3

        self._step("detect",
            f"needs={needs} | zones={len(zones)} | "
            f"confidence={confidence:.0%} | type='{document_type}'")

        return {
            "needs_signature": needs,
            "confidence":      round(confidence, 3),
            "zones":           zones[:5],
            "method":          method,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # 2. PROFIL UTILISATEUR — apprentissage
    # ──────────────────────────────────────────────────────────────────────────

    def _profile_key(self, user_id: str) -> str:
        return f"sig_profile_{user_id}"

    def get_profile(self, user_id: str) -> dict:
        """Retourne le profil mémorisé ou un profil vide par défaut."""
        try:
            raw = self.ltm.recall(self.NAME, self._profile_key(user_id))
            if raw and isinstance(raw, dict):
                return raw
        except Exception as e:
            self._step("profile", f"recall failed: {e}")
        return {
            "user_id":        user_id,
            "signer_name":    "",
            "confirmations":  0,
            "auto_enabled":   False,
            "signature_png":  None,
            "preferred_page": -1,      # -1 = dernière page (cohérent avec l'ancien)
            "preferred_x":    80.0,
            "preferred_y":    60.0,
            "preferred_w":    200.0,
            "preferred_h":    60.0,
            "doc_types":      [],
            "last_signed_at": "",
        }

    def learn(
        self,
        user_id:       str,
        signer_name:   str,
        signature_png: str,
        filename:      str   = "",
        document_type: str   = "",
        page:          int   = -1,
        x:             float = 80.0,
        y:             float = 60.0,
        width:         float = 200.0,
        height:        float = 60.0,
    ) -> dict:
        """
        Enregistre une signature confirmée, met à jour le profil,
        active le mode automatique dès MIN_CONFIRMATIONS atteint.
        """
        profile = self.get_profile(user_id)

        profile["user_id"]       = user_id
        profile["signer_name"]   = signer_name or profile["signer_name"]
        profile["confirmations"] = profile.get("confirmations", 0) + 1
        profile["signature_png"] = signature_png

        # Moyennage cumulatif des préférences de position
        n = profile["confirmations"]
        def _avg(old: float, new: float) -> float:
            return round((old * (n - 1) + new) / n, 2)

        profile["preferred_page"] = page
        profile["preferred_x"]    = _avg(profile.get("preferred_x", x), x)
        profile["preferred_y"]    = _avg(profile.get("preferred_y", y), y)
        profile["preferred_w"]    = _avg(profile.get("preferred_w", width), width)
        profile["preferred_h"]    = _avg(profile.get("preferred_h", height), height)

        if document_type and document_type not in profile.get("doc_types", []):
            profile.setdefault("doc_types", []).append(document_type)

        profile["last_signed_at"] = datetime.now(timezone.utc).isoformat()

        was_auto             = profile.get("auto_enabled", False)
        profile["auto_enabled"] = profile["confirmations"] >= MIN_CONFIRMATIONS

        if profile["auto_enabled"] and not was_auto:
            self._step("learn",
                f"✅ Mode automatique activé pour '{user_id}' "
                f"({profile['confirmations']} confirmations ≥ {MIN_CONFIRMATIONS})")

        try:
            self.ltm.memorize(self.NAME, self._profile_key(user_id), profile)
            self._step("learn",
                f"Profil mis à jour | confirmations={profile['confirmations']} | "
                f"auto={profile['auto_enabled']}")
        except Exception as e:
            self._step("learn", f"memorize failed: {e}")

        return profile

    # ──────────────────────────────────────────────────────────────────────────
    # 3. APPOSITION PHYSIQUE — rendu visuel complet (repris de l'ancien)
    # ──────────────────────────────────────────────────────────────────────────

    def _ensure_pdf(self, raw_bytes: bytes) -> bytes:
        """
        Convertit TXT → PDF si nécessaire.
        Repris de l'ancien SignerAgent.
        """
        if raw_bytes.startswith(b"%PDF"):
            return raw_bytes

        self._step("observe", "Format TXT détecté → conversion automatique en PDF")
        try:
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units  import cm
            from reportlab.platypus   import SimpleDocTemplate, Paragraph, Spacer

            text = raw_bytes.decode("utf-8", errors="replace")
            buf  = io.BytesIO()
            doc  = SimpleDocTemplate(
                buf, pagesize=(595.28, 841.89),
                leftMargin=2*cm, rightMargin=2*cm,
                topMargin=2*cm, bottomMargin=3*cm,
            )
            styles = getSampleStyleSheet()
            story  = []
            for line in text.split("\n"):
                safe = (line.replace("&", "&amp;")
                            .replace("<", "&lt;")
                            .replace(">", "&gt;"))
                story.append(Paragraph(safe or "&nbsp;", styles["Normal"]))
                story.append(Spacer(1, 2))
            doc.build(story)
            return buf.getvalue()
        except Exception as e:
            raise RuntimeError(f"Conversion TXT→PDF échouée : {e}")

    def _apply_signature(
        self,
        pdf_bytes:     bytes,
        signature_png: str,
        signer_name:   str   = "Signataire",
        now_str:       str   = "",
    ) -> bytes:
        """
        Appose la signature sur la DERNIÈRE page avec le rendu visuel complet
        de l'ancien SignerAgent : zone grise, badge vert, ligne séparatrice.

        Paramètres de position gérés automatiquement (zone bas de page).
        """
        try:
            import pypdf
            from reportlab.pdfgen import canvas as rl_canvas
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError(
                f"Dépendances manquantes : {exc}. "
                "pip install pypdf reportlab pillow"
            )

        if not now_str:
            now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

        reader  = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        n_pages = len(reader.pages)
        last_pi = n_pages - 1
        box     = reader.pages[last_pi].mediabox
        pw, ph  = float(box.width), float(box.height)

        self._step("observe",
            f"PDF : {n_pages} page(s) | signature sur page {last_pi + 1} "
            f"({pw:.0f}×{ph:.0f}pt)")

        # ── Overlay reportlab ─────────────────────────────────────────────────
        SZ_H   = 110.0
        MARGIN = 60.0
        ZONE_Y = 20.0
        ZONE_TOP = ZONE_Y + SZ_H
        sig_w  = min(200.0, pw * 0.35)
        sig_h  = 60.0
        sig_x  = MARGIN
        sig_y  = ZONE_Y + (SZ_H - sig_h) / 2 + 5

        ov = io.BytesIO()
        c  = rl_canvas.Canvas(ov, pagesize=(pw, ph))

        # Zone de fond gris clair
        c.setFillColorRGB(0.97, 0.97, 0.97)
        c.rect(0, ZONE_Y, pw, SZ_H, fill=1, stroke=0)

        # Ligne séparatrice haute
        c.setStrokeColorRGB(0.5, 0.5, 0.5)
        c.setLineWidth(0.8)
        c.line(MARGIN, ZONE_TOP, pw - MARGIN, ZONE_TOP)

        # Label "ZONE DE SIGNATURE"
        c.setFont("Helvetica-Bold", 7.5)
        c.setFillColorRGB(0.4, 0.4, 0.4)
        c.drawString(MARGIN, ZONE_TOP + 4, "ZONE DE SIGNATURE")

        # Image de la signature
        sig_bytes = base64.b64decode(signature_png)
        try:
            sig_img  = Image.open(io.BytesIO(sig_bytes)).convert("RGBA")
            sig_path = os.path.join(os.environ.get("TEMP", "/tmp"), "_ged_sig.png")
            sig_img.save(sig_path, "PNG")
            c.drawImage(sig_path, sig_x, sig_y, width=sig_w, height=sig_h, mask="auto")
        except Exception as e:
            self._step("observe", f"Image signature failed, fallback texte: {e}")
            c.setFont("Helvetica-Oblique", 16)
            c.setFillColorRGB(0.1, 0.1, 0.5)
            c.drawString(sig_x, sig_y + sig_h / 2, signer_name)

        # Ligne sous la signature + nom + date
        c.setStrokeColorRGB(0.3, 0.3, 0.3)
        c.setLineWidth(0.4)
        c.line(sig_x, sig_y - 2, sig_x + sig_w, sig_y - 2)
        c.setFont("Helvetica", 7.5)
        c.setFillColorRGB(0.25, 0.25, 0.25)
        c.drawString(sig_x, sig_y - 13, f"{signer_name}  ·  Signé le {now_str}")

        # Badge vert "✓ SIGNÉ ÉLECTRONIQUEMENT"
        bx = pw - MARGIN - 90
        by = ZONE_Y + SZ_H / 2 - 10
        c.setFillColorRGB(0.22, 0.7, 0.4)
        c.roundRect(bx, by, 90, 20, 5, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 8)
        c.setFillColorRGB(1, 1, 1)
        c.drawCentredString(bx + 45, by + 6, "✓ SIGNÉ ÉLECTRONIQUEMENT")

        c.save()
        ov.seek(0)

        # ── Fusion overlay sur la dernière page ───────────────────────────────
        self._step("action", f"Fusion overlay sur la page {last_pi + 1}")
        r2  = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        ov2 = pypdf.PdfReader(ov)
        w   = pypdf.PdfWriter()

        for i, pg in enumerate(r2.pages):
            if i == last_pi:
                pg.merge_page(ov2.pages[0])
            w.add_page(pg)

        out = io.BytesIO()
        w.write(out)
        return out.getvalue()

    # ──────────────────────────────────────────────────────────────────────────
    # 4. POINT D'ENTRÉE PRINCIPAL
    # ──────────────────────────────────────────────────────────────────────────

    def run(
        self,
        pdf_base64:    str,
        signature_png: str,
        signer_name:   str   = "Signataire",
        filename:      str   = "",
        page:          int   = -1,
        x:             float = 80.0,
        y:             float = 60.0,
        width:         float = 200.0,
        height:        float = 60.0,
        user_id:       str   = "",
        document_type: str   = "",
        **_,
    ) -> dict:
        """
        Point d'entrée unique :
          1. Vérifie doublon (STM + LTM)
          2. Décode et convertit le PDF si nécessaire
          3. Appose la signature avec rendu visuel complet
          4. Persiste en STM + LTM (hash SHA256)
          5. Met à jour le profil utilisateur (apprentissage)
        """
        self._reset()
        now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

        self._step("thought",
            f"Signature par « {signer_name} » le {now_str} | "
            f"fichier='{filename}' | user='{user_id}'")

        # ── 1. Vérification doublon STM ───────────────────────────────────────
        if filename and self.stm.is_signed(filename):
            sig_info = self.stm.get_signature_info(filename)
            self._step("observe",
                f"⚠ Déjà signé cette session par {sig_info.get('signer', '?')}")
            return {
                "signed":         False,
                "already_signed": True,
                "signer_name":    sig_info.get("signer", ""),
                "filename":       filename,
                "pdf_base64":     pdf_base64,
                "profile":        self.get_profile(user_id) if user_id else {},
                "auto_enabled":   False,
                "error": (
                    f"Ce document a déjà été signé par {sig_info.get('signer', '?')} "
                    f"le {sig_info.get('timestamp', '?')}."
                ),
                "processing_ms":  self._elapsed_ms(),
                "react_trace":    self.trace,
            }

        # ── 2. Vérification doublon LTM (hash SHA256) ─────────────────────────
        try:
            pdf_bytes_check = base64.b64decode(pdf_base64) if pdf_base64 else b""
            c_hash = hashlib.sha256(pdf_bytes_check).hexdigest()[:16] if pdf_bytes_check else ""
        except Exception:
            pdf_bytes_check, c_hash = b"", ""

        if filename and c_hash:
            existing = self.ltm.is_document_signed(filename, c_hash)
            if existing:
                self._step("observe",
                    f"⚠ Déjà signé en DB par {existing.get('signer_name', '?')} "
                    f"le {existing.get('signed_at', '?')[:10]}")
                return {
                    "signed":         False,
                    "already_signed": True,
                    "signer_name":    existing.get("signer_name", ""),
                    "filename":       filename,
                    "pdf_base64":     pdf_base64,
                    "profile":        self.get_profile(user_id) if user_id else {},
                    "auto_enabled":   False,
                    "error": (
                        f"Document déjà signé par {existing.get('signer_name', '?')} "
                        f"le {existing.get('signed_at', '?')[:10]}."
                    ),
                    "processing_ms":  self._elapsed_ms(),
                    "react_trace":    self.trace,
                }

        self._step("observe", "Registre vérifié — document non signé. Signature autorisée.")

        # ── 3. Décoder + convertir TXT→PDF si nécessaire ─────────────────────
        try:
            raw_bytes = base64.b64decode(pdf_base64)
            pdf_bytes = self._ensure_pdf(raw_bytes)
        except Exception as e:
            return {
                "signed": False, "already_signed": False,
                "error": f"PDF invalide : {e}",
                "pdf_base64": "", "filename": filename,
                "signer_name": signer_name, "profile": {},
                "auto_enabled": False,
                "processing_ms": self._elapsed_ms(), "react_trace": self.trace,
            }

        # ── 4. Apposer la signature ────────────────────────────────────────────
        self._step("action", "Création overlay zone de signature")
        try:
            signed_bytes = self._apply_signature(pdf_bytes, signature_png, signer_name, now_str)
            signed_b64   = base64.b64encode(signed_bytes).decode()
            pdf_hash     = hashlib.sha256(signed_bytes).hexdigest()[:16]
            self._step("observe",
                f"✓ PDF signé : {len(signed_bytes)} bytes | hash={pdf_hash}")
        except Exception as e:
            self._step("observe", f"✗ Erreur signature : {e}")
            return {
                "signed": False, "already_signed": False, "error": str(e),
                "pdf_base64": pdf_base64, "filename": filename,
                "signer_name": signer_name, "profile": {},
                "auto_enabled": False,
                "processing_ms": self._elapsed_ms(), "react_trace": self.trace,
            }

        # ── 5. Persister STM + LTM ────────────────────────────────────────────
        try:
            self.stm.mark_signed(filename or "document", signer_name)
            self.ltm.save_signed_document(
                filename or "document", signer_name,
                c_hash, len(signed_bytes),
            )
            self._step("observe", "Signature persistée STM + LTM")
        except Exception as e:
            self._step("observe", f"Persistance non-bloquante: {e}")

        # ── 6. Apprentissage profil utilisateur ───────────────────────────────
        profile      = {}
        auto_enabled = False
        if user_id:
            try:
                profile      = self.learn(
                    user_id=user_id, signer_name=signer_name,
                    signature_png=signature_png, filename=filename,
                    document_type=document_type,
                    page=page, x=x, y=y, width=width, height=height,
                )
                auto_enabled = profile.get("auto_enabled", False)
            except Exception as e:
                self._step("observe", f"learn() non-bloquant: {e}")

        ms = self._elapsed_ms()
        self._step("answer",
            f"✓ Signé par {signer_name} le {now_str} "
            f"(hash={pdf_hash}) en {ms}ms | auto={auto_enabled}")

        return {
            "signed":         True,
            "already_signed": False,
            "pdf_base64":     signed_b64,
            "signer_name":    signer_name,
            "signer":         signer_name,      # rétrocompat ancien champ
            "timestamp":      now_str,
            "filename":       filename,
            "pdf_hash":       pdf_hash,
            "message":        f"Signé par {signer_name} le {now_str}",
            "profile":        profile,
            "auto_enabled":   auto_enabled,
            "error":          "",
            "processing_ms":  ms,
            "react_trace":    self.trace,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # 5. MODE AUTOMATIQUE — appelé depuis analyze_document_files()
    # ──────────────────────────────────────────────────────────────────────────

    def check_and_auto_sign(
        self,
        document_text: str,
        document_type: str,
        filename:      str,
        user_id:       str,
        pdf_base64:    str            = "",
        pdf_bytes:     Optional[bytes] = None,
    ) -> dict:
        """
        Détecte les zones manquantes ET signe automatiquement si le profil
        utilisateur est suffisamment confirmé (≥ MIN_CONFIRMATIONS).

        Appelé dans orchestrator.analyze_document_files() après la classification.
        """
        # Détection
        detection = self.detect(
            document_text=document_text,
            document_type=document_type,
            filename=filename,
            pdf_bytes=pdf_bytes,
        )

        if not detection["needs_signature"]:
            return {
                "needs_signature": False,
                "auto_signed":     False,
                "sign_result":     None,
                "profile":         self.get_profile(user_id) if user_id else {},
                "reason":          "Aucune zone de signature détectée.",
            }

        profile = self.get_profile(user_id) if user_id else {}

        if not profile.get("auto_enabled"):
            remaining = max(0, MIN_CONFIRMATIONS - profile.get("confirmations", 0))
            self._step("check_auto",
                f"Mode auto désactivé — {remaining} confirmation(s) manquante(s)")
            return {
                "needs_signature": True,
                "auto_signed":     False,
                "sign_result":     None,
                "profile":         profile,
                "reason": (
                    f"Signature requise. Encore {remaining} confirmation(s) "
                    f"pour activer le mode automatique."
                ),
            }

        # Mode auto : préparer le PDF
        if not pdf_base64 and pdf_bytes:
            pdf_base64 = base64.b64encode(pdf_bytes).decode()

        if not pdf_base64 or not profile.get("signature_png"):
            return {
                "needs_signature": True,
                "auto_signed":     False,
                "sign_result":     None,
                "profile":         profile,
                "reason":          "Mode auto activé mais PDF ou signature PNG manquant.",
            }

        self._step("check_auto",
            f"Mode auto → signature automatique | "
            f"user='{user_id}' | confirmations={profile['confirmations']}")

        sign_result = self.run(
            pdf_base64    = pdf_base64,
            signature_png = profile["signature_png"],
            signer_name   = profile["signer_name"] or user_id,
            filename      = filename,
            page          = profile.get("preferred_page", -1),
            x             = profile.get("preferred_x", 80.0),
            y             = profile.get("preferred_y", 60.0),
            width         = profile.get("preferred_w", 200.0),
            height        = profile.get("preferred_h", 60.0),
            user_id       = user_id,
            document_type = document_type,
        )

        return {
            "needs_signature": True,
            "auto_signed":     sign_result.get("signed", False),
            "sign_result":     sign_result,
            "profile":         sign_result.get("profile", profile),
            "reason": (
                f"Signature automatique appliquée par {profile['signer_name']} "
                f"({profile['confirmations']} confirmations)."
                if sign_result.get("signed")
                else f"Échec auto-sign : {sign_result.get('error')}"
            ),
        }