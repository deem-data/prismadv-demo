"""Generation orchestrator that coordinates the full constraint generation pipeline."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Sequence

try:
    import dspy
except ImportError:
    raise ImportError(
        "dspy is required for generation module. "
        "Install with: uv sync --extra dspy"
    )

logger = logging.getLogger(__name__)

from prismadv.generation.assumption_extractor import AssumptionExtractor
from prismadv.generation.column_access import ColumnAccessDetector
from prismadv.generation.constraint_generator import ConstraintGenerator
from prismadv.generation.data_flow_detector import DataFlowDetector
from prismadv.generation.flow_graph_builder import FlowGraphBuilder
from prismadv.ir import AssumptionIR, ConstraintIR
from prismadv.profiling import ProfilerBackend, get_profiler
from prismadv.profiling.results import ProfileBundle


class GenerationContext:
    """Complete context from constraint generation pipeline.

    This holds all the IR objects and intermediate results from
    the generation process, enabling rich provenance tracking and
    multiple output formats (API, Python library, exports).
    """

    def __init__(
        self,
        *,
        task_code: str,
        task_file_name: str,
        dataset_path: str,
        dataset_profile: ProfileBundle,
        task_description: str,
        accessed_columns: list[str],
        data_flow_map: dict[str, list] | None = None,
        assumptions: list[AssumptionIR],
        constraints: list[ConstraintIR],
        llm_cost: float = 0.0,
        cost_breakdown: dict[str, float] | None = None,
        warnings: list[str] | None = None,
    ):
        """Initialize generation context.

        Args:
            task_code: The task code that was analyzed
            task_file_name: Name of the task file
            dataset_path: Path to the dataset
            dataset_profile: Profiling results (ProfileBundle) from the dataset
            task_description: Description of what the task does
            accessed_columns: Columns accessed in the code
            assumptions: Extracted assumptions
            constraints: Generated constraints
            llm_cost: Total LLM API cost in USD
            cost_breakdown: Per-stage cost breakdown (column_detection, assumption_extraction, constraint_generation)
        """
        self.task_code = task_code
        self.task_file_name = task_file_name
        self.dataset_path = dataset_path
        self.dataset_profile = dataset_profile
        self.task_description = task_description
        self.accessed_columns = accessed_columns
        self.data_flow_map: dict[str, list] = data_flow_map or {}
        self.assumptions = assumptions
        self.constraints = constraints
        self.llm_cost = llm_cost
        self.cost_breakdown: dict[str, float] = cost_breakdown or {}
        self.warnings: list[str] = warnings or []


class GenerationOrchestrator:
    """Orchestrate the full constraint generation pipeline.

    This class coordinates all steps:
    1. Profile dataset
    2. Detect accessed columns
    3. Extract assumptions from code
    4. Generate constraints (Deequ + GX)
    5. Build flow graph

    Returns a GenerationContext with all IR objects for rich provenance.
    """

    def __init__(
        self,
        *,
        lm: dspy.LM,
        profiler_backend: ProfilerBackend = ProfilerBackend.BUILTIN,
        max_parallel_llm_calls: int = 5,
    ):
        """Initialize the orchestrator.

        Args:
            lm: DSPy language model for LLM-powered components
            profiler_backend: Backend to use for dataset profiling
            max_parallel_llm_calls: Maximum concurrent LLM calls (default 5)
        """
        self._lm = lm
        self._profiler_backend = profiler_backend
        self._max_parallel_llm_calls = max_parallel_llm_calls

        # Initialize all components
        self._column_detector = ColumnAccessDetector(lm=lm)
        self._data_flow_detector = DataFlowDetector(lm=lm)
        self._assumption_extractor = AssumptionExtractor(lm=lm)
        self._constraint_generator = ConstraintGenerator(lm=lm)
        self._flow_graph_builder = FlowGraphBuilder()

    def _calculate_llm_cost(self) -> float:
        """Calculate total LLM cost from DSPy LM history.

        Uses litellm's cost calculation based on model and token usage.

        Returns:
            Total cost in USD, or 0.0 if calculation fails
        """
        try:
            import litellm

            total_cost = 0.0
            history = getattr(self._lm, "history", [])

            for entry in history:
                # DSPy history entries: {"response": litellm.ModelResponse, ...}
                # Usage is an attribute on the response object, not a top-level key.
                response = entry.get("response")
                if not response:
                    continue

                try:
                    # Pass the full response object — litellm extracts model + usage itself
                    cost = litellm.completion_cost(completion_response=response)
                    total_cost += cost
                except Exception as e:
                    # Some models may not have pricing info; fall back to token-level calc
                    raw_usage = getattr(response, "usage", None)
                    if raw_usage:
                        prompt_tokens = getattr(raw_usage, "prompt_tokens", 0) or 0
                        completion_tokens = getattr(raw_usage, "completion_tokens", 0) or 0
                        model = getattr(response, "model", None) or self._lm.model
                        if prompt_tokens > 0 or completion_tokens > 0:
                            try:
                                cost = litellm.completion_cost(
                                    model=model,
                                    prompt_tokens=prompt_tokens,
                                    completion_tokens=completion_tokens,
                                )
                                total_cost += cost
                            except Exception:
                                pass
                    logger.debug(f"Could not calculate cost for entry: {e}")

            return total_cost

        except ImportError:
            logger.warning("litellm not available for cost calculation")
            return 0.0
        except Exception as e:
            logger.warning(f"Failed to calculate LLM cost: {e}")
            return 0.0

    def _clear_lm_history(self) -> None:
        """Clear LM history before a new generation run."""
        if hasattr(self._lm, "history"):
            self._lm.history.clear()

    def generate(
        self,
        *,
        task_code: str,
        task_file_name: str,
        dataset_path: str | Path,
        task_description: str,
        columns_desc: str | None = None,
        progress_callback: "Callable[[float, str], None] | None" = None,
        stage_callback: "Callable[[str, GenerationContext], None] | None" = None,
        selected_columns: list[str] | None = None,
        column_detection_cost: float = 0.0,
    ) -> GenerationContext:
        """Run the full constraint generation pipeline.

        Args:
            task_code: The code to analyze
            task_file_name: Name of the task file (for provenance)
            dataset_path: Path to the CSV dataset
            task_description: Description of what the task does
            columns_desc: Optional formatted column description
            progress_callback: Optional callback(progress, step) for progress updates.
                              progress is 0.0-1.0, step is human-readable description.

        Returns:
            GenerationContext with all IR objects and results

        Raises:
            Various exceptions from individual pipeline stages
        """

        def report_progress(progress: float, step: str) -> None:
            """Report progress if callback is provided."""
            if progress_callback:
                progress_callback(progress, step)
            logger.info(f"📊 {step} ({progress:.0%})")

        # Clear LM history to track costs for this generation only
        self._clear_lm_history()

        # Step 1: Profile dataset
        report_progress(0.0, "Profiling dataset...")
        profiler = get_profiler(self._profiler_backend)
        # Generate dataset ID from path (for now, could be improved)
        import uuid
        dataset_id = f"dataset-{uuid.uuid4().hex[:8]}"
        dataset_profile = profiler.profile_csv(
            str(dataset_path),
            dataset_id=dataset_id,
            dataset_name=Path(dataset_path).name,
        )

        # Get column names and types from the dataset
        all_columns = [col.name for col in dataset_profile.dataset.columns]
        column_types = {col.name: col.inferred_type for col in dataset_profile.dataset.columns}

        # Step 2: Detect accessed columns (or use user selection)
        if selected_columns is not None:
            valid = set(all_columns)
            accessed_columns = [c for c in selected_columns if c in valid]
            if not accessed_columns:
                # Fall back to full detection if selection is empty/invalid
                report_progress(0.15, "Analyzing code for column access...")
                accessed_columns = self._column_detector.detect(
                    columns=all_columns,
                    code_script=task_code,
                    downstream_task_description=task_description,
                    columns_desc=columns_desc,
                )
            else:
                report_progress(0.20, f"Using {len(accessed_columns)} selected column(s)...")
        else:
            report_progress(0.15, "Analyzing code for column access...")
            accessed_columns = self._column_detector.detect(
                columns=all_columns,
                code_script=task_code,
                downstream_task_description=task_description,
                columns_desc=columns_desc,
            )

        # Snapshot cost after column detection stage.
        # If columns were pre-selected (detection ran in a separate API call),
        # use the externally provided detection cost instead of LM history (which won't have it).
        if selected_columns is not None and accessed_columns:
            cost_after_detection = column_detection_cost
        else:
            cost_after_detection = self._calculate_llm_cost()

        # Step 2.5: Detect data flow per column (parallel)
        n_cols = len(accessed_columns)
        report_progress(0.20, f"Detecting data flow... (0 / {n_cols} columns)")

        # Accumulate data flow results per column for progressive updates
        accumulated_data_flow: dict[str, list] = {}

        def on_data_flow_done(completed: int, total: int) -> None:
            mapped = 0.20 + (completed / total) * 0.10
            report_progress(mapped, f"Detecting data flow... ({completed} / {total} columns)")

        def on_data_flow_result(column: str, result: tuple[str, list]) -> None:
            col_name, spans = result
            accumulated_data_flow[col_name] = spans
            if stage_callback:
                partial_ctx = GenerationContext(
                    task_code=task_code,
                    task_file_name=task_file_name,
                    dataset_path=str(dataset_path),
                    dataset_profile=dataset_profile,
                    task_description=task_description,
                    accessed_columns=list(accumulated_data_flow.keys()),
                    data_flow_map=dict(accumulated_data_flow),
                    assumptions=[],
                    constraints=[],
                )
                stage_callback("data_flow_item", partial_ctx)

        data_flow_map = self._data_flow_detector.detect_parallel(
            code_script=task_code,
            accessed_columns=accessed_columns,
            task_description=task_description,
            max_workers=self._max_parallel_llm_calls,
            item_done_callback=on_data_flow_done,
            item_result_callback=on_data_flow_result,
        )

        # Snapshot cost after data flow detection
        cost_after_data_flow = self._calculate_llm_cost()

        # Step 3: Extract assumptions from code (in parallel per column)
        gen_warnings: list[str] = []

        report_progress(0.30, f"Extracting assumptions... (0 / {n_cols} columns)")

        # Accumulate assumptions as each column completes for progressive updates
        accumulated_assumptions: list[AssumptionIR] = []

        def on_column_done(completed: int, total: int) -> None:
            mapped = 0.30 + (completed / total) * 0.25
            report_progress(mapped, f"Extracting assumptions... ({completed} / {total} columns)")

        def on_assumption_result(column: str, column_assumptions: list[AssumptionIR]) -> None:
            accumulated_assumptions.extend(column_assumptions)
            if stage_callback and column_assumptions:
                partial_ctx = GenerationContext(
                    task_code=task_code,
                    task_file_name=task_file_name,
                    dataset_path=str(dataset_path),
                    dataset_profile=dataset_profile,
                    task_description=task_description,
                    accessed_columns=accessed_columns,
                    data_flow_map=data_flow_map,
                    assumptions=list(accumulated_assumptions),
                    constraints=[],
                )
                stage_callback("assumption_item", partial_ctx)

        assumptions = self._assumption_extractor.extract_parallel(
            code_script=task_code,
            columns=all_columns,
            accessed_columns=accessed_columns,
            task_description=task_description,
            columns_desc=columns_desc,
            source_file=task_file_name,
            max_workers=self._max_parallel_llm_calls,
            item_done_callback=on_column_done,
            item_result_callback=on_assumption_result,
            data_flow_map=data_flow_map,
        )

        # Warn if fewer assumptions than columns (some columns had LLM errors)
        cols_with_assumptions = len({a.columns[0] for a in assumptions if a.columns})
        if cols_with_assumptions < n_cols:
            skipped = n_cols - cols_with_assumptions
            gen_warnings.append(
                f"{skipped} of {n_cols} columns produced no assumptions (LLM extraction failed)."
            )

        # Snapshot cost after assumption extraction (before constraint generation)
        cost_after_assumptions = self._calculate_llm_cost()

        # Step 4: Generate constraints from assumptions (in parallel per assumption)
        n_assumptions = len(assumptions)
        report_progress(0.55, f"Generating constraints... (0 / {n_assumptions} assumptions)")

        # Accumulate constraints as each assumption completes for progressive updates
        accumulated_constraints: list[ConstraintIR] = []

        def on_constraint_progress(completed: int, total: int) -> None:
            mapped = 0.55 + (completed / total) * 0.35
            report_progress(mapped, f"Generating constraints... ({completed} / {total} assumptions)")

        def on_constraint_result(assumption: AssumptionIR, new_constraints: list[ConstraintIR]) -> None:
            accumulated_constraints.extend(new_constraints)
            if stage_callback and new_constraints:
                partial_ctx = GenerationContext(
                    task_code=task_code,
                    task_file_name=task_file_name,
                    dataset_path=str(dataset_path),
                    dataset_profile=dataset_profile,
                    task_description=task_description,
                    accessed_columns=accessed_columns,
                    data_flow_map=data_flow_map,
                    assumptions=assumptions,
                    constraints=list(accumulated_constraints),
                )
                stage_callback("constraint_item", partial_ctx)

        constraints = self._constraint_generator.generate_parallel(
            assumptions=assumptions,
            code_script=task_code,
            accessed_columns=accessed_columns,
            task_description=task_description,
            max_workers=self._max_parallel_llm_calls,
            item_done_callback=on_constraint_progress,
            item_result_callback=on_constraint_result,
        )

        # Warn if some assumptions produced no constraints
        if len(constraints) == 0 and n_assumptions > 0:
            gen_warnings.append("Constraint generation produced no results despite valid assumptions.")
        elif n_assumptions > 0 and len(constraints) < n_assumptions:
            gen_warnings.append(
                f"Some assumptions ({n_assumptions - len(constraints)} of {n_assumptions}) "
                f"failed to generate constraints."
            )

        # Snapshot total cost after constraint generation
        report_progress(0.90, "Calculating costs...")
        llm_cost = self._calculate_llm_cost()

        cost_breakdown = {
            "column_detection": max(0.0, cost_after_detection),
            "data_flow_detection": max(0.0, cost_after_data_flow - cost_after_detection),
            "assumption_extraction": max(0.0, cost_after_assumptions - cost_after_data_flow),
            "constraint_generation": max(0.0, llm_cost - cost_after_assumptions),
        }

        if llm_cost > 0:
            logger.info(
                f"💰 LLM API cost: ${llm_cost:.6f} "
                f"(detection=${cost_breakdown['column_detection']:.6f}, "
                f"data_flow=${cost_breakdown['data_flow_detection']:.6f}, "
                f"assumptions=${cost_breakdown['assumption_extraction']:.6f}, "
                f"constraints=${cost_breakdown['constraint_generation']:.6f})"
            )

        report_progress(1.0, "Complete!")

        # Return complete context
        return GenerationContext(
            task_code=task_code,
            task_file_name=task_file_name,
            dataset_path=str(dataset_path),
            dataset_profile=dataset_profile,
            task_description=task_description,
            accessed_columns=accessed_columns,
            data_flow_map=data_flow_map,
            assumptions=assumptions,
            constraints=constraints,
            llm_cost=llm_cost,
            cost_breakdown=cost_breakdown,
            warnings=gen_warnings,
        )
