from __future__ import annotations

import time

import httpx

from ai.providers.base import LLMProvider, LLMProviderAuthError, LLMProviderError, LLMProviderTimeoutError


class OpenAIProvider(LLMProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4o-mini",
        timeout_seconds: float = 20.0,
        max_retries: int = 2,
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        self.api_key = api_key.strip()
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)
        self.base_url = base_url.rstrip("/")

    def _build_payload(self, system_prompt: str, user_prompt: str) -> dict:
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise LLMProviderAuthError("OPENAI_API_KEY is not set")

        payload = self._build_payload(system_prompt, user_prompt)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/chat/completions"

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(url, headers=headers, json=payload)

                if response.status_code == 401:
                    raise LLMProviderAuthError("OpenAI authentication failed")
                if response.status_code in {429, 500, 502, 503, 504}:
                    raise LLMProviderError(f"OpenAI transient error: {response.status_code}")

                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            except httpx.TimeoutException as exc:
                last_error = LLMProviderTimeoutError(f"OpenAI request timed out: {exc}")
            except (KeyError, IndexError, TypeError) as exc:
                raise LLMProviderError(f"Malformed OpenAI response: {exc}") from exc
            except LLMProviderAuthError:
                raise
            except Exception as exc:  # noqa: BLE001
                if isinstance(exc, LLMProviderError):
                    last_error = exc
                else:
                    last_error = LLMProviderError(str(exc))

            if attempt < self.max_retries:
                time.sleep(min(2**attempt, 3))

        assert last_error is not None
        raise last_error
