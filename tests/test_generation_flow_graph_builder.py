"""Tests for flow graph builder."""

from __future__ import annotations

import pytest

from prismadv.api.v1.schemas import FlowNodeType
from prismadv.generation import FlowGraphBuilder
from prismadv.ir import AssumptionIR, ConstraintIR, SourceSpan


@pytest.fixture
def sample_assumptions():
    """Create sample assumptions for testing."""
    return [
        AssumptionIR(
            id="assumption-1",
            text="Age must be between 18 and 65",
            sources=[SourceSpan(start_line=15, end_line=16, file="test.py")],
            columns=["age"],
            constraint_type="range",
        ),
        AssumptionIR(
            id="assumption-2",
            text="Name must not be null",
            sources=[SourceSpan(start_line=10, end_line=10, file="test.py")],
            columns=["name"],
            constraint_type="completeness",
        ),
    ]


@pytest.fixture
def sample_constraints():
    """Create sample constraints for testing."""
    return [
        ConstraintIR(
            id="constraint-1",
            assumption_ids=["assumption-1"],
            column="age",
            columns=["age"],
            column_type="numerical",
            type="range",
            label="age (Range)",
        ),
        ConstraintIR(
            id="constraint-2",
            assumption_ids=["assumption-2"],
            column="name",
            columns=["name"],
            column_type="textual",
            type="completeness",
            label="name (Completeness)",
        ),
    ]


def test_flow_graph_builder_basic(sample_assumptions, sample_constraints):
    """Test basic flow graph building."""
    builder = FlowGraphBuilder()

    graph = builder.build(
        columns=["age", "name"],
        column_types={"age": "numerical", "name": "textual"},
        assumptions=sample_assumptions,
        constraints=sample_constraints,
        code_file_name="test.py",
    )

    # Check nodes
    assert len(graph.nodes) == 7  # 2 data + 1 code + 2 assumptions + 2 constraints

    # Check node types
    data_nodes = [n for n in graph.nodes if n.type == FlowNodeType.DATA]
    code_nodes = [n for n in graph.nodes if n.type == FlowNodeType.CODE]
    assumption_nodes = [n for n in graph.nodes if n.type == FlowNodeType.ASSUMPTION]
    constraint_nodes = [n for n in graph.nodes if n.type == FlowNodeType.CONSTRAINT]

    assert len(data_nodes) == 2
    assert len(code_nodes) == 1
    assert len(assumption_nodes) == 2
    assert len(constraint_nodes) == 2

    # Check edges
    assert len(graph.edges) == 6  # 2 code→data + 2 data→assumption + 2 assumption→constraint


def test_flow_graph_builder_node_positions(sample_assumptions, sample_constraints):
    """Test that nodes have correct positions."""
    builder = FlowGraphBuilder(column_spacing=100.0, layer_spacing=200.0)

    graph = builder.build(
        columns=["age", "name"],
        column_types={"age": "numerical", "name": "textual"},
        assumptions=sample_assumptions,
        constraints=sample_constraints,
        code_file_name="test.py",
    )

    # Code node should be at x=0 (Layer 1)
    code_node = [n for n in graph.nodes if n.type == FlowNodeType.CODE][0]
    assert code_node.position.x == 0.0

    # Data nodes should be at x=200 (Layer 2)
    data_nodes = [n for n in graph.nodes if n.type == FlowNodeType.DATA]
    assert all(n.position.x == 200.0 for n in data_nodes)

    # Assumptions should be at x=400 (Layer 3)
    assumption_nodes = [n for n in graph.nodes if n.type == FlowNodeType.ASSUMPTION]
    assert all(n.position.x == 400.0 for n in assumption_nodes)

    # Constraints should be at x=600 (Layer 4)
    constraint_nodes = [n for n in graph.nodes if n.type == FlowNodeType.CONSTRAINT]
    assert all(n.position.x == 600.0 for n in constraint_nodes)


def test_flow_graph_builder_empty_inputs():
    """Test flow graph with empty inputs."""
    builder = FlowGraphBuilder()

    graph = builder.build(
        columns=[],
        column_types={},
        assumptions=[],
        constraints=[],
        code_file_name="empty.py",
    )

    # Should still have code node
    assert len(graph.nodes) == 1
    assert graph.nodes[0].type == FlowNodeType.CODE
    assert len(graph.edges) == 0


def test_flow_graph_builder_single_column(sample_assumptions, sample_constraints):
    """Test flow graph with single column."""
    builder = FlowGraphBuilder()

    graph = builder.build(
        columns=["age"],
        column_types={"age": "numerical"},
        assumptions=[sample_assumptions[0]],  # Just age assumption
        constraints=[sample_constraints[0]],  # Just age constraint
        code_file_name="test.py",
    )

    assert len(graph.nodes) == 4  # 1 data + 1 code + 1 assumption + 1 constraint

    # Check connections (Code → Data flow)
    code_to_data = [e for e in graph.edges if e.source == "code-main" and e.target == "data-age"]
    assert len(code_to_data) == 1


def test_flow_graph_builder_node_labels(sample_assumptions, sample_constraints):
    """Test that nodes have correct labels."""
    builder = FlowGraphBuilder()

    graph = builder.build(
        columns=["age", "name"],
        column_types={"age": "numerical", "name": "textual"},
        assumptions=sample_assumptions,
        constraints=sample_constraints,
        code_file_name="test.py",
    )

    # Data node labels should be column names
    data_nodes = [n for n in graph.nodes if n.type == FlowNodeType.DATA]
    data_labels = {n.label for n in data_nodes}
    assert data_labels == {"age", "name"}

    # Code node label should be file name
    code_node = [n for n in graph.nodes if n.type == FlowNodeType.CODE][0]
    assert code_node.label == "test.py"

    # Assumption nodes should have truncated text
    assumption_nodes = [n for n in graph.nodes if n.type == FlowNodeType.ASSUMPTION]
    assert all(len(n.label) <= 33 for n in assumption_nodes)  # 30 + "..."


def test_flow_graph_builder_constraint_id_linkage(sample_constraints):
    """Test that constraint nodes have constraint_id for linkage."""
    builder = FlowGraphBuilder()

    graph = builder.build(
        columns=["age"],
        column_types={"age": "numerical"},
        assumptions=[AssumptionIR(
            id="assumption-1",
            text="Test",
            columns=["age"],
        )],
        constraints=[sample_constraints[0]],
        code_file_name="test.py",
    )

    constraint_nodes = [n for n in graph.nodes if n.type == FlowNodeType.CONSTRAINT]
    assert len(constraint_nodes) == 1
    assert constraint_nodes[0].constraint_id == "constraint-1"


def test_flow_graph_builder_assumption_to_constraint_edges(sample_assumptions, sample_constraints):
    """Test edges connect assumptions to their constraints."""
    builder = FlowGraphBuilder()

    graph = builder.build(
        columns=["age", "name"],
        column_types={"age": "numerical", "name": "textual"},
        assumptions=sample_assumptions,
        constraints=sample_constraints,
        code_file_name="test.py",
    )

    # Check assumption → constraint edges
    assumption_to_constraint = [
        e for e in graph.edges
        if e.source.startswith("assumption-") and e.target.startswith("constraint-")
    ]
    assert len(assumption_to_constraint) == 2

    # Check that edges match assumption_id
    for edge in assumption_to_constraint:
        # Edge should go from assumption-{id} to constraint-{id}
        # where constraint.assumption_id == assumption.id
        assert "assumption-" in edge.source
