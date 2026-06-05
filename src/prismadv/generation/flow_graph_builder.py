"""Flow graph builder for constraint generation provenance visualization."""

from __future__ import annotations

from typing import Sequence

from prismadv.api.v1.schemas import (
    ColumnType,
    FlowEdge,
    FlowGraphData,
    FlowNode,
    FlowNodeType,
    Position,
)
from prismadv.ir import AssumptionIR, ConstraintIR


class FlowGraphBuilder:
    """Build flow graph visualization from constraint generation results.

    The flow graph shows the provenance chain:
    Code → Data Columns → Assumptions → Constraints
    """

    def __init__(
        self,
        *,
        column_spacing: float = 100.0,
        layer_spacing: float = 200.0,
    ):
        """Initialize the builder with layout parameters.

        Args:
            column_spacing: Vertical spacing between nodes in same column
            layer_spacing: Horizontal spacing between layers (data/code/assumption/constraint)
        """
        self.column_spacing = column_spacing
        self.layer_spacing = layer_spacing

    def build(
        self,
        *,
        columns: Sequence[str],
        column_types: dict[str, str],  # column name -> "textual"|"numerical"|"categorical"
        assumptions: Sequence[AssumptionIR],
        constraints: Sequence[ConstraintIR],
        code_file_name: str,
    ) -> FlowGraphData:
        """Build flow graph from IR objects.

        Args:
            columns: Dataset columns that were accessed
            column_types: Mapping of column names to their types
            assumptions: Extracted assumptions
            constraints: Generated constraints
            code_file_name: Name of the code file

        Returns:
            FlowGraphData with nodes and edges
        """
        nodes: list[FlowNode] = []
        edges: list[FlowEdge] = []

        # Layer 1: Code node (centered vertically)
        x_code = 0.0
        y_code_center = (len(columns) - 1) * self.column_spacing / 2 if columns else 0
        nodes.append(FlowNode(
            id="code-main",
            type=FlowNodeType.CODE,
            label=code_file_name,
            position=Position(x=x_code, y=y_code_center),
        ))

        # Layer 2: Data column nodes
        x_data = x_code + self.layer_spacing
        for idx, column in enumerate(columns):
            column_type = column_types.get(column, "textual")
            nodes.append(FlowNode(
                id=f"data-{column}",
                type=FlowNodeType.DATA,
                label=column,
                column_type=ColumnType(column_type),
                position=Position(x=x_data, y=idx * self.column_spacing),
            ))

        # Connect code to data columns
        for column in columns:
            edges.append(FlowEdge(
                id=f"e-code-data-{column}",
                source="code-main",
                target=f"data-{column}",
            ))

        # Layer 3: Assumption nodes
        x_assumption = x_data + self.layer_spacing
        assumption_by_column: dict[str, list[AssumptionIR]] = {}
        for assumption in assumptions:
            for col in assumption.columns:
                if col not in assumption_by_column:
                    assumption_by_column[col] = []
                assumption_by_column[col].append(assumption)

        # Position assumptions vertically based on their first column
        y_offset = 0.0
        for assumption in assumptions:
            primary_col = assumption.columns[0] if assumption.columns else None
            column_type = column_types.get(primary_col, "textual") if primary_col else "textual"

            # Create short label from assumption text
            label = assumption.text[:30] + "..." if len(assumption.text) > 30 else assumption.text

            nodes.append(FlowNode(
                id=f"assumption-{assumption.id}",
                type=FlowNodeType.ASSUMPTION,
                label=label,
                column_type=ColumnType(column_type) if primary_col else None,
                assumption_id=assumption.id,
                position=Position(x=x_assumption, y=y_offset),
            ))

            # Connect data column(s) to assumption
            for col in assumption.columns:
                edges.append(FlowEdge(
                    id=f"e-data-{col}-{assumption.id}",
                    source=f"data-{col}",
                    target=f"assumption-{assumption.id}",
                ))

            y_offset += self.column_spacing

        # Layer 4: Constraint nodes
        x_constraint = x_assumption + self.layer_spacing
        y_offset = 0.0
        for constraint in constraints:
            # Get constraint type for display
            constraint_label = constraint.label or constraint.type

            nodes.append(FlowNode(
                id=f"constraint-{constraint.id}",
                type=FlowNodeType.CONSTRAINT,
                label=constraint_label[:40] + "..." if len(constraint_label) > 40 else constraint_label,
                column_type=ColumnType(constraint.column_type) if constraint.column_type else None,
                constraint_id=constraint.id,
                position=Position(x=x_constraint, y=y_offset),
            ))

            # Connect all related assumptions to this constraint (support many-to-many)
            for assumption_id in constraint.assumption_ids:
                edges.append(FlowEdge(
                    id=f"e-assumption-{assumption_id}-{constraint.id}",
                    source=f"assumption-{assumption_id}",
                    target=f"constraint-{constraint.id}",
                ))

            y_offset += self.column_spacing

        return FlowGraphData(nodes=nodes, edges=edges)
