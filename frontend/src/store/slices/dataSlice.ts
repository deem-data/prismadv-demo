import { StateCreator } from 'zustand';
import type { AppState, ColumnStats, DataQualityMetrics } from '@/types';
import apiClient from '@/api';

// Module-level counter to detect stale responses from rapid column clicks
let _selectColumnSeq = 0;

export interface DataSlice {
  selectedColumn: string | null;
  columnStats: Map<string, ColumnStats>;
  dataQualityMetrics: DataQualityMetrics | null;
  deequValidationResults: Map<string, { status: 'pass' | 'fail' | 'error'; message?: string }>;
  selectColumn: (column: string | null) => void;
}

export const createDataSlice: StateCreator<
  AppState,
  [],
  [],
  DataSlice
> = (set, get) => ({
  selectedColumn: null,
  columnStats: new Map(),
  dataQualityMetrics: null,
  deequValidationResults: new Map(),

  selectColumn: async (column: string | null) => {
    // Clear assumption selection to avoid conflicting highlights
    set({ selectedColumn: column, selectedAssumptionId: null });

    // Clear code + flow graph highlights when deselecting
    if (!column) {
      set({ highlightedLines: [], highlightedNodes: [] });
      return;
    }

    // Compute highlighted code lines from assumptions for this column
    const assumptions = get().assumptions;
    const columnLines = new Set<number>();
    for (const a of assumptions) {
      if (a.column === column || a.columns.includes(column)) {
        for (const line of a.sourceCodeLines) {
          columnLines.add(line);
        }
      }
    }

    // Fall back to raw code annotations (available after data flow detection, before assumptions)
    // The annotations Map merges entries per line, so use rawAnnotations which preserves all entries
    if (columnLines.size === 0) {
      const rawAnnotations = get().rawAnnotations;
      for (const ann of rawAnnotations) {
        if (ann.column === column) {
          columnLines.add(ann.lineNumber);
        }
      }
    }

    set({ highlightedLines: Array.from(columnLines).sort((a, b) => a - b) });

    // Highlight the column node + its descendants in the flow graph
    const flowGraph = get().flowGraph;
    if (flowGraph) {
      const columnNode = flowGraph.nodes.find(
        (n) => n.type === 'data' && n.label === column
      );
      if (columnNode) {
        const connected = [columnNode.id];
        const edges = flowGraph.edges;
        const findDescendants = (nodeId: string) => {
          edges.forEach((edge) => {
            if (edge.source === nodeId && !connected.includes(edge.target)) {
              connected.push(edge.target);
              findDescendants(edge.target);
            }
          });
        };
        findDescendants(columnNode.id);
        set({ highlightedNodes: connected });
      } else {
        set({ highlightedNodes: [] });
      }
    }

    // Fetch column stats if needed
    if (get().dataset) {
      const seq = ++_selectColumnSeq;
      const datasetId = get().dataset!.id;

      if (!get().columnStats.has(column)) {
        try {
          const response = await apiClient.getColumnStats(datasetId, column);
          if (seq !== _selectColumnSeq) return;
          set((state) => {
            const newStats = new Map(state.columnStats);
            newStats.set(column, response.stats);
            return { columnStats: newStats };
          });
        } catch (error) {
          if (seq !== _selectColumnSeq) return;
          get().addToast({
            type: 'error',
            message: `Failed to load column stats: ${error instanceof Error ? error.message : 'Unknown error'}`,
          });
        }
      }
    }
  },
});
