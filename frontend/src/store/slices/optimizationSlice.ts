import { StateCreator } from 'zustand';
import type { AppState, CostRecord } from '@/types';
import type { PromptInstructions, OptimizationRequest, Constraint, CachedRunSummary, CachedRunDetail } from '@/types';
import apiClient from '@/api';

export interface OptimizationSlice {
  isOptimizing: boolean;
  optimizationJobId: string | null;
  optimizationProgress: number;
  optimizationStep: string;
  optimizationLog: string[];
  currentPrompts: PromptInstructions | null;
  optimizedPrompts: PromptInstructions | null;
  evalF1Before: number | null;
  evalF1After: number | null;
  previousConstraints: Constraint[] | null;
  showPromptsPanel: boolean;
  // Cached runs
  cachedRuns: CachedRunSummary[] | null;
  selectedCachedRunId: string | null;
  cachedRunDetail: CachedRunDetail | null;
  isLoadingCachedRuns: boolean;
  fetchCurrentPrompts: () => Promise<void>;
  startOptimization: (request?: OptimizationRequest) => Promise<void>;
  applyOptimizedPrompts: () => Promise<void>;
  resetOptimizedPrompts: () => Promise<void>;
  snapshotConstraints: () => void;
  clearComparison: () => void;
  setShowPromptsPanel: (show: boolean) => void;
  // Cached run actions
  fetchCachedRuns: () => Promise<void>;
  selectCachedRun: (runId: string | null) => Promise<void>;
  applyCachedRun: () => Promise<void>;
}

export const createOptimizationSlice: StateCreator<
  AppState,
  [],
  [],
  OptimizationSlice
> = (set, get) => ({
  isOptimizing: false,
  optimizationJobId: null,
  optimizationProgress: 0,
  optimizationStep: '',
  optimizationLog: [],
  currentPrompts: null,
  optimizedPrompts: null,
  evalF1Before: null,
  evalF1After: null,
  previousConstraints: null,
  showPromptsPanel: false,
  cachedRuns: null,
  selectedCachedRunId: null,
  cachedRunDetail: null,
  isLoadingCachedRuns: false,

  fetchCurrentPrompts: async () => {
    try {
      const response = await apiClient.getPrompts();
      set({
        currentPrompts: response.current,
        optimizedPrompts: response.optimized ?? null,
      });
    } catch (error) {
      get().addToast({
        type: 'error',
        message: `Failed to fetch prompts: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    }
  },

  startOptimization: async (request = {}) => {
    set({
      isOptimizing: true,
      optimizationProgress: 0,
      optimizationStep: 'Starting optimization...',
      optimizationLog: [],
      optimizedPrompts: null,
      evalF1Before: null,
      evalF1After: null,
    });

    try {
      const job = await apiClient.startOptimization(request);
      set({ optimizationJobId: job.jobId });

      // Poll until done — timeout after 30 minutes (900 × 2 s)
      const MAX_POLL_ATTEMPTS = 900;
      let pollCount = 0;
      while (true) {
        await new Promise<void>((resolve) => setTimeout(resolve, 2000));

        // Stop polling if the UI was cancelled
        if (!get().isOptimizing) return;

        if (++pollCount > MAX_POLL_ATTEMPTS) {
          throw new Error('Optimization timed out after 30 minutes');
        }

        const status = await apiClient.getOptimizationJob(job.jobId);
        set({
          optimizationProgress: status.progress,
          optimizationStep: status.currentStep,
          optimizationLog: status.stepLog ?? [],
        });

        if (status.status === 'completed' && status.result) {
          const r = status.result;

          // Record optimization cost alongside generation costs
          if (r.llmCost > 0) {
            const record: CostRecord = {
              id: crypto.randomUUID(),
              timestamp: new Date().toISOString(),
              taskFileName: `Prompt optimization (${request.dataset ?? 'default'})`,
              datasetName: `${r.nRoundsCompleted} round${r.nRoundsCompleted !== 1 ? 's' : ''}`,
              totalCost: r.llmCost,
            };
            const { costHistory, totalCost } = get();
            set({ costHistory: [...costHistory, record], totalCost: totalCost + r.llmCost });
          }

          set({
            isOptimizing: false,
            currentPrompts: r.beforeInstructions,
            optimizedPrompts: r.afterInstructions,
            evalF1Before: r.evalScoreBefore,
            evalF1After: r.evalScoreAfter,
          });
          get().addToast({
            type: 'success',
            message: `Optimization complete! Score: ${r.evalScoreBefore.toFixed(3)} → ${r.evalScoreAfter.toFixed(3)}`,
          });
          return;
        }

        if (status.status === 'failed' || status.status === 'cancelled') {
          set({ isOptimizing: false, optimizationProgress: 0, optimizationStep: '' });
          return;
        }
      }
    } catch (error) {
      set({ isOptimizing: false, optimizationProgress: 0, optimizationStep: '' });
      get().addToast({
        type: 'error',
        message: `Optimization failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    }
  },

  applyOptimizedPrompts: async () => {
    const { optimizationJobId } = get();
    if (!optimizationJobId) return;
    try {
      await apiClient.applyOptimizedPrompts(optimizationJobId);
      get().addToast({ type: 'success', message: 'Optimized prompts are now active' });
    } catch (error) {
      get().addToast({
        type: 'error',
        message: `Failed to apply prompts: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    }
  },

  resetOptimizedPrompts: async () => {
    try {
      await apiClient.resetPrompts();
      set({ optimizedPrompts: null, evalF1Before: null, evalF1After: null });
      get().addToast({ type: 'info', message: 'Reverted to baseline prompts' });
    } catch (error) {
      get().addToast({
        type: 'error',
        message: `Failed to reset prompts: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    }
  },

  snapshotConstraints: () => {
    set({ previousConstraints: get().constraints });
  },

  clearComparison: () => {
    set({ previousConstraints: null });
  },

  setShowPromptsPanel: (show: boolean) => {
    set({ showPromptsPanel: show });
  },

  fetchCachedRuns: async () => {
    set({ isLoadingCachedRuns: true });
    try {
      const response = await apiClient.getCachedRuns();
      set({ cachedRuns: response.runs, isLoadingCachedRuns: false });

      // Auto-select the sleep_health run (or first available) if nothing selected
      if (!get().selectedCachedRunId && response.runs.length > 0) {
        const sleepRun = response.runs.find((r) => r.trainDataset === 'sleep_health');
        const target = sleepRun ?? response.runs[0];
        get().selectCachedRun(target.runId);
      }
    } catch (error) {
      set({ isLoadingCachedRuns: false });
      get().addToast({
        type: 'error',
        message: `Failed to fetch cached runs: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    }
  },

  selectCachedRun: async (runId: string | null) => {
    if (!runId) {
      set({ selectedCachedRunId: null, cachedRunDetail: null });
      return;
    }
    set({ selectedCachedRunId: runId, isLoadingCachedRuns: true });
    try {
      const detail = await apiClient.getCachedRunDetail(runId);
      set({
        cachedRunDetail: detail,
        currentPrompts: detail.baselineInstructions,
        optimizedPrompts: detail.optimizedInstructions,
        evalF1Before: detail.initialScore,
        evalF1After: detail.finalScore,
        isLoadingCachedRuns: false,
      });
    } catch (error) {
      set({ isLoadingCachedRuns: false });
      get().addToast({
        type: 'error',
        message: `Failed to load cached run: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    }
  },

  applyCachedRun: async () => {
    const { selectedCachedRunId } = get();
    if (!selectedCachedRunId) return;
    try {
      await apiClient.applyCachedRun(selectedCachedRunId);
      get().addToast({ type: 'success', message: 'Cached optimized prompts are now active' });
    } catch (error) {
      get().addToast({
        type: 'error',
        message: `Failed to apply cached run: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    }
  },
});
