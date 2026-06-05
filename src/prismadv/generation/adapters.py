"""Adapters to convert internal IR to API schemas."""

from __future__ import annotations

from prismadv.api.v1.schemas import (
    Assumption,
    AssumptionItem,
    CodeAnnotation,
    Constraint,
    ConstraintCode,
    ConstraintType,
    ColumnType,
    CostBreakdown,
    GenerationResult,
    GenerationStatistics,
)
from prismadv.generation.flow_graph_builder import FlowGraphBuilder
from prismadv.generation.orchestrator import GenerationContext
from prismadv.ir import AssumptionIR, ConstraintIR


def _parse_constraint_type(raw: str | None) -> ConstraintType:
    """Normalise a constraint type string that may contain pipe-separated alternatives.

    The LLM occasionally returns the format hint verbatim (e.g. 'completeness|enum|relationship').
    We pick the first token that maps to a valid ConstraintType, falling back to COMPLETENESS.
    """
    if not raw:
        return ConstraintType.COMPLETENESS
    for token in raw.split("|"):
        token = token.strip()
        try:
            return ConstraintType(token)
        except ValueError:
            continue
    return ConstraintType.COMPLETENESS


def assumption_ir_to_api(assumption_ir: AssumptionIR) -> Assumption:
    """Convert AssumptionIR to API Assumption schema.

    Args:
        assumption_ir: Internal assumption representation

    Returns:
        API-compatible Assumption object
    """
    # Extract source lines from sources
    source_lines = [span.start_line for span in assumption_ir.sources]
    source_file = assumption_ir.sources[0].file if assumption_ir.sources else ""

    return Assumption(
        text=assumption_ir.text,
        source_code_lines=source_lines,
        source_file=source_file,
    )


def merge_assumptions(assumptions: list[AssumptionIR]) -> Assumption:
    """Merge multiple AssumptionIR instances into a single API Assumption.

    Combines texts and merges source lines.

    Args:
        assumptions: List of AssumptionIR to merge

    Returns:
        Merged API Assumption
    """
    if not assumptions:
        return Assumption(
            text="No assumption found",
            source_code_lines=[],
            source_file="",
        )

    if len(assumptions) == 1:
        return assumption_ir_to_api(assumptions[0])

    # Merge multiple assumptions
    # Filter out empty texts for safety
    texts = [a.text for a in assumptions if a.text]
    merged_text = " AND ".join(texts) if texts else "Multiple assumptions"

    # Collect all source lines and files
    all_lines = []
    all_files = set()
    for a in assumptions:
        for span in a.sources:
            all_lines.append(span.start_line)
            all_files.add(span.file)

    # Sort and deduplicate lines
    unique_lines = sorted(set(all_lines))
    source_file = ", ".join(sorted(all_files)) if all_files else ""

    return Assumption(
        text=merged_text,
        source_code_lines=unique_lines,
        source_file=source_file,
    )


def constraint_ir_to_api(
    constraint_ir: ConstraintIR,
    assumptions: list[AssumptionIR],
) -> Constraint:
    """Convert ConstraintIR to API Constraint schema.

    Args:
        constraint_ir: Internal constraint representation
        assumptions: Related assumptions (supports many-to-many)

    Returns:
        API-compatible Constraint object
    """
    # Convert code specs to strings
    gx_code = ""
    if constraint_ir.code_gx:
        # GX code is already in method call format
        gx_code = constraint_ir.code_gx.type + "("
        # Add kwargs
        kwargs = constraint_ir.code_gx.kwargs
        gx_code += ", ".join(f"{k}={repr(v)}" for k, v in kwargs.items())
        gx_code += ")"
    elif constraint_ir.raw_gx_code:
        # Fallback: use raw LLM output when parsing failed
        gx_code = constraint_ir.raw_gx_code

    deequ_code = ""
    if constraint_ir.code_deequ:
        # Deequ code needs to be converted to string format
        deequ_code = constraint_ir.code_deequ.to_string()
    elif constraint_ir.raw_deequ_code:
        # Fallback: use raw LLM output when parsing failed
        deequ_code = constraint_ir.raw_deequ_code

    return Constraint(
        id=constraint_ir.id,
        column=constraint_ir.column,
        type=_parse_constraint_type(constraint_ir.type),
        column_type=ColumnType(constraint_ir.column_type) if constraint_ir.column_type else ColumnType.TEXTUAL,
        label=constraint_ir.label or f"{constraint_ir.column} ({constraint_ir.type})",
        enabled=constraint_ir.enabled,
        code=ConstraintCode(
            great_expectations=gx_code,
            deequ=deequ_code,
        ),
        assumption=merge_assumptions(assumptions),
        assumption_id=assumptions[0].id if assumptions else None,
        data_stats=constraint_ir.data_stats or {},
    )


def extract_code_annotations(
    constraints: list[ConstraintIR],
    assumptions_map: dict[str, AssumptionIR],
) -> list[CodeAnnotation]:
    """Extract code annotations from constraints.

    Args:
        constraints: List of constraints
        assumptions_map: Map of assumption_id to AssumptionIR

    Returns:
        List of code annotations for the editor
    """
    annotations: list[CodeAnnotation] = []

    for constraint in constraints:
        # Get all related assumptions (support many-to-many)
        related_assumptions = [
            assumptions_map[aid] for aid in constraint.assumption_ids if aid in assumptions_map
        ]
        if not related_assumptions:
            continue

        # Create annotations for each assumption's source lines
        for assumption in related_assumptions:
            if not assumption.sources:
                continue

            for source in assumption.sources:
                annotation = CodeAnnotation(
                    line_number=source.start_line,
                    type=_parse_constraint_type(constraint.type),
                    column_type=ColumnType(constraint.column_type) if constraint.column_type else ColumnType.TEXTUAL,
                    column=constraint.column,
                    constraint_ids=[constraint.id],
                    highlight=True,
                )
                annotations.append(annotation)

    return annotations


def generation_context_to_api(context: GenerationContext) -> GenerationResult:
    """Convert GenerationContext to API GenerationResult schema.

    This is the main adapter that converts the rich internal IR
    to the frontend-compatible API format.

    Args:
        context: Complete generation context with all IR objects

    Returns:
        API-compatible GenerationResult
    """
    # Build assumptions map for lookup
    assumptions_map = {a.id: a for a in context.assumptions}

    # Filter constraints that have valid assumptions and convert to API format
    # Keep both IR and API versions for consistency across flow graph, annotations, and API response
    valid_constraint_irs: list[ConstraintIR] = []
    api_constraints: list[Constraint] = []

    for constraint_ir in context.constraints:
        # Get all related assumptions (support many-to-many)
        related_assumptions = [
            assumptions_map[aid] for aid in constraint_ir.assumption_ids if aid in assumptions_map
        ]
        if not related_assumptions:
            continue  # Skip constraints without assumptions

        # Keep the IR version for flow graph and annotations
        valid_constraint_irs.append(constraint_ir)

        # Convert to API format
        api_constraint = constraint_ir_to_api(constraint_ir, related_assumptions)
        api_constraints.append(api_constraint)

    # Build flow graph using only valid constraints
    flow_graph_builder = FlowGraphBuilder()
    column_types = {
        col.name: col.inferred_type
        for col in context.dataset_profile.dataset.columns
    }
    flow_graph = flow_graph_builder.build(
        columns=context.accessed_columns,
        column_types=column_types,
        assumptions=context.assumptions,
        constraints=valid_constraint_irs,  # Use filtered constraints
        code_file_name=context.task_file_name,
    )

    # Extract code annotations
    if valid_constraint_irs:
        # Use constraint-based annotations when constraints exist
        code_annotations = extract_code_annotations(valid_constraint_irs, assumptions_map)
    elif context.assumptions:
        # Use assumption source spans when we have assumptions but no constraints yet
        code_annotations = []
        for assumption in context.assumptions:
            primary_col = assumption.columns[0] if assumption.columns else ""
            col_type = column_types.get(primary_col, "textual") if primary_col else "textual"
            for source in assumption.sources:
                code_annotations.append(CodeAnnotation(
                    line_number=source.start_line,
                    type=ConstraintType.FORMAT,
                    column_type=ColumnType(col_type),
                    column=primary_col,
                    constraint_ids=[],
                    highlight=True,
                ))
    elif context.data_flow_map:
        # Use data flow map when we only have column access info
        code_annotations = []
        for col, sources in context.data_flow_map.items():
            col_type = column_types.get(col, "textual")
            for source in sources:
                code_annotations.append(CodeAnnotation(
                    line_number=source.start_line,
                    type=ConstraintType.FORMAT,
                    column_type=ColumnType(col_type),
                    column=col,
                    constraint_ids=[],
                    highlight=True,
                ))
    else:
        code_annotations = []

    # Calculate statistics
    # Count unique source lines across all assumptions
    all_source_lines = set()
    for assumption in context.assumptions:
        for source in assumption.sources:
            all_source_lines.add(source.start_line)

    breakdown = context.cost_breakdown
    statistics = GenerationStatistics(
        constraint_count=len(api_constraints),
        assumption_count=len(context.assumptions),
        code_lines_covered=len(all_source_lines),
        columns_covered=len(context.accessed_columns),
        processing_time_ms=0,
        llm_cost=context.llm_cost,
        warnings=context.warnings,
        cost_breakdown=CostBreakdown(
            column_detection=breakdown.get("column_detection", 0.0),
            data_flow_detection=breakdown.get("data_flow_detection", 0.0),
            assumption_extraction=breakdown.get("assumption_extraction", 0.0),
            constraint_generation=breakdown.get("constraint_generation", 0.0),
        ),
    )

    # Build the flat assumptions list for the sidebar view.
    # For each raw AssumptionIR, collect which constraint IDs reference it.
    assumption_to_constraint_ids: dict[str, list[str]] = {a.id: [] for a in context.assumptions}
    for constraint_ir in valid_constraint_irs:
        for aid in constraint_ir.assumption_ids:
            if aid in assumption_to_constraint_ids:
                assumption_to_constraint_ids[aid].append(constraint_ir.id)

    api_assumptions: list[AssumptionItem] = []
    for assumption_ir in context.assumptions:
        source_lines = [span.start_line for span in assumption_ir.sources]
        primary_column = assumption_ir.columns[0] if assumption_ir.columns else ""
        api_assumptions.append(
            AssumptionItem(
                id=assumption_ir.id,
                text=assumption_ir.text,
                column=primary_column,
                columns=assumption_ir.columns,
                source_code_lines=source_lines,
                constraint_ids=assumption_to_constraint_ids.get(assumption_ir.id, []),
            )
        )

    return GenerationResult(
        constraints=api_constraints,
        assumptions=api_assumptions,
        flow_graph=flow_graph,
        code_annotations=code_annotations,
        statistics=statistics,
    )
