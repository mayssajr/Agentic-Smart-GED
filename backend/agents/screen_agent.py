# screen_agent.py
from agents.base_agent import BaseAgent
import mss, mss.tools, pyautogui, pytesseract, base64
from PIL import Image
import io

class ScreenAgent(BaseAgent):
    NAME   = "ScreenAgent"
    SKILLS = ["screen_read", "screen_click", "screen_type"]
    TOOL_SERVERS = []

    def capture_screen(self) -> tuple[str, Image.Image]:
        """Capture l'écran et retourne base64 + PIL Image"""
        with mss.mss() as sct:
            raw = sct.grab(sct.monitors[1])
            img = Image.frombytes("RGB", raw.size, raw.rgb)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()
        return b64, img

    def read_screen_text(self) -> str:
        """OCR sur l'écran courant"""
        _, img = self.capture_screen()
        return pytesseract.image_to_string(img, lang="fra+eng")

    def understand_screen_with_llm(self, b64_img: str, question: str = "") -> str:
        """
        Envoie le screenshot au LLM vision pour comprendre le contexte.
        Groq : llava-v1.5-7b-4096-preview (gratuit)
        """
        import requests, os
        prompt = question or (
            "Décris ce qui est affiché à l'écran. "
            "Identifie : l'application ouverte, les éléments cliquables visibles, "
            "le contenu principal, et suggère 3 actions pertinentes."
        )
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
                     "Content-Type": "application/json"},
            json={
                "model": "llava-v1.5-7b-4096-preview",
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image_url",
                         "image_url": {"url": f"data:image/png;base64,{b64_img}"}},
                        {"type": "text", "text": prompt}
                    ]
                }],
                "max_tokens": 500,
            },
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        return ""

    def move_and_click(self, x: int, y: int) -> bool:
        try:
            pyautogui.moveTo(x, y, duration=0.4)
            pyautogui.click()
            return True
        except Exception as e:
            self._step("observe", f"click failed: {e}")
            return False

    def run(self, action: str, x: int = 0, y: int = 0,
            text: str = "", question: str = "", **_) -> dict:
        self._reset()

        if action == "read":
            b64, _ = self.capture_screen()
            ocr    = self.read_screen_text()
            llm    = self.understand_screen_with_llm(b64, question)
            return {"ocr_text": ocr, "llm_analysis": llm,
                    "react_trace": self.trace}

        if action == "click":
            ok = self.move_and_click(x, y)
            return {"success": ok, "react_trace": self.trace}

        if action == "type":
            pyautogui.typewrite(text, interval=0.04)
            return {"success": True, "react_trace": self.trace}

        if action == "hotkey":
            keys = text.split("+")
            pyautogui.hotkey(*keys)
            return {"success": True, "react_trace": self.trace}

        return {"error": f"Action inconnue : {action}"}