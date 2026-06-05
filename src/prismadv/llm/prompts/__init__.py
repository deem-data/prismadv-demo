"""Legacy string-based prompts (deprecated).

This module contained manual prompt templates for use with the old LLMClient protocol.
With the migration to DSPy, prompts are now defined as dspy.Signature classes which
DSPy optimizes automatically.

See prismadv.generation.signatures for DSPy-based prompts.

Historical reference only - these prompts are no longer used in the codebase.
"""

from prismadv.llm.prompts.column_access_detection import COLUMN_ACCESS_DETECTION_PROMPT

__all__ = [
    "COLUMN_ACCESS_DETECTION_PROMPT",
]
