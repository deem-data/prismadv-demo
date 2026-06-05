import React, { useCallback, useEffect, useMemo, useRef } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node as ReactFlowNode,
  useNodesState,
  useEdgesState,
  MarkerType,
  ReactFlowInstance
} from 'reactflow';
import dagre from 'dagre';
import 'reactflow/dist/style.css';
import { FlowGraphData } from '@/types';
import { useAppStore } from '@/store';

// Custom Nodes
import DataNode from './nodes/DataNode';
import CodeNode from './nodes/CodeNode';
import AssumptionNode from './nodes/AssumptionNode';
import ConstraintNode from './nodes/ConstraintNode';

interface FlowGraphProps {
  data: FlowGraphData | null;
}

const nodeTypes = {
  data: DataNode,
  code: CodeNode,
  assumption: AssumptionNode,
  constraint: ConstraintNode,
};

// Fixed dimensions per node type for Dagre layout calculation
const NODE_DIMENSIONS: Record<string, { width: number; height: number }> = {
  code:        { width: 160, height: 50 },
  data:        { width: 160, height: 50 },
  assumption:  { width: 210, height: 60 },
  constraint:  { width: 210, height: 60 },
};
const DEFAULT_DIM = { width: 180, height: 50 };

function applyDagreLayout(
  nodes: ReactFlowNode[],
  edges: { source: string; target: string }[],
): ReactFlowNode[] {
  if (nodes.length === 0) return nodes;

  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: 'LR', ranksep: 80, nodesep: 40 });

  nodes.forEach(node => {
    const dim = NODE_DIMENSIONS[node.type ?? ''] ?? DEFAULT_DIM;
    g.setNode(node.id, { width: dim.width, height: dim.height });
  });

  edges.forEach(edge => g.setEdge(edge.source, edge.target));

  dagre.layout(g);

  return nodes.map(node => {
    const { x, y } = g.node(node.id);
    const dim = NODE_DIMENSIONS[node.type ?? ''] ?? DEFAULT_DIM;
    return {
      ...node,
      position: {
        x: x - dim.width / 2,
        y: y - dim.height / 2,
      },
    };
  });
}

const FlowGraph: React.FC<FlowGraphProps> = ({ data }) => {
  const { highlightedNodes, selectConstraint, selectAssumption, selectColumn, deleteAssumption, deleteConstraint } = useAppStore();
  const reactFlowInstanceRef = useRef<ReactFlowInstance | null>(null);
  const prevNodeCountRef = useRef(0);
  const prevNodeIdsRef = useRef<Set<string>>(new Set());
  const accentTextual = 'rgb(var(--color-accent-textual))';
  const accentCategorical = 'rgb(var(--color-accent-categorical))';
  const accentNumerical = 'rgb(var(--color-accent-numerical))';
  const accentPurple = 'rgb(var(--color-accent-purple))';
  const borderColor = 'rgb(var(--color-dark-border))';
  const mutedColor = 'rgb(var(--color-text-muted))';
  const miniMapNodeColor = 'rgb(var(--color-dark-light))';
  const miniMapMaskColor = 'rgba(0, 0, 0, 0.2)';

  const initialNodes: ReactFlowNode[] = useMemo(() => {
    if (!data?.nodes) return [];
    return data.nodes
      .filter(node => node.id && node.id !== 'undefined')
      .map(node => ({
        id: node.id,
        type: node.type,
        position: node.position, // overridden by Dagre in useEffect
        data: {
          label: node.label,
          originalType: node.type,
          columnType: node.columnType,
          constraintId: node.constraintId,
          assumptionId: node.assumptionId,
        },
      }));
  }, [data]);

  const initialEdges = useMemo(() => {
    return (data?.edges ?? []).filter(
      edge =>
        edge.source &&
        edge.target &&
        edge.source !== 'undefined' &&
        edge.target !== 'undefined',
    );
  }, [data]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    const newIds = new Set(initialNodes.map((n) => n.id));
    const prevIds = prevNodeIdsRef.current;
    const hasNewNodes = initialNodes.some((n) => !prevIds.has(n.id));

    if (prevIds.size > 0 && !hasNewNodes) {
      // Only removals — keep existing positions, just filter out removed nodes/edges
      setNodes((cur) => cur.filter((n) => newIds.has(n.id)));
      setEdges(initialEdges);
    } else {
      // New nodes added (or first render) — run full Dagre layout
      const layouted = applyDagreLayout(initialNodes, initialEdges);
      setNodes(layouted);
      setEdges(initialEdges);

      if (layouted.length > 0 && prevNodeCountRef.current === 0) {
        requestAnimationFrame(() => {
          reactFlowInstanceRef.current?.fitView({ padding: 0.2, duration: 250 });
        });
      }
    }

    prevNodeCountRef.current = initialNodes.length;
    prevNodeIdsRef.current = newIds;
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  const onNodesDelete = useCallback((deleted: ReactFlowNode[]) => {
    for (const node of deleted) {
      if (node.data?.assumptionId) {
        deleteAssumption(node.data.assumptionId);
      } else if (node.data?.constraintId) {
        deleteConstraint(node.data.constraintId);
      }
    }
  }, [deleteAssumption, deleteConstraint]);

  const onNodeClick = useCallback((_: React.MouseEvent, node: ReactFlowNode) => {
    if (node.data?.constraintId) {
      selectConstraint(node.data.constraintId);
    } else if (node.data?.assumptionId) {
      selectAssumption(node.data.assumptionId);
    } else if (node.data?.originalType === 'data') {
      selectColumn(node.data.label);
    }
  }, [selectConstraint, selectAssumption, selectColumn]);

  if (!data || data.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-text-muted text-sm">
        No graph data available. Upload task file and dataset to generate.
      </div>
    );
  }

  const highlightedNodesMap = new Set(highlightedNodes);
  const nodesWithHighlight = nodes.map(node => ({
    ...node,
    data: {
      ...node.data,
      highlighted: highlightedNodesMap.has(node.id),
    },
    style: {
      ...node.style,
      opacity: highlightedNodesMap.size > 0 && !highlightedNodesMap.has(node.id) ? 0.3 : 1,
    },
  }));

  const edgesWithHighlight = edges.map(edge => ({
    ...edge,
    animated: true,
    style: {
      ...edge.style,
      opacity:
        highlightedNodesMap.size > 0 &&
        !highlightedNodesMap.has(edge.source) &&
        !highlightedNodesMap.has(edge.target)
          ? 0.2
          : 1,
      stroke: accentTextual,
    },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color: accentTextual,
    },
  }));

  return (
    <div className="w-full h-full bg-dark-medium min-w-0">
      <ReactFlow
        nodes={nodesWithHighlight}
        edges={edgesWithHighlight}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodesDelete={onNodesDelete}
        onNodeClick={onNodeClick}
        onInit={(instance) => {
          reactFlowInstanceRef.current = instance;
        }}
        fitView
        minZoom={0.1}
        maxZoom={1.5}
        proOptions={{ hideAttribution: true }}
      >
        <Background color={borderColor} gap={16} />
        <Controls className="react-flow__controls--dark" />
        <MiniMap
          nodeStrokeColor={(n) => {
            const type = n.data?.originalType;
            if (type === 'data') return accentTextual;
            if (type === 'constraint') return accentCategorical;
            if (type === 'assumption') return accentNumerical;
            if (type === 'code') return accentPurple;
            return mutedColor;
          }}
          nodeColor={miniMapNodeColor}
          maskColor={miniMapMaskColor}
          className="bg-dark-light border border-dark-border"
          style={{ width: 110, height: 73 }}
        />
      </ReactFlow>
    </div>
  );
};

export default FlowGraph;
