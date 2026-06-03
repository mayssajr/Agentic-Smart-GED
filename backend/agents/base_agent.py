from __future__ import annotations

import os
import sys
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union

BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class BaseAgent(ABC):

    NAME:          str       = "BaseAgent"
    SKILLS:        List[str] = []
    SYSTEM_PROMPT: str       = ""
    TOOL_SERVERS:  list      = []

    def __init__(self) -> None:
        self.trace: List[dict] = []
        self._t0: float = 0.0
        if BASE_DIR not in sys.path:
            sys.path.insert(0, BASE_DIR)

    def _step(self, step_type: str, content: str) -> None:
        entry = {"type": step_type, "content": content, "ms": self._elapsed_ms()}
        self.trace.append(entry)
        print(f"[{self.NAME}/{step_type.upper()}] {content[:120]}", file=sys.stderr)

    def _reset(self) -> None:
        self.trace = []
        self._t0   = time.time()

    def _elapsed_ms(self) -> int:
        return int((time.time() - self._t0) * 1000)

    def _call_tool(self, server: Union[str, dict],
                   tool_name: str, args: Dict[str, Any]) -> str:
        from mcp_client import call_mcp_tool
        return call_mcp_tool(server, tool_name, args)

    def _call_tool_safe(self, server: Union[str, dict],
                        tool_name: str, args: Dict[str, Any],
                        default: str = "") -> str:
        try:
            return self._call_tool(server, tool_name, args)
        except Exception as e:
            self._step("observe", f"_call_tool_safe failed ({tool_name}): {e}")
            return default

    def _generate(self, prompt: str, max_tokens: int, system: str = "") -> str:
        from services.llm_client import generate
        return generate(prompt, max_tokens=max_tokens,
                        system=system or self.SYSTEM_PROMPT)

    @abstractmethod
    def run(self, **kwargs) -> dict:
        raise NotImplementedError

    def get_skills(self) -> List[str]:
        return list(self.SKILLS)

    def has_skill(self, skill_id: str) -> bool:
        return skill_id in self.SKILLS