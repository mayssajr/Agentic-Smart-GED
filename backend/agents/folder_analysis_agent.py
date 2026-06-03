import json
import os
import shutil
from datetime import datetime, timezone
from typing import Optional

from agents.base_agent import BaseAgent, BASE_DIR

# ── Extensions de fichiers traités ───────────────────────────────────────────
# PDF, DOCX, TXT — OCR non inclus ici (déléguer à OCRAgent si nécessaire)
_SUPPORTED_EXTS = {".pdf", ".docx", ".doc", ".txt", ".md"}

# Nombre maximum de fichiers à traiter en une seule passe (évite les timeouts LLM)
_MAX_FILES = 20

# Taille maximale du contenu lu par fichier (chars) avant troncature
_MAX_CONTENT_CHARS = 6000

# ── Spec serveur filesystem MCP officiel ─────────────────────────────────────
# Le serveur reçoit le dossier racine DOCS_DIR comme seul répertoire autorisé.
# Il refuse tout accès hors de ce dossier.
_DOCS_DIR = os.path.abspath(
    os.getenv("DOCS_DIR", os.getenv("GED_DATA_DIR", "./data"))
)

_FS_SPEC = {
    "command": "npx",
    "args":    ["-y", "@modelcontextprotocol/server-filesystem", _DOCS_DIR],
    "env":     {},
}


def _npx_available() -> bool:
    """Vérifie que npx est disponible sur le système."""
    return shutil.which("npx") is not None


class FolderAnalysisAgent(BaseAgent):
    """
    Agent d'analyse autonome de dossier.

    Contrairement aux autres agents qui reçoivent un texte déjà extrait,
    cet agent part d'un nom de dossier et fait TOUT lui-même :
    lister, lire, résumer, écrire le rapport.

    C'est le patron "agentic loop" pur : l'agent décide seul
    de combien de fichiers traiter, dans quel ordre, et quoi écrire.
    """
    NAME = "FolderAnalysisAgent"

    # SYSTEM_PROMPT : utilisé pour le résumé consolidé final (LLM direct)
    SYSTEM_PROMPT = (
        "Tu es un agent expert en analyse documentaire pour la GED NeoLedge Elise. "
        "Tu analyses des collections de documents professionnels et produis des rapports "
        "synthétiques, structurés et actionnables. "
        "Tu identifies les patterns communs, les dates importantes, les parties impliquées "
        "et les points d'attention dans chaque collection. "
        "Tu rédiges en français professionnel."
    )

    TOOL_SERVERS = []   # Pas de serveur MCP custom — on utilise le filesystem officiel

    def run(
        self,
        folder_path:  str,
        objective:    str            = "Résume tous les documents de ce dossier",
        file_filter:  Optional[str]  = None,   # ex: ".pdf", ".txt" — None = tous
        output_file:  Optional[str]  = None,   # nom du rapport (ex: "rapport_contrats.md")
        **_,
    ) -> dict:
        """
        Analyse autonome d'un dossier via filesystem MCP.

        folder_path : chemin relatif au DOCS_DIR (ex: "contrats", "factures/2026")
        objective   : ce que l'utilisateur veut (ex: "résume tous les PDFs")
        file_filter : extension à filtrer (ex: ".pdf") — None = tous les formats
        output_file : nom du fichier rapport à écrire (None = auto-généré)

        Retourne :
          folder_path    — dossier analysé
          files_found    — nombre de fichiers trouvés
          files_processed— nombre de fichiers traités
          summaries      — liste des résumés individuels
          consolidated   — rapport consolidé final
          report_path    — chemin du rapport écrit (relatif à DOCS_DIR)
          processing_ms  — durée totale
          react_trace    — trace ReAct complète
        """
        self._reset()

        # ── Vérification prérequis ────────────────────────────────────────────
        if not _npx_available():
            self._step("observe",
                "✗ npx absent — impossible d'utiliser le filesystem MCP. "
                "Installer Node.js 18+ depuis https://nodejs.org")
            return self._error_result(
                "npx non disponible. Installez Node.js 18+.",
            )

        # Construire le chemin absolu du dossier cible
        target_dir = os.path.join(_DOCS_DIR, folder_path.lstrip("/\\"))
        target_dir = os.path.normpath(target_dir)

        # ── THOUGHT : planification ───────────────────────────────────────────
        self._step("thought",
            f"Analyse du dossier '{folder_path}' | "
            f"Objectif : '{objective[:80]}' | "
            f"Filtre : {file_filter or 'tous les formats'} | "
            f"DOCS_DIR : {_DOCS_DIR}")

        # ── ACTION 1 : list_directory — lister les fichiers ───────────────────
        # filesystem MCP outil : list_directory(path) → liste des entrées
        self._step("action",
            f"filesystem.list_directory('{target_dir}')")
        all_entries = []
        try:
            raw = self._call_tool(_FS_SPEC, "list_directory", {
                "path": target_dir,
            })
            # Le serveur retourne une liste formatée type :
            # "[FILE] contrat_001.pdf\n[FILE] contrat_002.pdf\n[DIR] archives"
            all_entries = self._parse_directory_listing(raw)
            self._step("observe",
                f"list_directory OK : {len(all_entries)} entrée(s) | "
                f"Fichiers : {sum(1 for e in all_entries if e['type'] == 'file')} | "
                f"Sous-dossiers : {sum(1 for e in all_entries if e['type'] == 'dir')}")
        except Exception as exc:
            self._step("observe", f"✗ list_directory failed : {exc}")
            return self._error_result(
                f"Impossible de lire le dossier '{folder_path}' : {exc}. "
                f"Vérifiez que le dossier existe dans DOCS_DIR={_DOCS_DIR}"
            )

        # Filtrer les fichiers éligibles
        eligible_files = [
            e for e in all_entries
            if e["type"] == "file"
            and self._is_eligible(e["name"], file_filter)
        ]

        if not eligible_files:
            ext_msg = f" avec l'extension '{file_filter}'" if file_filter else ""
            self._step("observe",
                f"Aucun fichier éligible{ext_msg} dans '{folder_path}'. "
                f"Formats supportés : {', '.join(_SUPPORTED_EXTS)}")
            return self._error_result(
                f"Aucun fichier{ext_msg} trouvé dans '{folder_path}'."
            )

        # Limiter le nombre de fichiers traités
        if len(eligible_files) > _MAX_FILES:
            self._step("observe",
                f"⚠ {len(eligible_files)} fichiers trouvés — limité à {_MAX_FILES} "
                f"pour éviter un timeout LLM. Utiliser file_filter pour restreindre.")
            eligible_files = eligible_files[:_MAX_FILES]

        self._step("observe",
            f"{len(eligible_files)} fichier(s) à traiter : "
            f"{', '.join(e['name'] for e in eligible_files[:5])}"
            + (f" (+ {len(eligible_files)-5} autres)" if len(eligible_files) > 5 else ""))

        # ── ACTION 2+3 : read_file + résumé pour chaque fichier ───────────────
        # Boucle agentic : l'agent lit chaque fichier et le résume individuellement
        summaries = []
        errors    = []

        for i, entry in enumerate(eligible_files, 1):
            file_path = os.path.join(target_dir, entry["name"])

            # filesystem MCP outil : read_file(path) → contenu texte brut
            self._step("action",
                f"[{i}/{len(eligible_files)}] filesystem.read_file('{entry['name']}')")
            try:
                content = self._call_tool(_FS_SPEC, "read_file", {
                    "path": file_path,
                })
                # Tronquer si trop long
                if len(content) > _MAX_CONTENT_CHARS:
                    content = content[:_MAX_CONTENT_CHARS] + "\n[... contenu tronqué]"
                    self._step("observe",
                        f"  Contenu tronqué à {_MAX_CONTENT_CHARS} chars.")
                else:
                    self._step("observe",
                        f"  read_file OK : {len(content)} chars.")

            except Exception as exc:
                self._step("observe", f"  ✗ read_file failed : {exc}")
                errors.append({"file": entry["name"], "error": str(exc)})
                continue

            # ACTION 3 : résumé individuel via LLM (appel direct, pas via MCP)
            # SYSTEM_PROMPT de l'agent injecté ici
            self._step("action",
                f"  LLM résumé individuel → '{entry['name']}'")
            try:
                from services.llm_client import summarize
                # Détecter le type par extension
                ext = os.path.splitext(entry["name"])[1].lower()
                doc_type = self._guess_doc_type(entry["name"], content)
                summary_text = summarize(
                    content,
                    doc_type,
                    system=self.SYSTEM_PROMPT,
                )
                summaries.append({
                    "file":     entry["name"],
                    "doc_type": doc_type,
                    "summary":  summary_text,
                    "chars":    len(content),
                })
                self._step("observe",
                    f"  Résumé OK : {len(summary_text)} chars | type={doc_type}")
            except Exception as exc:
                self._step("observe", f"  ✗ LLM résumé failed : {exc}")
                summaries.append({
                    "file":     entry["name"],
                    "doc_type": "Autre",
                    "summary":  f"Résumé non disponible : {exc}",
                    "chars":    len(content) if content else 0,
                })

        # ── ACTION 4 : consolidation LLM ─────────────────────────────────────
        # Résumé consolidé de tous les fichiers du dossier
        self._step("action",
            f"LLM consolidation → rapport final ({len(summaries)} résumés)")
        consolidated = ""
        try:
            all_summaries_text = "\n\n".join(
                f"### {s['file']} ({s['doc_type']})\n{s['summary']}"
                for s in summaries
            )
            consolidation_prompt = (
                f"Objectif de l'utilisateur : {objective}\n\n"
                f"Dossier analysé : {folder_path}\n"
                f"Nombre de documents : {len(summaries)}\n\n"
                f"Résumés individuels :\n{all_summaries_text}\n\n"
                "Produis un rapport consolidé en 3 sections :\n"
                "1. SYNTHÈSE GLOBALE (2-3 phrases sur l'ensemble du dossier)\n"
                "2. POINTS CLÉS (liste des éléments importants communs ou notables)\n"
                "3. ACTIONS RECOMMANDÉES (si applicable : signatures manquantes, "
                "   échéances proches, anomalies)\n"
                "Rédige en français professionnel."
            )
            from services.llm_client import generate
            consolidated = generate(
                consolidation_prompt,
                max_tokens=600,
                system=self.SYSTEM_PROMPT,
            )
            self._step("observe",
                f"Consolidation OK : {len(consolidated)} chars.")
        except Exception as exc:
            consolidated = f"Rapport consolidé non disponible : {exc}"
            self._step("observe", f"✗ Consolidation LLM failed : {exc}")

        # ── ACTION 5 : write_file — écrire le rapport final ───────────────────
        # filesystem MCP outil : write_file(path, content) → écrit le fichier
        now        = datetime.now(timezone.utc)
        report_name = output_file or (
            f"rapport_{folder_path.replace('/', '_').replace(os.sep, '_')}"
            f"_{now.strftime('%Y%m%d_%H%M')}.md"
        )
        report_path = os.path.join(_DOCS_DIR, report_name)
        report_content = self._build_report_md(
            folder_path   = folder_path,
            objective     = objective,
            summaries     = summaries,
            consolidated  = consolidated,
            errors        = errors,
            generated_at  = now.isoformat(),
        )

        self._step("action",
            f"filesystem.write_file('{report_name}')")
        report_written = False
        try:
            self._call_tool(_FS_SPEC, "write_file", {
                "path":    report_path,
                "content": report_content,
            })
            report_written = True
            self._step("observe",
                f"✓ Rapport écrit : '{report_name}' ({len(report_content)} chars)")
        except Exception as exc:
            self._step("observe",
                f"✗ write_file failed : {exc} — rapport disponible en mémoire seulement")

        # ── ANSWER ────────────────────────────────────────────────────────────
        ms = self._elapsed_ms()
        self._step("answer",
            f"Analyse terminée : {len(summaries)}/{len(eligible_files)} fichiers "
            f"traités en {ms}ms. "
            f"Rapport : {'✓ ' + report_name if report_written else '✗ non écrit'}.")

        return {
            "folder_path":     folder_path,
            "docs_dir":        _DOCS_DIR,
            "files_found":     len(eligible_files),
            "files_processed": len(summaries),
            "files_errors":    len(errors),
            "summaries":       summaries,
            "consolidated":    consolidated,
            "report_path":     report_name if report_written else None,
            "report_written":  report_written,
            "errors":          errors,
            "processing_ms":   ms,
            "react_trace":     self.trace,
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _parse_directory_listing(self, raw: str) -> list:
        """
        Parse la sortie de list_directory du serveur filesystem officiel.

        Formats possibles retournés par le serveur :
          "[FILE] nom_fichier.pdf"
          "[DIR]  sous_dossier"
        ou format JSON selon la version du serveur.
        """
        entries = []
        if not raw or not raw.strip():
            return entries

        # Tentative format JSON (versions récentes du serveur)
        if raw.strip().startswith("[") or raw.strip().startswith("{"):
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            entries.append({
                                "name": item.get("name", ""),
                                "type": "dir" if item.get("isDirectory") else "file",
                            })
                        elif isinstance(item, str):
                            entries.append({"name": item, "type": "file"})
                return entries
            except json.JSONDecodeError:
                pass

        # Format texte : "[FILE] nom" ou "[DIR] nom"
        for line in raw.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("[FILE]") or line.startswith("[file]"):
                name = line.replace("[FILE]", "").replace("[file]", "").strip()
                if name:
                    entries.append({"name": name, "type": "file"})
            elif line.startswith("[DIR]") or line.startswith("[dir]"):
                name = line.replace("[DIR]", "").replace("[dir]", "").strip()
                if name:
                    entries.append({"name": name, "type": "dir"})
            else:
                # Format sans préfixe — supposer fichier
                entries.append({"name": line, "type": "file"})

        return entries

    def _is_eligible(self, filename: str, file_filter: Optional[str]) -> bool:
        """
        Vérifie si un fichier doit être traité.

        file_filter : extension spécifique (ex: ".pdf") ou None = tous
        """
        ext = os.path.splitext(filename)[1].lower()
        if file_filter:
            return ext == file_filter.lower()
        return ext in _SUPPORTED_EXTS

    def _guess_doc_type(self, filename: str, content: str) -> str:
        """
        Devine le type de document pour orienter le résumé LLM.
        Basé sur le nom de fichier et les mots-clés du contenu.
        """
        name_lower    = filename.lower()
        content_lower = content.lower()

        if any(k in name_lower for k in ["contrat", "cdi", "cdd", "avenant", "convention"]):
            return "RH"
        if any(k in name_lower for k in ["facture", "devis", "commande", "bon"]):
            return "Juridique"
        if any(k in name_lower for k in ["spec", "cahier", "api", "architecture"]):
            return "Technique"
        if any(k in content_lower for k in ["salarié", "employeur", "salaire", "période d'essai"]):
            return "RH"
        if any(k in content_lower for k in ["tribunal", "clause", "résiliation", "partie"]):
            return "Juridique"
        if any(k in content_lower for k in ["api", "serveur", "architecture", "déploiement"]):
            return "Technique"
        return "Autre"

    def _build_report_md(
        self,
        folder_path:  str,
        objective:    str,
        summaries:    list,
        consolidated: str,
        errors:       list,
        generated_at: str,
    ) -> str:
        """Construit le contenu Markdown du rapport final."""
        lines = [
            f"# Rapport d'analyse — {folder_path}",
            f"",
            f"**Généré le** : {generated_at[:19].replace('T', ' ')} UTC  ",
            f"**Objectif** : {objective}  ",
            f"**Fichiers traités** : {len(summaries)}  ",
            f"",
            f"---",
            f"",
            f"## Synthèse consolidée",
            f"",
            consolidated,
            f"",
            f"---",
            f"",
            f"## Résumés individuels",
            f"",
        ]
        for i, s in enumerate(summaries, 1):
            lines += [
                f"### {i}. {s['file']}",
                f"*Type : {s['doc_type']} · {s['chars']:,} caractères*",
                f"",
                s["summary"],
                f"",
            ]

        if errors:
            lines += [
                f"---",
                f"",
                f"## Fichiers non traités ({len(errors)})",
                f"",
            ]
            for e in errors:
                lines.append(f"- `{e['file']}` : {e['error']}")
            lines.append("")

        lines += [
            f"---",
            f"*Rapport généré par FolderAnalysisAgent — NeoLedge Elise*",
        ]
        return "\n".join(lines)

    def _error_result(self, message: str) -> dict:
        """Retourne un résultat d'erreur standardisé."""
        return {
            "folder_path":     "",
            "docs_dir":        _DOCS_DIR,
            "files_found":     0,
            "files_processed": 0,
            "files_errors":    0,
            "summaries":       [],
            "consolidated":    "",
            "report_path":     None,
            "report_written":  False,
            "errors":          [{"file": "", "error": message}],
            "processing_ms":   self._elapsed_ms(),
            "react_trace":     self.trace,
        }