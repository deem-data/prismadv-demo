"""Global active-instructions store for the optimization module.

When the user applies optimized prompts, the instructions are stored here.
Every new GenerationOrchestrator created in the API layer will check and
apply these overrides if present.
"""

from __future__ import annotations

from typing import Optional

# Module-level store: {component_name: instruction_text} or None (baseline)
_active_instructions: Optional[dict[str, str]] = None


def set_active_instructions(instructions: dict[str, str]) -> None:
    """Store optimized instructions as the active set for future generation runs."""
    global _active_instructions
    _active_instructions = dict(instructions)


def get_active_instructions() -> Optional[dict[str, str]]:
    """Return the active optimized instructions, or None if using baseline."""
    return _active_instructions


def clear_active_instructions() -> None:
    """Reset to baseline (original) instructions."""
    global _active_instructions
    _active_instructions = None


def has_active_instructions() -> bool:
    return _active_instructions is not None
