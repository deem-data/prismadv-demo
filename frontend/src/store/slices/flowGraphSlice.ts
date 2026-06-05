import { StateCreator } from 'zustand';
import type { AppState, FlowGraphData } from '@/types';

export interface FlowGraphSlice {
  flowGraph: FlowGraphData | null;
  highlightedNodes: string[];
}

export const createFlowGraphSlice: StateCreator<
  AppState,
  [],
  [],
  FlowGraphSlice
> = () => ({
  flowGraph: null,
  highlightedNodes: [],
});
