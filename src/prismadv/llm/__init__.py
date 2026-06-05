"""LLM utilities and error handling.

Note: This module previously defined an LLMClient protocol, but we've moved
to using DSPy directly for all LLM interactions. See prismadv.generation for
DSPy-based implementations.
"""

from prismadv.llm.errors import LLMError, LLMOutputError
from prismadv.llm.factory import create_lm, create_lm_from_env

__all__ = [
    "LLMError",
    "LLMOutputError",
    "create_lm",
    "create_lm_from_env",
]
