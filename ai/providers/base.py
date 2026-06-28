from __future__ import annotations

from abc import ABC, abstractmethod


class LLMGatewayError(Exception):
    pass


class LLMProviderError(LLMGatewayError):
    pass


class LLMProviderAuthError(LLMProviderError):
    pass


class LLMProviderTimeoutError(LLMProviderError):
    pass


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError
