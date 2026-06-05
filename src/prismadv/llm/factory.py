"""Factory functions for creating LLM instances."""

from __future__ import annotations

import logging
import os
from typing import Literal, Optional

logger = logging.getLogger(__name__)

# Default models (cheap and fast)
DEFAULT_MODELS = {
    "openai": "openai/gpt-4o-mini",
    "anthropic": "anthropic/claude-3-5-haiku-20241022",
    "gemini": "gemini/gemini-2.5-flash",
}

LLMProvider = Literal["openai", "anthropic", "gemini"]


def create_lm_from_env(
    *,
    model: Optional[str] = None,
    load_dotenv: bool = True,
) -> "dspy.LM":
    """Create a DSPy LM instance by auto-detecting API keys from environment.

    Checks for API keys in this order:
    1. OPENAI_API_KEY → uses gpt-4o-mini by default
    2. ANTHROPIC_API_KEY → uses claude-3-5-haiku by default
    3. GEMINI_API_KEY or GOOGLE_API_KEY → uses gemini-2.5-flash by default

    The model can be overridden with the LLM_MODEL environment variable or
    the model parameter.

    Args:
        model: Optional model override (e.g., "openai/gpt-4o", "gemini/gemini-2.5-flash")
        load_dotenv: Whether to load .env file (default True)

    Returns:
        Configured DSPy LM instance

    Raises:
        ImportError: If dspy is not installed
        ValueError: If no API key is found in environment

    Example:
        >>> from prismadv.llm import create_lm_from_env
        >>> lm = create_lm_from_env()  # Auto-detect from environment
        >>> lm = create_lm_from_env(model="openai/gpt-4o")  # Override model
    """
    try:
        import dspy
    except ImportError:
        raise ImportError(
            "dspy is required for LLM functionality. "
            "Install with: uv sync --extra dspy"
        )

    # Load .env file if requested
    if load_dotenv:
        try:
            from dotenv import load_dotenv as _load_dotenv

            _load_dotenv()
        except ImportError:
            pass  # python-dotenv not installed, use system environment variables

    # Check for model override in environment
    model = model or os.getenv("LLM_MODEL")

    # Auto-detect provider and API key
    if os.getenv("OPENAI_API_KEY"):
        provider = "openai"
        api_key = os.getenv("OPENAI_API_KEY")
        model = model or DEFAULT_MODELS["openai"]
    elif os.getenv("ANTHROPIC_API_KEY"):
        provider = "anthropic"
        api_key = os.getenv("ANTHROPIC_API_KEY")
        model = model or DEFAULT_MODELS["anthropic"]
    elif os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        provider = "gemini"
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        model = model or DEFAULT_MODELS["gemini"]
    else:
        raise ValueError(
            "No LLM API key found in environment. "
            "Set one of: OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY"
        )

    # Ensure model has provider prefix (e.g., "gemini/gemini-2.5-flash")
    # This is required for DSPy/litellm to route to the correct API
    if "/" not in model:
        model = f"{provider}/{model}"

    logger.info(f"🤖 Using {provider.upper()} LLM: {model}")

    return dspy.LM(model, api_key=api_key, cache=False)


def create_lm(
    provider: LLMProvider,
    api_key: str,
    model: Optional[str] = None,
) -> "dspy.LM":
    """Create a DSPy LM instance with explicit configuration.

    Args:
        provider: LLM provider ("openai", "anthropic", or "gemini")
        api_key: API key for the provider
        model: Optional model override. If not provided, uses cheap default.

    Returns:
        Configured DSPy LM instance

    Raises:
        ImportError: If dspy is not installed
        ValueError: If provider is invalid

    Example:
        >>> from prismadv.llm import create_lm
        >>> lm = create_lm("openai", api_key="sk-...", model="openai/gpt-4o")
        >>> lm = create_lm("gemini", api_key="...", model="gemini/gemini-2.5-flash")
    """
    try:
        import dspy
    except ImportError:
        raise ImportError(
            "dspy is required for LLM functionality. "
            "Install with: uv sync --extra dspy"
        )

    if provider not in DEFAULT_MODELS:
        raise ValueError(
            f"Invalid provider: {provider}. "
            f"Must be one of: {', '.join(DEFAULT_MODELS.keys())}"
        )

    # Use default model if not specified
    model = model or DEFAULT_MODELS[provider]

    # Ensure model has provider prefix (e.g., "gemini/gemini-2.5-flash")
    # This is required for DSPy/litellm to route to the correct API
    if "/" not in model:
        model = f"{provider}/{model}"

    logger.info(f"🤖 Using {provider.upper()} LLM: {model}")

    return dspy.LM(model, api_key=api_key, cache=False)
