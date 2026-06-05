import { StateCreator } from 'zustand';
import type { AppState, AssumptionItem } from '@/types';
import apiClient from '@/api';

export interface AssumptionsSlice {
  assumptions: AssumptionItem[];
  selectedAssumptionId: string | null;
  generatingAssumptionId: string | null;
  selectAssumption: (id: string | null) => void;
  updateAssumptionText: (id: string, text: string) => void;
  addAssumption: (assumption: AssumptionItem) => void;
  deleteAssumption: (id: string) => void;
  generateConstraintsFromAssumption: (assumptionId: string) => Promise<void>;
  sidebarTab: 'constraints' | 'assumptions';
  setSidebarTab: (tab: 'constraints' | 'assumptions') => void;
}

export const createAssumptionsSlice: StateCreator<
  AppState,
  [],
  [],
  AssumptionsSlice
> = (set, get) => ({
  assumptions: [],
  selectedAssumptionId: null,
  generatingAssumptionId: null,
  sidebarTab: 'assumptions',
  setSidebarTab: (tab) => set({ sidebarTab: tab }),

  selectAssumption: (id: string | null) => {
    set({ selectedAssumptionId: id, sidebarTab: 'assumptions' });

    if (!id) {
      set({ highlightedLines: [], highlightedNodes: [] });
      return;
    }

    const assumption = get().assumptions.find((a) => a.id === id);
    if (assumption) {
      set({ highlightedLines: assumption.sourceCodeLines });
    }

    // Highlight connected nodes in the flow graph
    const flowGraph = get().flowGraph;
    if (flowGraph) {
      const assumptionNodeId = `assumption-${id}`;
      const assumptionNode = flowGraph.nodes.find((n) => n.id === assumptionNodeId);
      if (assumptionNode) {
        const connectedNodes = [assumptionNode.id];
        const edges = flowGraph.edges;
        const findAncestors = (nodeId: string) => {
          edges.forEach((edge) => {
            if (edge.target === nodeId && !connectedNodes.includes(edge.source)) {
              connectedNodes.push(edge.source);
              findAncestors(edge.source);
            }
          });
        };
        findAncestors(assumptionNode.id);
        set({ highlightedNodes: connectedNodes });
      }
    }
  },

  updateAssumptionText: (id: string, text: string) => {
    set((state) => ({
      assumptions: state.assumptions.map((a) =>
        a.id === id ? { ...a, text } : a
      ),
      // Mark constraints as out of sync — user should re-run inference
      // if they want constraints regenerated from the new wording.
      constraintsSynced: false,
    }));
  },

  addAssumption: (assumption: AssumptionItem) => {
    set((state) => ({ assumptions: [...state.assumptions, assumption] }));
  },

  deleteAssumption: (id: string) => {
    const { selectedAssumptionId, flowGraph } = get();
    const assumptionNodeId = `assumption-${id}`;

    // Remove assumption node and its edges from the flow graph
    const updatedFlowGraph = flowGraph ? {
      nodes: flowGraph.nodes.filter((n) => n.id !== assumptionNodeId),
      edges: flowGraph.edges.filter((e) =>
        e.source !== assumptionNodeId && e.target !== assumptionNodeId
      ),
    } : null;

    set((state) => ({
      assumptions: state.assumptions.filter((a) => a.id !== id),
      selectedAssumptionId: selectedAssumptionId === id ? null : selectedAssumptionId,
      highlightedLines: selectedAssumptionId === id ? [] : state.highlightedLines,
      highlightedNodes: selectedAssumptionId === id ? [] : state.highlightedNodes,
      flowGraph: updatedFlowGraph,
    }));
  },

  generateConstraintsFromAssumption: async (assumptionId: string) => {
    const { taskFile, dataset, llmSettings, constraints, addConstraint, addToast } = get();
    const assumption = get().assumptions.find((a) => a.id === assumptionId);
    if (!taskFile || !dataset || !assumption) return;

    set({ generatingAssumptionId: assumptionId });
    try {
      const options: Record<string, unknown> = { model: llmSettings.model };
      if (llmSettings.useOwnKey && llmSettings.apiKey) {
        options.apiKey = llmSettings.apiKey;
      }

      const linkedConstraints = constraints.filter((c) =>
        assumption.constraintIds.includes(c.id)
      );
      const existingConstraints = linkedConstraints.length > 0
        ? linkedConstraints.map((c) => ({
            greatExpectations: c.code.greatExpectations,
            deequ: c.code.deequ,
          }))
        : undefined;

      const result = await apiClient.generateFromAssumption({
        assumptionText: assumption.text,
        column: assumption.column,
        taskFileId: taskFile.id,
        datasetId: dataset.id,
        options,
        existingConstraints,
      });

      const newIds: string[] = [];
      for (const c of result.constraints) {
        addConstraint(c);
        newIds.push(c.id);
      }

      if (newIds.length > 0) {
        // Update assumption's constraintIds + add nodes/edges to flow graph
        // We use the store's assumptionId (not the backend's temp one) for correct edges
        const assumptionNodeId = `assumption-${assumptionId}`;
        set((state) => {
          const updatedFlowGraph = state.flowGraph ? {
            nodes: [
              ...state.flowGraph.nodes,
              ...result.constraints.map((c) => ({
                id: `constraint-${c.id}`,
                type: 'constraint' as const,
                label: c.label,
                columnType: c.columnType,
                constraintId: c.id,
                position: { x: 0, y: 0 },
              })),
            ],
            edges: [
              ...state.flowGraph.edges,
              ...result.constraints.map((c) => ({
                id: `e-${assumptionId}-${c.id}`,
                source: assumptionNodeId,
                target: `constraint-${c.id}`,
              })),
            ],
          } : null;

          return {
            assumptions: state.assumptions.map((a) =>
              a.id === assumptionId
                ? { ...a, constraintIds: [...a.constraintIds, ...newIds] }
                : a
            ),
            flowGraph: updatedFlowGraph,
          };
        });
      }

      if (result.message && result.constraints.length === 0) {
        addToast({ type: 'info', message: result.message });
      } else if (result.message) {
        addToast({ type: 'success', message: result.message });
      } else {
        addToast({ type: 'success', message: `Generated ${result.constraints.length} constraint${result.constraints.length !== 1 ? 's' : ''}` });
      }
    } catch (error) {
      addToast({ type: 'error', message: `Failed to generate constraints: ${error instanceof Error ? error.message : 'Unknown error'}` });
    } finally {
      set({ generatingAssumptionId: null });
    }
  },
});
