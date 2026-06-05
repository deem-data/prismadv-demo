"""LLM-based instruction proposer for the GEPA optimization loop.

Mirrors the GlobalInstructionProposalSignature from the GEPA research code
(code/workflow_dspy/gepa/strategies/instruction_proposal.py) but is fully
self-contained in the demo package.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

try:
    import dspy
except ImportError:
    raise ImportError(
        "dspy is required for the optimization module. "
        "Install with: uv sync --extra dspy"
    )


# ---------------------------------------------------------------------------
# DSPy Signature
# ---------------------------------------------------------------------------

class InstructionProposalSig(dspy.Signature):
    """You are an expert prompt engineer optimizing a task-aware data validation system.

    The system uses three sequential LLM modules to generate data quality constraints:
    1. Column Access Detection: identifies which dataset columns a task script accesses
    2. Assumption Extraction: infers what data quality properties the code assumes
    3. Constraint Code Generation: converts assumptions into executable GX / Deequ rules

    The optimization objective is COLUMN-LEVEL FAILURE PRECISION (CFPr):
    CFPr = P(task fails | column constraint fires)
    A high CFPr means constraints only fire when the task actually fails (no false alarms).
    A low CFPr means constraints fire even on clean data (false alarms).

    You are given:
    - Current module instructions (one per module)
    - Feedback: examples of constraints that fired on clean data (false alarms) or
      missed real errors, with the associated code context and assumption traces

    Your task: propose improved instructions for one or more modules to increase CFPr.
    Focus on:
    - Making constraints more specific (avoid over-generalizing)
    - Ensuring constraints match the actual logic in the task code
    - Reducing false alarms on typical clean data distributions
    - Maintaining error-level (not warning-level) constraints

    IMPORTANT: Preserve the output format specifications in the instructions.
    Return valid JSON with exactly the keys requested.
    """

    # Current module configurations (JSON-serialized dict of module_name -> instruction_text)
    current_modules: str = dspy.InputField(
        desc="JSON object mapping module names to their current instruction texts"
    )

    # Feedback per module (JSON-serialized dict of module_name -> list of feedback dicts)
    feedback: str = dspy.InputField(
        desc="JSON object mapping module names to lists of feedback examples"
    )

    # Which modules to update (JSON array of module names)
    modules_to_update: str = dspy.InputField(
        desc="JSON array of module names to update (subset of current_modules keys)"
    )

    # Output: updated instruction texts (JSON object, only for modules_to_update)
    updated_instructions: dict[str, str] = dspy.OutputField(
        desc=(
            "JSON object mapping module names to their NEW instruction texts. "
            "Only include modules listed in modules_to_update. "
            "Instructions must be complete and self-contained."
        )
    )


# ---------------------------------------------------------------------------
# Proposer class
# ---------------------------------------------------------------------------

class InstructionProposer:
    """Proposes updated module instructions using an LLM.

    Wraps InstructionProposalSig and handles JSON serialisation / error recovery.
    """

    def __init__(self, lm: dspy.LM):
        self._lm = lm
        self._predictor = dspy.Predict(InstructionProposalSig)

    def propose(
        self,
        current_candidate: dict[str, str],
        reflective_dataset: dict[str, list[dict]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        """Propose new instructions for the specified components.

        Args:
            current_candidate: Current instructions {component_name: instruction_text}
            reflective_dataset: Feedback per component {component_name: [feedback_dict, ...]}
            components_to_update: Which components to update

        Returns:
            New instructions dict for updated components. Falls back to the
            current candidate on any LLM error.
        """
        try:
            with dspy.context(lm=self._lm):
                result = self._predictor(
                    current_modules=json.dumps(current_candidate, indent=2),
                    feedback=json.dumps(reflective_dataset, indent=2),
                    modules_to_update=json.dumps(components_to_update),
                )
            new_instrs = result.updated_instructions

            # Validate that the output covers the requested components
            if not isinstance(new_instrs, dict):
                raise ValueError(f"Expected dict output, got {type(new_instrs)}")

            # Merge: start from current, overwrite with proposed updates
            merged = dict(current_candidate)
            for comp in components_to_update:
                if comp in new_instrs and isinstance(new_instrs[comp], str) and new_instrs[comp].strip():
                    merged[comp] = new_instrs[comp].strip()
                else:
                    logger.warning("Proposer did not update component %r — keeping current", comp)

            return merged

        except Exception as exc:
            logger.warning("Instruction proposal failed (%s) — keeping current candidate", exc)
            return dict(current_candidate)
