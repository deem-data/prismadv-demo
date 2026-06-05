import { StateCreator } from 'zustand';
import type { AppState, DeequSuggestion, ErrorBenchmarkResult } from '@/types';
import apiClient from '@/api';

export interface DeequSlice {
  deequSuggestions: DeequSuggestion[] | null;
  /** The dataset ID for which suggestions were last fetched. */
  deequSuggestionsDatasetId: string | null;
  isLoadingDeequSuggestions: boolean;
  showDeequComparison: boolean;
  /** Currently selected Deequ suggestion ID (for detail panel). */
  selectedDeequSuggestionId: string | null;

  // Error-batch benchmark state
  errorBenchmarkJobId: string | null;
  errorBenchmarkStatus: 'idle' | 'running' | 'completed' | 'failed';
  errorBenchmarkProgress: number;
  errorBenchmarkStep: string;
  errorBenchmarkResult: ErrorBenchmarkResult | null;

  /** Fetch Deequ suggestions for the current dataset (noop if no dataset). */
  fetchDeequSuggestions: () => Promise<void>;
  /** Toggle the comparison panel. Fetches suggestions if needed. */
  toggleDeequComparison: () => void;
  /** Clear all Deequ state (e.g. when a new dataset is uploaded). */
  clearDeequSuggestions: () => void;
  /** Select a Deequ suggestion to show in the detail panel. */
  selectDeequSuggestion: (id: string | null) => void;
  /** Start the error-batch benchmark. */
  startErrorBenchmark: () => Promise<void>;
  /** Clear benchmark state back to idle. */
  clearErrorBenchmark: () => void;
}

let _benchmarkPollTimer: ReturnType<typeof setInterval> | null = null;

export const createDeequSlice: StateCreator<
  AppState,
  [],
  [],
  DeequSlice
> = (set, get) => ({
  deequSuggestions: null,
  deequSuggestionsDatasetId: null,
  isLoadingDeequSuggestions: false,
  showDeequComparison: false,
  selectedDeequSuggestionId: null,

  errorBenchmarkJobId: null,
  errorBenchmarkStatus: 'idle',
  errorBenchmarkProgress: 0,
  errorBenchmarkStep: '',
  errorBenchmarkResult: null,

  fetchDeequSuggestions: async () => {
    const { dataset } = get();
    if (!dataset) return;

    set({ isLoadingDeequSuggestions: true });
    try {
      const response = await apiClient.getDeequSuggestions(dataset.id);
      set({
        deequSuggestions: response.suggestions,
        deequSuggestionsDatasetId: dataset.id,
        isLoadingDeequSuggestions: false,
      });
    } catch (error) {
      set({ isLoadingDeequSuggestions: false });
      get().addToast({
        type: 'error',
        message: `Failed to load Deequ suggestions: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    }
  },

  toggleDeequComparison: () => {
    const { showDeequComparison, dataset, deequSuggestionsDatasetId } = get();

    if (showDeequComparison) {
      // Turn off
      set({ showDeequComparison: false, selectedDeequSuggestionId: null });
      return;
    }

    // Turn on — fetch if we don't have suggestions for the current dataset
    if (
      dataset &&
      (deequSuggestionsDatasetId !== dataset.id || get().deequSuggestions === null)
    ) {
      set({ showDeequComparison: true });
      get().fetchDeequSuggestions();
    } else {
      set({ showDeequComparison: true });
    }
  },

  clearDeequSuggestions: () => {
    set({
      deequSuggestions: null,
      deequSuggestionsDatasetId: null,
      showDeequComparison: false,
      isLoadingDeequSuggestions: false,
      selectedDeequSuggestionId: null,
    });
  },

  selectDeequSuggestion: (id) => {
    set({ selectedDeequSuggestionId: id });
  },

  startErrorBenchmark: async () => {
    const { dataset, taskFile, constraints, deequSuggestions } = get();
    if (!dataset || !taskFile) return;

    // Send raw filenames — backend resolves the dataset directory and task name
    const datasetName = dataset.name;
    const taskName = taskFile.name.replace(/\.py$/, '');

    // Build constraint codes from store
    const prismadvConstraints = constraints
      .filter((c) => c.code?.deequ)
      .map((c) => ({ id: c.id, deequCode: c.code.deequ! }));
    const deequCodes = (deequSuggestions ?? [])
      .filter((s) => s.deequCode)
      .map((s) => ({ id: s.id, deequCode: s.deequCode! }));

    if (!prismadvConstraints.length || !deequCodes.length) {
      get().addToast({ type: 'error', message: 'Need both PrismaDV constraints and Deequ suggestions with Deequ code.' });
      return;
    }

    // Stop any existing poll
    if (_benchmarkPollTimer) {
      clearInterval(_benchmarkPollTimer);
      _benchmarkPollTimer = null;
    }

    set({
      errorBenchmarkStatus: 'running',
      errorBenchmarkProgress: 0,
      errorBenchmarkStep: 'Starting...',
      errorBenchmarkResult: null,
      errorBenchmarkJobId: null,
    });

    try {
      const job = await apiClient.startErrorBenchmark(datasetName, taskName, prismadvConstraints, deequCodes);
      set({ errorBenchmarkJobId: job.jobId });

      if (job.status === 'completed' && job.result) {
        set({
          errorBenchmarkStatus: 'completed',
          errorBenchmarkProgress: 1,
          errorBenchmarkStep: 'Complete!',
          errorBenchmarkResult: job.result,
        });
        return;
      }

      // Start polling
      _benchmarkPollTimer = setInterval(async () => {
        const { errorBenchmarkJobId, errorBenchmarkStatus } = get();
        if (!errorBenchmarkJobId || errorBenchmarkStatus !== 'running') {
          if (_benchmarkPollTimer) {
            clearInterval(_benchmarkPollTimer);
            _benchmarkPollTimer = null;
          }
          return;
        }

        try {
          const status = await apiClient.getErrorBenchmarkJob(errorBenchmarkJobId);
          set({
            errorBenchmarkProgress: status.progress,
            errorBenchmarkStep: status.currentStep,
          });

          if (status.status === 'completed') {
            set({
              errorBenchmarkStatus: 'completed',
              errorBenchmarkResult: status.result ?? null,
            });
            if (_benchmarkPollTimer) {
              clearInterval(_benchmarkPollTimer);
              _benchmarkPollTimer = null;
            }
          } else if (status.status === 'failed') {
            set({
              errorBenchmarkStatus: 'failed',
              errorBenchmarkStep: status.error ?? 'Benchmark failed',
            });
            if (_benchmarkPollTimer) {
              clearInterval(_benchmarkPollTimer);
              _benchmarkPollTimer = null;
            }
          }
        } catch {
          // Ignore poll errors, keep trying
        }
      }, 2000);
    } catch (error: any) {
      const detail = error?.response?.data?.detail ?? (error instanceof Error ? error.message : 'Failed to start benchmark');
      set({
        errorBenchmarkStatus: 'idle',
        errorBenchmarkProgress: 0,
        errorBenchmarkStep: '',
      });
      get().addToast({ type: 'error', message: `Error benchmark: ${detail}` });
    }
  },

  clearErrorBenchmark: () => {
    if (_benchmarkPollTimer) {
      clearInterval(_benchmarkPollTimer);
      _benchmarkPollTimer = null;
    }
    set({
      errorBenchmarkJobId: null,
      errorBenchmarkStatus: 'idle',
      errorBenchmarkProgress: 0,
      errorBenchmarkStep: '',
      errorBenchmarkResult: null,
    });
  },
});
