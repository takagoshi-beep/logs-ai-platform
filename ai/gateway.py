from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from jinja2 import Template

from ai.providers.base import LLMGatewayError, LLMProvider
from ai.providers.openai import OpenAIProvider

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PROMPT_DIR = ROOT_DIR / "prompts"


class PromptNotFoundError(LLMGatewayError):
    pass


class LLMGateway:
    def __init__(self, provider: LLMProvider, prompt_dir: Path | None = None) -> None:
        self.provider = provider
        self.prompt_dir = prompt_dir or DEFAULT_PROMPT_DIR

    @classmethod
    def from_env(cls) -> "LLMGateway":
        provider_name = (os.getenv("LLM_PROVIDER") or "openai").strip().lower()
        if provider_name != "openai":
            raise LLMGatewayError(f"Unsupported provider: {provider_name}")

        provider = OpenAIProvider(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            timeout_seconds=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "20")),
            max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "2")),
        )
        return cls(provider=provider)

    def _render_prompt(self, template_name: str, context: dict[str, Any]) -> str:
        template_path = self.prompt_dir / template_name
        if not template_path.exists():
            raise PromptNotFoundError(f"Prompt not found: {template_path}")
        content = template_path.read_text(encoding="utf-8")
        return Template(content).render(**context).strip()

    def generate_answer(
        self,
        *,
        message: str,
        plan: dict[str, Any],
        workflow: dict[str, Any],
        results: list[dict[str, Any]],
        draft_answer: str,
    ) -> str:
        context = {
            "message": message,
            "draft_answer": draft_answer,
            "plan_json": json.dumps(plan, ensure_ascii=False, indent=2),
            "workflow_json": json.dumps(workflow, ensure_ascii=False, indent=2),
            "results_json": json.dumps(results, ensure_ascii=False, indent=2),
        }
        system_prompt = self._render_prompt("answer_system.txt", context)
        user_prompt = self._render_prompt("answer_user.txt", context)

        try:
            answer = self.provider.generate(system_prompt=system_prompt, user_prompt=user_prompt)
            return (answer or "").strip() or draft_answer
        except Exception:
            # Keep runtime resilient in local/test environments without API keys.
            return draft_answer
