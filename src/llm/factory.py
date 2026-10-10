"""Pick an LLM provider from the environment."""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv

from src.llm.types import LLMClient, LLMError

load_dotenv()


def get_llm(provider: Optional[str] = None, model: Optional[str] = None) -> LLMClient:
    """
    Provider resolution order:
      1. explicit ``provider`` argument
      2. ``LLM_PROVIDER`` env var ("anthropic" | "gemini")
      3. whichever API key is present (ANTHROPIC_API_KEY first, then GEMINI_API_KEY)

    Set LLM_PROVIDER=anthropic explicitly if you authenticate via ``ant auth login``
    instead of an API key.
    """
    provider = (provider or os.getenv("LLM_PROVIDER") or "").lower()
    if not provider:
        if os.getenv("ANTHROPIC_API_KEY"):
            provider = "anthropic"
        elif os.getenv("GEMINI_API_KEY"):
            provider = "gemini"
        else:
            raise LLMError(
                "No LLM configured. Set LLM_PROVIDER plus ANTHROPIC_API_KEY or GEMINI_API_KEY."
            )

    if provider == "anthropic":
        from src.llm.anthropic_client import AnthropicLLM

        return AnthropicLLM(model=model)
    if provider in ("gemini", "google"):
        from src.llm.gemini_client import GeminiLLM

        return GeminiLLM(model=model)
    raise LLMError(f"Unknown LLM_PROVIDER '{provider}' (expected 'anthropic' or 'gemini')")
