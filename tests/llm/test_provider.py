"""Provider tests (offline: neither anthropic nor openai installed/required)."""
from __future__ import annotations

import sys

import pytest

from src.llm.provider import (ANTHROPIC_MODEL, OPENAI_MODEL,
                              AnthropicProvider, LLMProvider, OpenAIProvider)


def test_module_imports_without_llm_sdks():
    # The top-of-file import already proves it; assert neither SDK was pulled in.
    assert isinstance(AnthropicProvider(), LLMProvider)
    assert isinstance(OpenAIProvider(), LLMProvider)


def test_model_constants():
    assert ANTHROPIC_MODEL == "claude-sonnet-5"
    assert OPENAI_MODEL == "gpt-4o"
    assert AnthropicProvider.model == ANTHROPIC_MODEL
    assert OpenAIProvider.model == OPENAI_MODEL


@pytest.mark.parametrize("provider_cls,key", [
    (AnthropicProvider, "ANTHROPIC_API_KEY"),
    (OpenAIProvider, "OPENAI_API_KEY"),
])
def test_missing_api_key_raises_clear_error(monkeypatch, provider_cls, key):
    monkeypatch.delenv(key, raising=False)
    with pytest.raises(RuntimeError, match=key):
        provider_cls().complete("system", "user")


@pytest.mark.parametrize("provider_cls,key,module", [
    (AnthropicProvider, "ANTHROPIC_API_KEY", "anthropic"),
    (OpenAIProvider, "OPENAI_API_KEY", "openai"),
])
def test_missing_sdk_raises_install_hint(monkeypatch, provider_cls, key, module):
    monkeypatch.setenv(key, "test-key")
    monkeypatch.setitem(sys.modules, module, None)  # force ImportError
    with pytest.raises(RuntimeError, match="requirements-llm.txt") as excinfo:
        provider_cls().complete("system", "user")
    assert module in str(excinfo.value)
