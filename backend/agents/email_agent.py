from __future__ import annotations
import base64 as _b64
import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from email.mime.application import MIMEApplication

from agents.base_agent import BaseAgent
from core.constants import MCP_SPECS, SkillID


# ── Expéditeur par défaut ──────────────────────────────────────────────────────
# Utilisé pour signer les emails si aucune variable COMPANY_NAME n'est définie.
_SENDER_NAME = os.getenv("COMPANY_NAME", "AeroTech RH")

# ── Prompts système ────────────────────────────────────────────────────────────

_GENERIC_EMAIL_SYSTEM = (
    "Tu rédiges des emails professionnels GED en français. "
    "Email clair, concis, max 200 mots. "
    "Format :\nSUJET: <sujet>\nCORPS: <corps>"
)

# RÈGLES STRICTES pour le LLM :
# - Ne jamais écrire "[Votre Nom]", "[Signature]" ou tout placeholder entre crochets.
# - Toujours signer avec le nom de l'expéditeur fourni dans le contexte.
# - Utiliser UNIQUEMENT les données fournies — ne rien inventer.
# - Produire uniquement SUJET: et CORPS: — aucun texte avant ou après.
_RECRUITMENT_EMAIL_SYSTEM = f"""Tu es un expert RH chez {_SENDER_NAME}.
Tu rédiges des emails de recrutement professionnels, chaleureux et personnalisés en français.

RÈGLES ABSOLUES :
1. Utilise UNIQUEMENT les informations fournies dans le contexte. Ne JAMAIS inventer de détails.
2. Si des points forts sont fournis, les mentionner explicitement dans l'email — pas de formule générique.
3. Si un créneau d'entretien est fourni, l'inclure exactement tel quel.
4. JAMAIS de placeholder entre crochets comme [Votre Nom], [Date], [Lien]. Utilise les vraies valeurs.
5. Signer TOUJOURS avec "Cordialement,\\n{_SENDER_NAME}" — pas autre chose.
6. Longueur : 120 à 200 mots maximum. Email concis et direct.

Format de sortie STRICT (rien d'autre, pas de texte avant ou après) :
SUJET: <sujet complet>
CORPS: <corps de l'email complet, avec salutation et signature>"""


class EmailAgent(BaseAgent):
    NAME   = "EmailAgent"
    SKILLS = [SkillID.EMAIL_REPORT.value, SkillID.EMAIL_SIGNED.value]
    SYSTEM_PROMPT = _GENERIC_EMAIL_SYSTEM
    TOOL_SERVERS  = []

    # ─────────────────────────────────────────────────────────────────────────
    # Point d'entrée principal (usage générique GED)
    # ─────────────────────────────────────────────────────────────────────────

    def run(
        self,
        mode:          str,
        to:            str,
        filename:      str  = "",
        document_type: str  = "",
        summary:       str  = "",
        extraction:    str  = "",
        subject:       str  = "",
        body:          str  = "",
        pdf_base64:    str  = "",
        **_,
    ) -> dict:
        self._reset()
        self._step("thought", f"EmailAgent | mode={mode} | to={to}")

        if not to or "@" not in to:
            self._step("observe", f"Adresse invalide : '{to}'")
            return {"success": False, "error": f"Adresse invalide : '{to}'",
                    "processing_ms": self._elapsed_ms()}

        if not subject or not body:
            self._step("action", "Rédaction email via LLM")
            subject, body = self._write_email(filename, document_type, summary, extraction)

        self._step("observe", f"Sujet : '{subject[:60]}'")

        attachment_bytes: bytes | None = None
        if pdf_base64:
            try:
                attachment_bytes = _b64.b64decode(pdf_base64)
            except Exception as e:
                self._step("observe", f"Décodage base64 failed : {e} → envoi sans PJ")

        if mode == "signed_pdf":
            return self._send_smtp(to, subject, body, pdf_base64, filename)

        if not attachment_bytes:
            result = self._send_via_gmail_mcp(to, subject, body)
            if result.get("success"):
                return {**result, "subject_used": subject, "body_sent": body,
                        "processing_ms": self._elapsed_ms()}
            self._step("observe", f"Gmail MCP failed : {result.get('error')} → fallback")

        if self._is_gmail_native_available():
            ok, info = self._send_gmail_native(
                to=to, subject=subject, body=body,
                attachment_bytes=attachment_bytes,
                attachment_filename=(filename or "document.pdf") if attachment_bytes else None,
            )
            if ok:
                return {"success": True, "email_to": to, "subject_used": subject,
                        "body_sent": body,
                        "has_attachment": bool(attachment_bytes),
                        "processing_ms": self._elapsed_ms()}
            self._step("observe", f"Gmail natif failed : {info} → SMTP")

        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pass = os.getenv("SMTP_PASSWORD", "") or os.getenv("SMTP_PASS", "")
        if smtp_user and smtp_pass:
            return self._send_smtp(to, subject, body, pdf_base64, filename)

        return {"success": False, "error": "Aucune méthode d'envoi disponible.",
                "processing_ms": self._elapsed_ms()}

    # ─────────────────────────────────────────────────────────────────────────
    # Email de scoring / recommandation post-analyse CV
    # ─────────────────────────────────────────────────────────────────────────

    def send_score_email(
        self,
        to:             str,
        candidate_name: str,
        position:       str,
        recommendation: str,           # "Entretien" | "ListeAttente" | "Refus"
        score:          int   = 0,
        strengths:      list[str] | None = None,
        gaps:           list[str] | None = None,
        summary:        str   = "",
        slot_formatted: str   = "",
        meet_link:      str   = "",
        event_link:     str   = "",
        **_,
    ) -> dict:
        self._reset()
        self._step("thought",
            f"send_score_email | reco={recommendation} | to={to} | poste={position}")

        if not to or "@" not in to:
            return {"success": False, "error": f"Adresse invalide : '{to}'"}

        subject, body = self._write_score_email(
            candidate_name = candidate_name,
            position       = position,
            recommendation = recommendation,
            score          = score,
            strengths      = strengths or [],
            gaps           = gaps or [],
            summary        = summary,
            slot_formatted = slot_formatted,
            meet_link      = meet_link,
            event_link     = event_link,
        )
        self._step("observe", f"Sujet généré : {subject[:60]}")
        self._step("observe", f"Corps (100 car.) : {body[:100]}")
        result = self._dispatch(to, subject, body)
        result["recommendation"] = recommendation
        result["score"]          = score
        result["body_sent"]      = body      # ← exposé pour que la bannière l'affiche
        result["subject_sent"]   = subject
        return result

    def _write_score_email(
        self,
        candidate_name: str,
        position:       str,
        recommendation: str,
        score:          int,
        strengths:      list[str],
        gaps:           list[str],
        summary:        str,
        slot_formatted: str,
        meet_link:      str,
        event_link:     str,
    ) -> tuple[str, str]:

        first = candidate_name.split()[0] if candidate_name else "Candidat(e)"

        # ── Construire le bloc créneau ────────────────────────────────────────
        slot_block = ""
        if slot_formatted:
            slot_block = f"\nCréneau retenu : {slot_formatted}"
            if meet_link:
                slot_block += f"\nLien Google Meet : {meet_link}"
            elif event_link:
                slot_block += f"\nLien Google Calendar : {event_link}"

        # ── Construire les blocs points forts / lacunes ───────────────────────
        strengths_block = ""
        if strengths:
            strengths_block = "Points forts identifiés :\n" + "\n".join(
                f"- {s}" for s in strengths[:4])

        gaps_block = ""
        if gaps and recommendation != "Entretien":
            gaps_block = "Points à développer :\n" + "\n".join(
                f"- {g}" for g in gaps[:3])

        # ── Instruction de ton selon la recommandation ────────────────────────
        if recommendation == "Entretien":
            tone = (
                "Email de CONVOCATION À UN ENTRETIEN : chaleureux, enthousiaste. "
                "Annonce clairement l'entretien. "
                "Si un créneau est fourni, l'inclure EXACTEMENT. "
                "Mentionner les points forts spécifiques du candidat. "
                "Inclure le lien Meet si disponible."
            )
        elif recommendation == "ListeAttente":
            tone = (
                "Email de MISE EN VIVIER : positif et valorisant. "
                "Expliquer qu'il n'y a pas de poste disponible actuellement "
                "mais que le profil est retenu. "
                "Mentionner les points forts spécifiques."
            )
        else:  # Refus
            tone = (
                "Email de REFUS BIENVEILLANT : respectueux et encourageant. "
                "Ne pas mentionner le score. "
                "Citer 1-2 points forts spécifiques du candidat pour valoriser. "
                "Encourager à postuler pour d'autres opportunités. "
                "Ne JAMAIS terminer par '[Votre Nom]' ou un placeholder."
            )

        prompt = f"""Contexte :
Candidat : {candidate_name} (prénom : {first})
Poste : {position}
Décision : {recommendation}
Analyse : {summary[:300] if summary else 'Non disponible'}
{strengths_block}
{gaps_block}
{slot_block}
Expéditeur : {_SENDER_NAME}

Instruction : {tone}

Signe l'email avec "Cordialement,\\n{_SENDER_NAME}"
"""
        try:
            from services.llm_client import generate
            raw   = generate(prompt, max_tokens=500, system=_RECRUITMENT_EMAIL_SYSTEM).strip()
            subject, body = self._parse_llm_output(raw, position, recommendation)
            # Vérification anti-placeholder
            body = self._clean_placeholders(body, candidate_name)
            return subject, body
        except Exception as e:
            self._step("observe", f"LLM score email failed : {e} → fallback statique")
            return self._fallback_score_email(
                candidate_name, position, recommendation,
                strengths, gaps, slot_formatted, meet_link, event_link)

    def _fallback_score_email(
        self,
        candidate_name: str,
        position:       str,
        recommendation: str,
        strengths:      list[str],
        gaps:           list[str],
        slot_formatted: str,
        meet_link:      str,
        event_link:     str,
    ) -> tuple[str, str]:
        """Fallback statique propre — utilisé uniquement si le LLM est indisponible."""
        first = candidate_name.split()[0] if candidate_name else "Candidat(e)"

        if recommendation == "Entretien":
            subject = f"Convocation à un entretien — {position}"
            slot_line = ""
            if slot_formatted:
                slot_line = f"\n📅 Créneau : {slot_formatted}"
            meet_line = ""
            if meet_link:
                meet_line = f"\n🎥 Google Meet : {meet_link}"
            elif event_link:
                meet_line = f"\n🔗 Agenda : {event_link}"
            strengths_line = ""
            if strengths:
                strengths_line = "\nNous avons particulièrement apprécié :\n" + \
                    "\n".join(f"  • {s}" for s in strengths[:3])
            body = (
                f"Bonjour {first},\n\n"
                f"Nous avons le plaisir de vous convier à un entretien pour le poste "
                f"de {position}."
                f"{strengths_line}"
                f"{slot_line}{meet_line}\n\n"
                f"Merci de confirmer votre disponibilité en répondant à cet email.\n\n"
                f"Cordialement,\n{_SENDER_NAME}"
            )

        elif recommendation == "ListeAttente":
            subject = f"Votre candidature au poste de {position}"
            strengths_line = ""
            if strengths:
                strengths_line = "\n\nNous avons notamment apprécié :\n" + \
                    "\n".join(f"  • {s}" for s in strengths[:3])
            body = (
                f"Bonjour {first},\n\n"
                f"Nous vous remercions de l'intérêt que vous portez au poste de {position}. "
                f"Votre profil a retenu notre attention."
                f"{strengths_line}\n\n"
                f"Nous n'avons pas de poste disponible actuellement, "
                f"mais nous conservons votre candidature dans notre vivier.\n\n"
                f"Cordialement,\n{_SENDER_NAME}"
            )

        else:  # Refus
            subject = f"Suite de votre candidature — {position}"
            strengths_line = ""
            if strengths:
                strengths_line = "\n\nNous avons apprécié :\n" + \
                    "\n".join(f"  • {s}" for s in strengths[:2])
            body = (
                f"Bonjour {first},\n\n"
                f"Nous vous remercions d'avoir postulé au poste de {position} "
                f"et du temps consacré à votre candidature."
                f"{strengths_line}\n\n"
                f"Après examen attentif, nous ne sommes pas en mesure de donner "
                f"suite à votre dossier à ce stade. "
                f"Nous vous encourageons à surveiller nos futures offres.\n\n"
                f"Cordialement,\n{_SENDER_NAME}"
            )

        return subject, body

    # ─────────────────────────────────────────────────────────────────────────
    # Email convocation entretien (appelé directement par l'orchestrateur)
    # ─────────────────────────────────────────────────────────────────────────

    def send_recruitment_convocation(
        self,
        to:             str,
        candidate_name: str,
        position:       str,
        slot_formatted: str,
        html_link:      str,
        meet_link:      str       = "",
        strengths:      list[str] | None = None,
        sender_name:    str       = "",
    ) -> dict:
        self._reset()
        sender = sender_name or _SENDER_NAME
        self._step("thought", f"Convocation entretien → {to} | {position}")
        if not to or "@" not in to:
            return {"success": False, "error": f"Adresse invalide : '{to}'"}

        subject, body = self._write_convocation_email(
            candidate_name = candidate_name,
            position       = position,
            slot_formatted = slot_formatted,
            html_link      = html_link,
            meet_link      = meet_link,
            strengths      = strengths or [],
            sender_name    = sender,
        )
        self._step("observe", f"Sujet : {subject[:60]}")
        result = self._dispatch(to, subject, body)
        result["body_sent"]    = body
        result["subject_sent"] = subject
        return result

    def _write_convocation_email(
        self,
        candidate_name: str,
        position:       str,
        slot_formatted: str,
        html_link:      str,
        meet_link:      str,
        strengths:      list[str],
        sender_name:    str,
    ) -> tuple[str, str]:
        first = candidate_name.split()[0] if candidate_name else "Candidat(e)"

        meet_info = ""
        if meet_link:
            meet_info = f"Lien Google Meet : {meet_link}"
        elif html_link:
            meet_info = f"Lien Google Calendar : {html_link}"

        strengths_block = ""
        if strengths:
            strengths_block = "Points forts du candidat identifiés par l'IA :\n" + \
                "\n".join(f"- {s}" for s in strengths[:3])
        else:
            strengths_block = "(Points forts non fournis — ne pas évoquer ce sujet)"

        prompt = f"""Contexte :
Candidat : {candidate_name} (prénom : {first})
Poste : {position}
Créneau d'entretien : {slot_formatted}
{meet_info}
{strengths_block}
Expéditeur : {sender_name}

Rédige une convocation à entretien professionnelle et chaleureuse.
RÈGLES :
- Inclure le créneau EXACTEMENT tel quel : "{slot_formatted}"
- Si des points forts sont fournis, les mentionner précisément (pas de formule générique)
- Si "(Points forts non fournis)" est indiqué, NE PAS mentionner les points forts du tout
- Inclure le lien Meet ou Calendar s'il est fourni
- Signer avec "Cordialement,\\n{sender_name}"
- Ne JAMAIS écrire de placeholder entre crochets
"""
        try:
            from services.llm_client import generate
            raw     = generate(prompt, max_tokens=450, system=_RECRUITMENT_EMAIL_SYSTEM).strip()
            subject, body = self._parse_llm_output(raw, position, "Entretien")
            body = self._clean_placeholders(body, candidate_name)
            return subject, body
        except Exception as e:
            self._step("observe", f"LLM convocation failed : {e} → fallback")
            return self._fallback_score_email(
                candidate_name, position, "Entretien",
                strengths, [], slot_formatted, meet_link, html_link)

    # ─────────────────────────────────────────────────────────────────────────
    # Email décision RH post-entretien
    # ─────────────────────────────────────────────────────────────────────────

    def send_decision_email(
        self,
        to:             str,
        candidate_name: str,
        position:       str,
        decision:       str,   # "Accepte" ou "Refuse"
    ) -> dict:
        self._reset()
        self._step("thought", f"Decision email | {decision} → {to} | {position}")
        if not to or "@" not in to:
            return {"success": False, "error": f"Adresse invalide : '{to}'"}

        subject, body = self._write_decision_email(candidate_name, position, decision)
        self._step("observe", f"Sujet : {subject[:60]}")
        result = self._dispatch(to, subject, body)
        result["body_sent"]    = body
        result["subject_sent"] = subject
        return result

    def _write_decision_email(
        self, candidate_name: str, position: str, decision: str
    ) -> tuple[str, str]:
        first = candidate_name.split()[0] if candidate_name else "Candidat(e)"

        if decision == "Accepte":
            tone = (
                "Email de FÉLICITATIONS post-entretien : annoncer que la candidature est retenue, "
                "mentionner que l'équipe RH reprendra contact pour les modalités d'intégration. "
                "Ton enthousiaste et chaleureux."
            )
        else:
            tone = (
                "Email de REFUS post-entretien : bienveillant et respectueux. "
                "Mentionner que l'entretien s'est bien déroulé. "
                "Encourager le candidat. "
                "Ne pas promettre de retour futur précis."
            )

        prompt = f"""Candidat : {candidate_name} (prénom : {first})
Poste : {position}
Décision post-entretien : {decision}
Expéditeur : {_SENDER_NAME}

Instruction : {tone}

Signer avec "Cordialement,\\n{_SENDER_NAME}"
Ne JAMAIS écrire de placeholder entre crochets.
"""
        try:
            from services.llm_client import generate
            raw = generate(prompt, max_tokens=400, system=_RECRUITMENT_EMAIL_SYSTEM).strip()
            subject, body = self._parse_llm_output(
                raw, position,
                "Accepte" if decision == "Accepte" else "Refus"
            )
            body = self._clean_placeholders(body, candidate_name)
            return subject, body
        except Exception as e:
            self._step("observe", f"LLM decision email failed : {e} → fallback")
            return self._fallback_decision_email(candidate_name, position, decision)

    def _fallback_decision_email(
        self, candidate_name: str, position: str, decision: str
    ) -> tuple[str, str]:
        first = candidate_name.split()[0] if candidate_name else "Candidat(e)"
        if decision == "Accepte":
            subject = f"Votre candidature au poste de {position} — Décision favorable 🎉"
            body = (
                f"Bonjour {first},\n\n"
                f"Nous avons le plaisir de vous informer que votre candidature "
                f"au poste de {position} a été retenue à l'issue de votre entretien.\n\n"
                f"Notre équipe RH vous contactera très prochainement pour vous communiquer "
                f"les prochaines étapes et les modalités d'intégration.\n\n"
                f"Bienvenue dans l'équipe !\n\n"
                f"Cordialement,\n{_SENDER_NAME}"
            )
        else:
            subject = f"Suite de votre entretien — {position}"
            body = (
                f"Bonjour {first},\n\n"
                f"Nous vous remercions d'avoir participé à notre processus de recrutement "
                f"pour le poste de {position}.\n\n"
                f"Après délibération, nous avons le regret de vous informer que nous ne "
                f"donnons pas suite à votre candidature. Cela ne remet pas en cause la "
                f"qualité de votre profil.\n\n"
                f"Nous vous souhaitons pleine réussite dans vos recherches.\n\n"
                f"Cordialement,\n{_SENDER_NAME}"
            )
        return subject, body

    # ─────────────────────────────────────────────────────────────────────────
    # Email de refus simple (avant entretien)
    # ─────────────────────────────────────────────────────────────────────────

    def send_simple_refusal_email(
        self,
        to:             str,
        candidate_name: str,
        position:       str,
    ) -> dict:
        """
        Email de refus AVANT entretien.
        Distinct de send_decision_email (post-entretien).
        """
        self._reset()
        self._step("thought", f"Refus simple (avant entretien) → {to} | {position}")
        if not to or "@" not in to:
            return {"success": False, "error": f"Adresse invalide : '{to}'"}

        first = candidate_name.split()[0] if candidate_name else "Candidat(e)"
        try:
            from services.llm_client import generate
            prompt = (
                f"Candidat : {candidate_name} (prénom : {first})\n"
                f"Poste : {position}\n"
                f"Expéditeur : {_SENDER_NAME}\n\n"
                "Rédige un email de refus de candidature AVANT entretien.\n"
                "Ton : bienveillant, respectueux, encourageant. 80 à 120 mots.\n"
                "Ne pas mentionner d'entretien ni de score.\n"
                f"Signer avec 'Cordialement,\\n{_SENDER_NAME}'\n"
                "Ne JAMAIS écrire de placeholder entre crochets.\n"
            )
            raw = generate(prompt, max_tokens=300, system=_RECRUITMENT_EMAIL_SYSTEM).strip()
            subject, body = self._parse_llm_output(raw, position, "Refus")
            body = self._clean_placeholders(body, candidate_name)
        except Exception as e:
            self._step("observe", f"LLM refus simple failed : {e} → fallback")
            subject = f"Suite de votre candidature — {position}"
            body = (
                f"Bonjour {first},\n\n"
                f"Nous avons bien étudié votre candidature au poste de {position} "
                f"et vous remercions de l'intérêt que vous nous portez.\n\n"
                f"Après examen attentif, nous ne sommes pas en mesure de donner suite "
                f"à votre dossier à ce stade. Nous vous encourageons à surveiller "
                f"nos prochaines offres.\n\n"
                f"Cordialement,\n{_SENDER_NAME}"
            )

        self._step("observe", f"Sujet : {subject[:60]}")
        result = self._dispatch(to, subject, body)
        result["body_sent"]    = body
        result["subject_sent"] = subject
        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Email onboarding
    # ─────────────────────────────────────────────────────────────────────────

    def send_onboarding_email(
        self,
        to:             str,
        candidate_name: str,
        position:       str,
        start_date_str: str       = "",
        checklist:      list[str] | None = None,
        reminder_link:  str       = "",
        sender_name:    str       = "",
    ) -> dict:
        self._reset()
        sender = sender_name or _SENDER_NAME
        self._step("thought", f"Onboarding email → {to} | {position} | {start_date_str}")
        if not to or "@" not in to:
            return {"success": False, "error": f"Adresse invalide : '{to}'"}

        subject, body = self._build_onboarding_content(
            candidate_name = candidate_name,
            position       = position,
            start_date_str = start_date_str,
            checklist      = checklist or [],
            reminder_link  = reminder_link,
            sender_name    = sender,
        )
        self._step("observe", f"Sujet : {subject[:60]}")
        result = self._dispatch(to, subject, body)
        result["body_sent"]    = body
        result["subject_sent"] = subject
        return result

    def _build_onboarding_content(
        self, candidate_name, position, start_date_str,
        checklist, reminder_link, sender_name,
    ) -> tuple[str, str]:
        first = candidate_name.split()[0] if candidate_name else "Candidat(e)"
        subject = f"Bienvenue — Votre intégration au poste de {position} 🎉"
        if start_date_str:
            try:
                from datetime import datetime
                dt    = datetime.fromisoformat(start_date_str)
                JOURS = ["lundi","mardi","mercredi","jeudi","vendredi","samedi","dimanche"]
                MOIS  = ["","janvier","février","mars","avril","mai","juin",
                          "juillet","août","septembre","octobre","novembre","décembre"]
                date_line = (f"\n📅 Prise de poste : {JOURS[dt.weekday()]} {dt.day} "
                             f"{MOIS[dt.month]} {dt.year}\n")
            except Exception:
                date_line = f"\n📅 Prise de poste : {start_date_str}\n"
        else:
            date_line = "\n📅 Notre équipe RH vous communiquera votre date de prise de poste.\n"

        if checklist:
            checklist_block = (
                "\n📋 Documents à nous transmettre avant votre arrivée :\n"
                + "\n".join(f"  ☐ {item}" for item in checklist)
                + "\n"
            )
        else:
            checklist_block = "\n📋 Notre équipe RH vous communiquera la liste des documents à fournir.\n"

        reminder_line = (
            f"\n🔔 Rappel agenda : {reminder_link}\n" if reminder_link else ""
        )
        body = (
            f"Bonjour {first},\n\n"
            f"Nous avons le plaisir de confirmer votre intégration en tant que {position}. "
            f"Toute l'équipe se réjouit de vous accueillir !\n"
            f"{date_line}"
            f"{checklist_block}"
            f"{reminder_line}\n"
            f"N'hésitez pas à nous contacter pour toute question.\n\n"
            f"Cordialement,\n{sender_name}"
        )
        return subject, body

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers communs
    # ─────────────────────────────────────────────────────────────────────────

    def _parse_llm_output(
        self, raw: str, position: str, recommendation: str
    ) -> tuple[str, str]:
        """
        Parse la sortie LLM au format SUJET:/CORPS:.
        Retourne (subject, body) avec des valeurs sûres si le parsing échoue.
        """
        lines = raw.split("\n")
        subject = None
        body    = None

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.upper().startswith("SUJET:") and subject is None:
                subject = stripped.split(":", 1)[-1].strip()
            elif stripped.upper().startswith("CORPS:") and body is None:
                # Le corps commence à la ligne suivante
                rest = "\n".join(lines[i + 1:]).strip()
                if rest:
                    body = rest
                else:
                    # Corps sur la même ligne
                    body = stripped.split(":", 1)[-1].strip() or raw

        # Fallback sujet
        if not subject:
            if recommendation == "Entretien":
                subject = f"Convocation à un entretien — {position}"
            elif recommendation == "ListeAttente":
                subject = f"Votre candidature — {position}"
            else:
                subject = f"Suite de votre candidature — {position}"

        # Fallback corps (si le LLM n'a pas mis CORPS:, on prend tout le raw)
        if not body:
            # Chercher si le raw contient directement le texte (sans marqueurs)
            body = raw.strip()

        return subject, body

    def _clean_placeholders(self, body: str, candidate_name: str = "") -> str:
        """
        Supprime ou remplace les placeholders entre crochets que le LLM
        pourrait générer malgré les instructions.
        """
        import re
        # Remplacer [Votre Nom], [Signature], [Nom], [Your Name], etc.
        body = re.sub(
            r'\[(?:Votre\s+Nom|Signature|Nom|Your\s+Name|NOM|nom)\]',
            _SENDER_NAME,
            body, flags=re.IGNORECASE
        )
        # Remplacer [Date], [Lien], [URL] par chaîne vide
        body = re.sub(
            r'\[(?:Date|Lien|URL|Link|Créneau|Creneau)\]',
            '',
            body, flags=re.IGNORECASE
        )
        # Remplacer tout placeholder générique restant [...]
        body = re.sub(r'\[[^\]]{1,40}\]', '', body)
        # Nettoyer doubles espaces/lignes résultants
        body = re.sub(r'\n{3,}', '\n\n', body)
        return body.strip()

    # ─────────────────────────────────────────────────────────────────────────
    # Dispatcher commun (Gmail MCP → Gmail natif → SMTP)
    # ─────────────────────────────────────────────────────────────────────────

    def _dispatch(self, to: str, subject: str, body: str) -> dict:
        result = self._send_via_gmail_mcp(to, subject, body)
        if result.get("success"):
            return {**result, "subject_used": subject, "body_sent": body,
                    "processing_ms": self._elapsed_ms()}

        self._step("observe", f"Gmail MCP failed : {result.get('error')} → Gmail natif")

        if self._is_gmail_native_available():
            ok, info = self._send_gmail_native(to=to, subject=subject, body=body)
            if ok:
                return {"success": True, "email_to": to, "subject_used": subject,
                        "body_sent": body,
                        "processing_ms": self._elapsed_ms()}
            self._step("observe", f"Gmail natif failed : {info} → SMTP")

        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pass = os.getenv("SMTP_PASSWORD", "") or os.getenv("SMTP_PASS", "")
        if smtp_user and smtp_pass:
            return self._send_smtp(to, subject, body, "", "")

        return {"success": False, "error": "Aucune méthode d'envoi disponible.",
                "processing_ms": self._elapsed_ms()}

    # ─────────────────────────────────────────────────────────────────────────
    # Gmail MCP subprocess
    # ─────────────────────────────────────────────────────────────────────────

    def _send_via_gmail_mcp(self, to: str, subject: str, body: str) -> dict:
        self._step("action", f"Gmail MCP subprocess → {to}")
        try:
            from mcp_client import call_mcp_tool
            import re
            raw = call_mcp_tool(
                MCP_SPECS["gmail"], "send_email",
                {"to": [to] if isinstance(to, str) else to,
                 "subject": subject, "body": body, "mimeType": "text/plain"},
            )
            self._step("observe", f"Gmail MCP raw : {str(raw)[:120]}")
            try:
                data = json.loads(raw) if isinstance(raw, str) and raw.strip() else {}
            except json.JSONDecodeError:
                data = {}
            raw_lower = (raw or "").lower()
            if (data.get("success") or data.get("messageId") or data.get("id")
                    or "sent successfully" in raw_lower
                    or ("id:" in raw_lower and "error" not in raw_lower)):
                msg_id = (data.get("messageId") or data.get("id") or
                          (re.search(r'ID:\s*(\S+)', raw or '', re.IGNORECASE) or [None, ""])[1])
                self._step("observe", f"Gmail MCP OK → {to} | id={msg_id}")
                return {"success": True, "email_to": to, "message_id": msg_id,
                        "method": "gmail_mcp_subprocess"}
            error = data.get("error", data.get("message", str(data)[:80]))
            return {"success": False, "error": error}
        except Exception as e:
            self._step("observe", f"Gmail MCP exception : {e}")
            return {"success": False, "error": str(e)}

    # ─────────────────────────────────────────────────────────────────────────
    # Gmail natif
    # ─────────────────────────────────────────────────────────────────────────

    def _is_gmail_native_available(self) -> bool:
        try:
            from core.constants import get_google_credentials
            creds = get_google_credentials()
            return creds is not None and creds.valid
        except Exception:
            return False

    def _send_gmail_native(
        self, to, subject, body,
        attachment_bytes=None, attachment_filename=None,
    ) -> tuple[bool, str]:
        try:
            import base64
            from googleapiclient.discovery import build
            from core.constants import get_google_credentials
            creds = get_google_credentials()
            if not creds:
                return False, "token.json absent"
            service = build("gmail", "v1", credentials=creds)
            msg = MIMEMultipart()
            msg["To"]      = to
            msg["Subject"] = subject
            sender = os.getenv("GMAIL_USER", "")
            if sender:
                msg["From"] = sender
            msg.attach(MIMEText(body, "plain", "utf-8"))
            if attachment_bytes and attachment_filename:
                part = MIMEApplication(attachment_bytes, Name=attachment_filename)
                part["Content-Disposition"] = f'attachment; filename="{attachment_filename}"'
                msg.attach(part)
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            service.users().messages().send(userId="me", body={"raw": raw}).execute()
            self._step("observe", f"Gmail natif OK → {to}")
            return True, to
        except ImportError:
            return False, "google-api-python-client non installé"
        except Exception as e:
            return False, str(e)

    # ─────────────────────────────────────────────────────────────────────────
    # Rédaction LLM (email générique GED)
    # ─────────────────────────────────────────────────────────────────────────

    def _write_email(self, filename, document_type, summary, extraction) -> tuple[str, str]:
        from services.llm_client import generate
        content = summary[:400] or extraction[:400]
        try:
            raw   = generate(
                f"Document : {filename} (type : {document_type})\n"
                f"Contenu :\n{content}\n\nRédige un email professionnel :",
                max_tokens=350, system=self.SYSTEM_PROMPT,
            )
            lines   = raw.strip().split("\n")
            subject = f"[GED] Rapport — {filename}"
            body    = raw
            for i, line in enumerate(lines):
                if line.upper().startswith("SUJET:"):
                    subject = line.split(":", 1)[-1].strip()
                elif line.upper().startswith("CORPS:"):
                    body = "\n".join(lines[i:]).split(":", 1)[-1].strip()
                    break
            return subject, body
        except Exception as e:
            self._step("observe", f"Rédaction LLM failed : {e}")
            return f"[GED] Rapport — {filename}", content

    # ─────────────────────────────────────────────────────────────────────────
    # SMTP — fallback final
    # ─────────────────────────────────────────────────────────────────────────

    def _send_smtp(self, to, subject, body, pdf_base64, filename) -> dict:
        self._step("action", f"SMTP → {to}")
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pass = os.getenv("SMTP_PASSWORD", "") or os.getenv("SMTP_PASS", "")
        if not smtp_user:
            return {"success": False, "error": "SMTP_USER manquant",
                    "processing_ms": self._elapsed_ms()}
        if not smtp_pass:
            return {"success": False, "error": "SMTP_PASSWORD manquant",
                    "processing_ms": self._elapsed_ms()}
        try:
            msg = MIMEMultipart()
            msg["From"]    = smtp_user
            msg["To"]      = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))
            if pdf_base64 and filename:
                from email.mime.base import MIMEBase
                from email import encoders
                part = MIMEBase("application", "octet-stream")
                part.set_payload(_b64.b64decode(pdf_base64))
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
                msg.attach(part)
            with smtplib.SMTP(smtp_host, smtp_port) as s:
                s.starttls()
                s.login(smtp_user, smtp_pass)
                s.sendmail(smtp_user, to, msg.as_string())
            self._step("observe", f"SMTP OK → {to}")
            return {"success": True, "email_to": to, "subject_used": subject,
                    "body_sent": body,
                    "has_attachment": bool(pdf_base64 and filename),
                    "processing_ms": self._elapsed_ms()}
        except smtplib.SMTPAuthenticationError:
            return {"success": False,
                    "error": "Auth SMTP échouée — utilise un App Password Gmail",
                    "processing_ms": self._elapsed_ms()}
        except Exception as e:
            return {"success": False, "error": str(e), "processing_ms": self._elapsed_ms()}