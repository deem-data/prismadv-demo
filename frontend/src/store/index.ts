import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { AppState } from '@/types';
import { createFilesSlice } from './slices/filesSlice';
import { createConstraintsSlice } from './slices/constraintsSlice';
import { createCodeEditorSlice } from './slices/codeEditorSlice';
import { createFlowGraphSlice } from './slices/flowGraphSlice';
import { createDataSlice } from './slices/dataSlice';
import { createUISlice } from './slices/uiSlice';
import { createExecutionSlice } from './slices/executionSlice';
import { createToastsSlice } from './slices/toastsSlice';
import { createLLMSlice } from './slices/llmSlice';
import { createPreferencesSlice } from './slices/preferencesSlice';
import { createOptimizationSlice } from './slices/optimizationSlice';
import { createAssumptionsSlice } from './slices/assumptionsSlice';
import { createDeequSlice } from './slices/deequSlice';

/**
 * PrismaDV App Store
 *
 * Combines all state slices into a single Zustand store:
 * - Files: taskFile, dataset
 * - Constraints: constraints, selection
 * - Code Editor: code, highlights, annotations
 * - Flow Graph: nodes, edges, selection
 * - Data: column stats, data quality
 * - UI: panel visibility, collapse states
 * - Execution: generation progress
 * - Toasts: notifications
 */
export const useAppStore = create<AppState>()(
  devtools(
    (...args) => ({
      ...createFilesSlice(...args),
      ...createConstraintsSlice(...args),
      ...createCodeEditorSlice(...args),
      ...createFlowGraphSlice(...args),
      ...createDataSlice(...args),
      ...createUISlice(...args),
      ...createExecutionSlice(...args),
      ...createToastsSlice(...args),
      ...createLLMSlice(...args),
      ...createPreferencesSlice(...args),
      ...createOptimizationSlice(...args),
      ...createAssumptionsSlice(...args),
      ...createDeequSlice(...args),
    }),
    { name: 'PrismaDV Store' }
  )
);

// Selectors for common state access patterns
export const selectTaskFile = (state: AppState) => state.taskFile;
export const selectDataset = (state: AppState) => state.dataset;
export const selectConstraints = (state: AppState) => state.constraints;
export const selectSelectedConstraint = (state: AppState) =>
  state.constraints.find((c) => c.id === state.selectedConstraintId);
export const selectEnabledConstraints = (state: AppState) =>
  state.constraints.filter((c) => c.enabled);
export const selectFlowGraph = (state: AppState) => state.flowGraph;
export const selectUIState = (state: AppState) => state.ui;
export const selectIsGenerating = (state: AppState) => state.isGenerating;

export default useAppStore;
