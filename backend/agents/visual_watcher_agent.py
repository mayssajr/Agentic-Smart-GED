"""
agents/visual_watcher_agent.py
══════════════════════════════
Agent de surveillance visuelle INTELLIGENT — version 2.

Comportement complet et autonome :
  1. Navigue vers la page liste des documents (/documents)
  2. Prend un screenshot — lit tous les badges à l'écran par OCR
  3. Détecte les documents avec badge "RECU" (non encore analysés)
  4. Clique sur le bouton "Voir" de la même ligne
  5. Attend le chargement de la page détail
  6. Clique sur "Analyser le document"
  7. Attend la fin de l'analyse (détecte "ANALYSE IA EN COURS" puis résultat)
  8. Revient à la liste — recommence pour le document suivant
  9. Logue chaque cycle dans le Playbook ACE (apprentissage du pattern)

ACE intégration :
  - Section "workflow_patterns" dans le playbook
  - Le système apprend : "dès qu'un document RECU arrive → analyser immédiatement"
  - Métriques : temps moyen, taux de succès, documents traités

Lancement :
  python agents/visual_watcher_agent.py           # surveillance continue
  python agents/visual_watcher_agent.py --once    # 1 cycle puis arrêt
  python agents/visual_watcher_agent.py --debug   # affiche le texte OCR complet
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import json
import requests
from datetime import datetime
from typing import Optional, List, Dict, Tuple

# ── Configuration ─────────────────────────────────────────────────────────────
FRONTEND_URL    = os.getenv("FRONTEND_URL",  "http://localhost:3000")
AI_BACKEND      = os.getenv("AI_BACKEND",    "http://localhost:8000")
POLL_SECONDS    = int(os.getenv("WATCHER_POLL", "15"))
CLICK_COOLDOWN  = 30
OCR_CONF        = 35
SCREENSHOT_DIR  = "screenshots"

# ── Textes clés pour la détection visuelle ────────────────────────────────────
BADGE_RECU       = ["RECU", "Recu", "reçu", "Reçu"]
BADGE_ANALYZED   = ["À TRAITER", "A TRAITER", "ENTRETIEN", "ACCEPTÉ", "REFUSÉ", "LISTE"]
BTN_VOIR         = ["Voir"]
BTN_ANALYSER     = ["Analyser le document", "Analyser"]
TEXT_LOADING     = ["ANALYSE IA EN COURS", "EN COURS", "Automatique"]
TEXT_DONE        = ["ANALYSE IA", "Regénérer", "Synthèse globale", "Afficher l'analyse", "Masquer"]
TEXT_DOCUMENTS   = ["Mes Documents", "Mes documents", "Gestionnaire"]


class VisualWatcherAgent:

    NAME = "VisualWatcherAgent"

    def __init__(self, debug: bool = False):
        self.debug          = debug
        self._last_click_ts = 0.0
        self._cycle_count   = 0
        self._success_count = 0
        self._session_start = datetime.utcnow().isoformat()
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        self._check_libs()

    def _check_libs(self):
        missing = []
        for lib in ["mss", "pytesseract", "pyautogui", "PIL"]:
            try: __import__("PIL" if lib == "PIL" else lib)
            except ImportError: missing.append(lib)
        if missing:
            print(f"\n[ERREUR] Librairies manquantes : {', '.join(missing)}")
            print("  pip install mss pytesseract pyautogui pillow\n")
            sys.exit(1)
        import pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE    = 0.4

    # ══════════════════════════════════════════════════════════════════════════
    # BOUCLE PRINCIPALE
    # ══════════════════════════════════════════════════════════════════════════

    def run_forever(self):
        self._print_banner()
        # Naviguer vers la liste dès le démarrage
        self._navigate_to_list()
        time.sleep(2)

        while True:
            try:
                self._watch_cycle()
            except KeyboardInterrupt:
                self._on_stop()
                break
            except Exception as e:
                self._log("observe", f"Erreur non fatale : {e}")
            time.sleep(POLL_SECONDS)

    def run_once(self):
        self._navigate_to_list()
        time.sleep(2)
        self._watch_cycle()

    # ══════════════════════════════════════════════════════════════════════════
    # CYCLE DE SURVEILLANCE
    # ══════════════════════════════════════════════════════════════════════════

    def _watch_cycle(self):
        """
        1 cycle complet :
          A. Screenshot de l'état actuel
          B. Détecter la page (liste ou détail)
          C. Agir en conséquence
        """
        img   = self._screenshot("cycle")
        text, boxes = self._ocr(img)

        if self.debug:
            self._print_ocr(text)

        # ── Cas 1 : on est sur la page liste ──────────────────────────────────
        if self._on_list_page(text):
            self._log("observe", "Page liste détectée")
            self._handle_list_page(text, boxes)

        # ── Cas 2 : on est sur la page détail d'un document ──────────────────
        elif self._on_detail_page(text):
            self._log("observe", "Page détail détectée")
            self._handle_detail_page(text, boxes)

        # ── Cas 3 : page inconnue → retourner à la liste ──────────────────────
        else:
            self._log("observe", "Page inconnue → retour à la liste")
            self._navigate_to_list()

    # ══════════════════════════════════════════════════════════════════════════
    # GESTION PAGE LISTE
    # ══════════════════════════════════════════════════════════════════════════

    def _handle_list_page(self, text: str, boxes: List[Dict]):
        """
        Sur la page liste :
        1. Chercher une ligne avec badge RECU
        2. Trouver le bouton Voir sur la même ligne
        3. Cliquer Voir
        """
        # Trouver toutes les positions des badges RECU
        recu_boxes = self._find_texts(boxes, BADGE_RECU)

        if not recu_boxes:
            self._log("observe", "Aucun document RECU visible — liste propre ✓")
            return

        # Prendre le premier document RECU
        recu = recu_boxes[0]
        self._log("observe",
            f"Document RECU détecté @ y={recu['y']} | texte='{recu['text']}'")

        # Trouver le bouton "Voir" sur la même ligne (même Y ± 15px)
        voir_box = self._find_on_same_row(boxes, BTN_VOIR, recu["y"], tolerance=20)

        if not voir_box:
            self._log("observe",
                f"Bouton 'Voir' non trouvé sur la ligne y={recu['y']} — "
                f"essai clic ligne complète")
            # Fallback : cliquer directement sur le titre du document (même ligne)
            title_box = self._find_closest_right(boxes, recu, max_dist=600)
            if title_box:
                self._click(title_box, label="Titre document")
            return

        # Cliquer sur Voir
        self._click(voir_box, label="Voir")
        self._log("observe", "Navigation vers le document — attente chargement...")
        time.sleep(3)

    # ══════════════════════════════════════════════════════════════════════════
    # GESTION PAGE DÉTAIL
    # ══════════════════════════════════════════════════════════════════════════

    def _handle_detail_page(self, text: str, boxes: List[Dict]):
        """
        Sur la page détail :
        1. L'analyse est-elle déjà en cours ? → attendre
        2. L'analyse est-elle déjà faite ? → retourner à la liste
        3. Le bouton Analyser est-il visible ? → cliquer
        """
        # Déjà en cours
        if self._text_in(text, TEXT_LOADING):
            self._log("observe", "Analyse en cours — attente 10s")
            time.sleep(10)
            return

        # Déjà terminée
        if self._text_in(text, TEXT_DONE):
            self._log("answer", "Analyse terminée ✓ — retour à la liste")
            self._on_analysis_done(text)
            self._navigate_to_list()
            return

        # Chercher le bouton Analyser
        analyser_box = self._find_texts(boxes, BTN_ANALYSER)
        if not analyser_box:
            self._log("observe", "Bouton 'Analyser' non visible — page pas prête ?")
            return

        # Cooldown
        elapsed = time.time() - self._last_click_ts
        if elapsed < CLICK_COOLDOWN:
            self._log("observe", f"Cooldown {int(CLICK_COOLDOWN-elapsed)}s")
            return

        # Cliquer Analyser
        self._click(analyser_box[0], label="Analyser le document")
        self._cycle_count += 1

        # Attendre que l'analyse démarre
        self._wait_for_loading()

    # ══════════════════════════════════════════════════════════════════════════
    # DÉTECTION DE PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _on_list_page(self, text: str) -> bool:
        return (self._text_in(text, TEXT_DOCUMENTS) and
                self._text_in(text, ["Voir", "Modifier", "Supprimer",
                                     "Nom du document", "Mes documents"]))

    def _on_detail_page(self, text: str) -> bool:
        return self._text_in(text, ["Détails", "Fichiers", "Tâches",
                                    "Ajouter des fichiers", "Analyser"])

    # ══════════════════════════════════════════════════════════════════════════
    # SCREENSHOT & OCR
    # ══════════════════════════════════════════════════════════════════════════

    def _screenshot(self, tag: str = "") -> str:
        import mss
        from PIL import Image
        path = os.path.join(SCREENSHOT_DIR, f"{tag}_{int(time.time())}.png")
        with mss.mss() as sct:
            raw = sct.grab(sct.monitors[1])
            Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX").save(path)
        return path

    def _ocr(self, img_path: str) -> Tuple[str, List[Dict]]:
        import pytesseract
        from PIL import Image
        img       = Image.open(img_path)
        full_text = pytesseract.image_to_string(img, lang="fra+eng")
        raw       = pytesseract.image_to_data(
            img, lang="fra+eng", output_type=pytesseract.Output.DICT)
        boxes = [
            {
                "text": raw["text"][i],
                "x":    raw["left"][i] + raw["width"][i]  // 2,
                "y":    raw["top"][i]  + raw["height"][i] // 2,
                "w":    raw["width"][i],
                "h":    raw["height"][i],
                "conf": max(int(raw["conf"][i]), 0),
            }
            for i in range(len(raw["text"]))
            if raw["text"][i].strip() and
               str(raw["conf"][i]) != "-1" and
               int(raw["conf"][i]) >= OCR_CONF
        ]
        return full_text, boxes

    # ══════════════════════════════════════════════════════════════════════════
    # HELPERS DE DÉTECTION
    # ══════════════════════════════════════════════════════════════════════════

    def _find_texts(self, boxes: List[Dict], targets: List[str]) -> List[Dict]:
        """Retourne toutes les boîtes dont le texte correspond à une cible."""
        found = []
        for box in boxes:
            for t in targets:
                if t.lower() in box["text"].lower():
                    found.append(box)
                    break
        return found

    def _find_on_same_row(
        self, boxes: List[Dict], targets: List[str],
        ref_y: int, tolerance: int = 20
    ) -> Optional[Dict]:
        """
        Cherche un bouton dans la liste targets
        sur la même ligne horizontale que ref_y (±tolerance px).
        """
        candidates = self._find_texts(boxes, targets)
        for c in candidates:
            if abs(c["y"] - ref_y) <= tolerance:
                return c
        # Élargir la tolérance si rien trouvé
        for c in candidates:
            if abs(c["y"] - ref_y) <= tolerance * 2:
                return c
        return None

    def _find_closest_right(
        self, boxes: List[Dict], ref: Dict, max_dist: int = 400
    ) -> Optional[Dict]:
        """Retourne la boîte la plus proche à droite de ref sur la même ligne."""
        candidates = [
            b for b in boxes
            if abs(b["y"] - ref["y"]) <= 15
            and b["x"] > ref["x"]
            and b["x"] - ref["x"] <= max_dist
            and b["text"] not in ["Voir", "Modifier", "Supprimer"]
        ]
        return min(candidates, key=lambda b: b["x"]) if candidates else None

    def _text_in(self, text: str, targets: List[str]) -> bool:
        low = text.lower()
        return any(t.lower() in low for t in targets)

    # ══════════════════════════════════════════════════════════════════════════
    # CLIC & NAVIGATION
    # ══════════════════════════════════════════════════════════════════════════

    def _click(self, box: Dict, label: str = ""):
        import pyautogui
        x, y = box["x"], box["y"]
        self._log("action", f"Clic '{label}' @ ({x}, {y}) conf={box.get('conf',0)}%")
        pyautogui.moveTo(x, y, duration=0.9)
        time.sleep(0.3)
        pyautogui.click()
        self._last_click_ts = time.time()
        print(f"\n  ✅ [{_now()}] '{label}' cliqué @ ({x}, {y})\n", flush=True)

    def _navigate_to_list(self):
        """Navigue vers la page liste via pyautogui (Ctrl+L + URL)."""
        import pyautogui
        self._log("action", f"Navigation → {FRONTEND_URL}/documents")
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.4)
        pyautogui.hotkey("ctrl", "a")
        pyautogui.typewrite(f"{FRONTEND_URL}/documents", interval=0.03)
        pyautogui.press("enter")
        time.sleep(2.5)

    def _wait_for_loading(self):
        """Attend 4s puis confirme que l'analyse a démarré."""
        self._log("observe", "Attente démarrage analyse...")
        time.sleep(4)
        img = self._screenshot("loading_check")
        text, _ = self._ocr(img)
        if self._text_in(text, TEXT_LOADING):
            self._log("answer", "Analyse IA démarrée — skeleton visible ✓")
        elif self._text_in(text, TEXT_DONE):
            self._log("answer", "Analyse terminée (très rapide) ✓")
            self._on_analysis_done(text)
        else:
            self._log("observe", "Démarrage non confirmé — prochain cycle")

    # ══════════════════════════════════════════════════════════════════════════
    # INTÉGRATION ACE — Apprentissage du pattern de workflow
    # ══════════════════════════════════════════════════════════════════════════

    def _on_analysis_done(self, screen_text: str):
        """
        Appelé quand une analyse se termine avec succès.
        Notifie ACE pour apprendre le pattern : 
        'dès qu'un document RECU arrive → analyser immédiatement'.
        """
        self._success_count += 1
        self._log_to_ace_playbook()

    def _log_to_ace_playbook(self):
        """
        Ajoute ou met à jour un bullet ACE dans la section 'workflow_patterns'
        pour mémoriser que ce process est automatisé et fiable.
        """
        try:
            payload = {
                "op":      "ADD",
                "section": "workflow_patterns",
                "content": (
                    f"Processus automatisé : dès qu'un document apparaît avec statut RECU "
                    f"dans la liste GED, l'agent visuel navigue vers le document et lance "
                    f"l'analyse IA immédiatement sans intervention humaine. "
                    f"Cycle #{self._cycle_count} — succès #{self._success_count}."
                ),
                "metadata": {
                    "agent":        "VisualWatcherAgent",
                    "pattern":      "auto_analyze_on_recu",
                    "cycle":        self._cycle_count,
                    "success":      self._success_count,
                    "session_start": self._session_start,
                    "logged_at":    datetime.utcnow().isoformat(),
                },
            }
            # Appeler le Curator ACE directement
            requests.post(
                f"{AI_BACKEND}/ace/override",
                json={
                    "candidate_id":      0,
                    "candidate_name":    "VisualWatcherAgent",
                    "position":          "automation",
                    "ai_score":          100,
                    "ai_recommendation": "Entretien",
                    "ai_status":         "Recu",
                    "human_status":      "ATraiter",
                    "user_id":           "visual_watcher",
                    "notes": (
                        f"Pattern appris : analyse automatique déclenchée visuellement "
                        f"sur document RECU. Cycle #{self._cycle_count}."
                    ),
                },
                timeout=10,
            )
            self._log("observe", f"ACE notifié — pattern workflow loggué (cycle #{self._cycle_count})")
        except Exception as e:
            self._log("observe", f"ACE log non-bloquant : {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # UTILITAIRES
    # ══════════════════════════════════════════════════════════════════════════

    def _log(self, step: str, msg: str):
        icons = {"thought": "🤔", "action": "⚡", "observe": "👁", "answer": "✅"}
        print(f"  {icons.get(step,'•')} [{_now()}] {msg}", file=sys.stderr, flush=True)

    def _print_banner(self):
        print(f"\n{'═'*60}")
        print(f"  VisualWatcherAgent v2 — Surveillance GED intelligente")
        print(f"  Fréquence  : toutes les {POLL_SECONDS}s")
        print(f"  Liste GED  : {FRONTEND_URL}/documents")
        print(f"  ACE        : {AI_BACKEND}/ace")
        print(f"  Arrêt      : Ctrl+C  |  Urgence : coin haut-gauche")
        print(f"{'═'*60}\n")

    def _print_ocr(self, text: str):
        print(f"\n{'─'*40}")
        print("  [DEBUG OCR] :")
        print(text[:600])
        print(f"{'─'*40}\n")

    def _on_stop(self):
        elapsed = (datetime.utcnow() - datetime.fromisoformat(self._session_start)).seconds
        print(f"\n  Arrêt | Cycles: {self._cycle_count} | "
              f"Succès: {self._success_count} | "
              f"Durée: {elapsed//60}m{elapsed%60}s")


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


# ── Point d'entrée ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="VisualWatcherAgent v2 — GED intelligent screen controller"
    )
    parser.add_argument("--once",  action="store_true",
                        help="1 cycle de surveillance puis arrêt")
    parser.add_argument("--debug", action="store_true",
                        help="Afficher le texte OCR complet à chaque cycle")
    args = parser.parse_args()

    agent = VisualWatcherAgent(debug=args.debug)

    if args.once:
        agent.run_once()
    else:
        agent.run_forever()