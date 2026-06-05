"""Legacy LLM client protocol (deprecated).

This module defined a simple string-based LLM client protocol, but has been
superseded by DSPy's structured approach. New code should use dspy.LM directly.

Historical reference only - not exported from prismadv.llm.
"""

from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    """Legacy protocol for simple string-based LLM completion.

    DEPRECATED: Use dspy.LM instead for structured prompting and typed I/O.
    """

    def complete(self, prompt: str) -> str:
        """Complete a prompt and return the response as a string."""
        ...
