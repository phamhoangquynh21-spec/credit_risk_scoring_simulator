"""LLM providers for memo generation (Stage 5.4).

The ``anthropic``/``openai`` SDKs are optional extras (requirements-llm.txt)
and are lazy-imported inside ``complete()``, so importing this module needs
neither. API keys are read from the environment at call time; a missing key
or SDK raises a clear RuntimeError (memo.py turns provider failures into the
template fallback, so scoring never depends on an LLM being reachable).
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod

ANTHROPIC_MODEL = "claude-sonnet-5"
OPENAI_MODEL = "gpt-4o"

_INSTALL_HINT = ("install the optional LLM extras: "
                 "pip install -r requirements-llm.txt")


class LLMProvider(ABC):
    """A chat-completion backend for memo generation."""

    name: str = "abstract"
    model: str = "abstract"

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Return the completion text for a system + user prompt pair."""


def _require_env(var: str) -> str:
    value = os.environ.get(var)
    if not value:
        raise RuntimeError(
            f"{var} is not set; export it to use this provider "
            "(or pass provider=None to generate_memo for the template fallback)")
    return value


class AnthropicProvider(LLMProvider):
    name = "anthropic"
    model = ANTHROPIC_MODEL

    def complete(self, system: str, user: str) -> str:
        api_key = _require_env("ANTHROPIC_API_KEY")
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError(
                f"the 'anthropic' package is not installed; {_INSTALL_HINT}"
            ) from exc
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=self.model, max_tokens=1024, system=system,
            messages=[{"role": "user", "content": user}])
        return response.content[0].text


class OpenAIProvider(LLMProvider):
    name = "openai"
    model = OPENAI_MODEL

    def complete(self, system: str, user: str) -> str:
        api_key = _require_env("OPENAI_API_KEY")
        try:
            import openai
        except ImportError as exc:
            raise RuntimeError(
                f"the 'openai' package is not installed; {_INSTALL_HINT}"
            ) from exc
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}])
        return response.choices[0].message.content
