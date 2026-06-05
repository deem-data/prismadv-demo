import { StateCreator } from 'zustand';
import type { AppState, Constraint, ConstraintCode, ValidateConstraintResponse } from '@/types';
import apiClient from '@/api';

export interface ConstraintsSlice {
  constraints: Constraint[];
  selectedConstraintId: string | null;
  selectConstraint: (id: string | null) => void;
  toggleConstraint: (id: string, enabled: boolean) => void;
  deleteConstraint: (id: string) => void;
  updateConstraint: (id: string, patch: { label?: string; code?: ConstraintCode }) => void;
  addConstraint: (constraint: Constraint) => void;
  validateConstraint: (constraintId: string, backend: 'great_expectations' | 'deequ') => Promise<ValidateConstraintResponse | null>;
}

export const createConstraintsSlice: StateCreator<
  AppState,
  [],
  [],
  ConstraintsSlice
> = (set, get) => ({
  constraints: [],
  selectedConstraintId: null,

  selectConstraint: (id: string | null) => {
    set({ selectedConstraintId: id, ...(id ? { sidebarTab: 'constraints' as const } : {}) });

    // Highlight related code lines when constraint is selected
    if (id) {
      const constraint = get().constraints.find((c) => c.id === id);
      if (constraint) {
        const sourceLines = constraint.assumption.sourceCodeLines;
        set({ highlightedLines: sourceLines });

        // Highlight related nodes in flow graph
        const flowGraph = get().flowGraph;
        if (flowGraph) {
          const constraintNode = flowGraph.nodes.find(
            (n) => n.type === 'constraint' && n.constraintId === id
          );
          if (constraintNode) {
            // Find all connected nodes
            const connectedNodes = [constraintNode.id];
            const edges = flowGraph.edges;

            // Traverse backwards from constraint to find connected nodes
            const findConnectedNodes = (nodeId: string) => {
              edges.forEach((edge) => {
                if (edge.target === nodeId && !connectedNodes.includes(edge.source)) {
                  connectedNodes.push(edge.source);
                  findConnectedNodes(edge.source);
                }
              });
            };

            findConnectedNodes(constraintNode.id);
            set({ highlightedNodes: connectedNodes });
          }
        }
      }
    } else {
      set({ highlightedLines: [], highlightedNodes: [] });
    }
  },

  toggleConstraint: (id: string, enabled: boolean) => {
    set((state) => ({
      constraints: state.constraints.map((c) =>
        c.id === id ? { ...c, enabled } : c
      ),
    }));
  },

  deleteConstraint: (id: string) => {
    const { selectedConstraintId, flowGraph } = get();

    // Remove constraint node and its edges from the flow graph
    const updatedFlowGraph = flowGraph ? {
      nodes: flowGraph.nodes.filter((n) => !(n.type === 'constraint' && n.constraintId === id)),
      edges: flowGraph.edges.filter((e) => {
        const targetNode = flowGraph.nodes.find((n) => n.id === e.target);
        return !(targetNode?.type === 'constraint' && targetNode.constraintId === id);
      }),
    } : null;

    set((state) => ({
      constraints: state.constraints.filter((c) => c.id !== id),
      selectedConstraintId: selectedConstraintId === id ? null : selectedConstraintId,
      highlightedLines: selectedConstraintId === id ? [] : state.highlightedLines,
      highlightedNodes: selectedConstraintId === id ? [] : state.highlightedNodes,
      flowGraph: updatedFlowGraph,
    }));
  },

  updateConstraint: (id: string, patch: { label?: string; code?: ConstraintCode }) => {
    set((state) => ({
      constraints: state.constraints.map((c) =>
        c.id === id ? { ...c, ...patch } : c
      ),
    }));
  },

  addConstraint: (constraint: Constraint) => {
    set((state) => ({
      constraints: [...state.constraints, constraint],
      constraintsSynced: false,
    }));
  },

  validateConstraint: async (constraintId: string, backend: 'great_expectations' | 'deequ') => {
    const { dataset, constraints, dataQualityMetrics } = get();
    if (!dataset) return null;

    const constraint = constraints.find((c) => c.id === constraintId);
    if (!constraint) return null;

    const code = backend === 'deequ' ? constraint.code.deequ : constraint.code.greatExpectations;
    if (!code) return null;

    try {
      const result = await apiClient.validateConstraint(dataset.id, {
        constraintId: constraint.id,
        column: constraint.column,
        backend,
        greatExpectationsCode: backend === 'great_expectations' ? code : undefined,
        deequCode: backend === 'deequ' ? code : undefined,
      });

      const statusKey = result.status === 'passed' ? 'pass' as const
        : result.status === 'failed' ? 'fail' as const : 'error' as const;
      const message = result.error || result.message || '';

      if (backend === 'deequ') {
        // Store Deequ results in the dedicated map
        set((state) => {
          const newMap = new Map(state.deequValidationResults);
          newMap.set(constraintId, { status: statusKey, message });
          return { deequValidationResults: newMap };
        });
      } else {
        // Update global dataQualityMetrics for GE so constraint list stays in sync
        const violations =
          result.status === 'passed' ? 0 : result.status === 'failed' ? 1 : 2;

        if (dataQualityMetrics) {
          set({
            dataQualityMetrics: {
              ...dataQualityMetrics,
              metrics: {
                ...dataQualityMetrics.metrics,
                violationsByConstraint: {
                  ...dataQualityMetrics.metrics.violationsByConstraint,
                  [constraintId]: violations,
                },
                validationMessages: {
                  ...dataQualityMetrics.metrics.validationMessages,
                  [constraintId]: message,
                },
              },
            },
          });
        } else {
          set({
            dataQualityMetrics: {
              datasetId: dataset.id,
              metrics: {
                completeness: 0,
                validity: 0,
                constraintCount: constraints.length,
                activeConstraints: constraints.filter((c) => c.enabled).length,
                disabledConstraints: constraints.filter((c) => !c.enabled).length,
                violationCount: violations > 0 ? 1 : 0,
                violationsByConstraint: { [constraintId]: violations },
                validationMessages: { [constraintId]: message },
                overallHealth: 'warning',
              },
            },
          });
        }
      }

      return result;
    } catch (error) {
      get().addToast({
        type: 'error',
        message: `Validation failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
      return null;
    }
  },
});
