import { StateCreator } from 'zustand';
import type { AppState, CodeAnnotation, CostRecord, GenerationResult } from '@/types';
import apiClient, { CancelledError } from '@/api';
import { QUICK_EXAMPLE_DATASET, QUICK_EXAMPLE_SCRIPT, quickExampleResult } from '@/api/quickExampleFixture';

// Module-level abort controllers — not stored in Zustand (non-serializable)
let _currentAbortController: AbortController | null = null;
let _currentDetectAbortController: AbortController | null = null;

export interface ExecutionSlice {
  isGenerating: boolean;
  isDetecting: boolean;
  generationProgress: number;
  currentStep: string;
  totalCost: number;
  costHistory: CostRecord[];
  currentJobId: string | null;
  showCacheDialog: boolean;
  pendingCachedResult: (GenerationResult & { cached?: boolean }) | null;
  isOverlayMinimized: boolean;
  generateConstraints: (forceRegenerate?: boolean, selectedColumns?: string[]) => Promise<void>;
  cancelGeneration: () => Promise<void>;
  startDetection: (controller: AbortController) => void;
  stopDetection: () => void;
  cancelDetection: () => void;
  minimizeOverlay: () => void;
  restoreOverlay: () => void;
  useCachedResult: () => void;
  dismissCacheDialog: () => void;
  loadEIDBench: (dataset: string, script: string) => Promise<void>;
  loadQuickExample: () => Promise<void>;
  reset: () => void;
}

export const createExecutionSlice: StateCreator<
  AppState,
  [],
  [],
  ExecutionSlice
> = (set, get) => ({
  detectedAccessedColumns: [],
  isGenerating: false,
  isDetecting: false,
  generationProgress: 0,
  currentStep: '',
  totalCost: 0,
  costHistory: [],
  currentJobId: null,
  showCacheDialog: false,
  pendingCachedResult: null,
  isOverlayMinimized: false,

  generateConstraints: async (forceRegenerate = false, selectedColumns?: string[]) => {
    const { taskFile, dataset } = get();

    if (!taskFile || !dataset) {
      get().addToast({
        type: 'error',
        message: 'Please upload both task file and dataset first',
      });
      return;
    }

    _currentAbortController = new AbortController();

    set({
      isGenerating: true,
      generationProgress: 0,
      currentStep: 'Initializing...',
      currentJobId: null,
      isOverlayMinimized: false,
    });

    try {
      const { llmSettings, preferences } = get();

      // Build options with LLM settings + preferences
      const options: Record<string, unknown> = {
        model: llmSettings.model,
        forceRegenerate,
        maxParallelCalls: preferences.maxParallelCalls,
      };

      // Add API key if using own key
      if (llmSettings.useOwnKey && llmSettings.apiKey) {
        options.apiKey = llmSettings.apiKey;
      }

      // Add selected columns if provided
      if (selectedColumns && selectedColumns.length > 0) {
        options.selectedColumns = selectedColumns;
      }

      const result = await apiClient.generateConstraints(
        {
          taskFileId: taskFile.id,
          datasetId: dataset.id,
          options,
        },
        (progress, step) => {
          set({
            generationProgress: progress,
            currentStep: step,
          });
        },
        _currentAbortController.signal,
        (jobId) => { set({ currentJobId: jobId }); },
        // Apply intermediate results progressively as each stage completes
        (intermediate) => {
          const intAnnotations = new Map<number, CodeAnnotation>();
          for (const ann of intermediate.codeAnnotations ?? []) {
            const existing = intAnnotations.get(ann.lineNumber);
            if (existing) {
              existing.constraintIds = [...new Set([...existing.constraintIds, ...ann.constraintIds])];
            } else {
              intAnnotations.set(ann.lineNumber, { ...ann });
            }
          }
          set({
            assumptions: intermediate.assumptions ?? [],
            constraints: intermediate.constraints ?? [],
            flowGraph: intermediate.flowGraph ?? null,
            annotations: intAnnotations,
            rawAnnotations: intermediate.codeAnnotations ?? [],
          });
        },
      );

      // Check if result is cached and forceRegenerate wasn't set
      if (result.cached && !forceRegenerate) {
        // Store the cached result and show dialog
        set({
          isGenerating: false,
          showCacheDialog: true,
          pendingCachedResult: result,
        });
        return;
      }

      // Update state with generation results — merge constraintIds for duplicate lines
      const annotationsMap = new Map<number, CodeAnnotation>();
      for (const ann of result.codeAnnotations) {
        const existing = annotationsMap.get(ann.lineNumber);
        if (existing) {
          existing.constraintIds = [...new Set([...existing.constraintIds, ...ann.constraintIds])];
        } else {
          annotationsMap.set(ann.lineNumber, { ...ann });
        }
      }

      // Accumulate cost and record this run
      const { totalCost, costHistory, taskFile: tf, dataset: ds } = get();
      const runCost = result.statistics.llmCost || 0;
      const newCost = totalCost + runCost;

      const newRecord: CostRecord = {
        id: crypto.randomUUID(),
        timestamp: new Date().toISOString(),
        taskFileName: tf?.name ?? 'unknown',
        datasetName: ds?.name ?? 'unknown',
        totalCost: runCost,
        breakdown: result.statistics.costBreakdown,
      };

      set({
        constraints: result.constraints,
        assumptions: result.assumptions ?? [],
        flowGraph: result.flowGraph,
        annotations: annotationsMap,
        rawAnnotations: result.codeAnnotations ?? [],
        isGenerating: false,
        generationProgress: 1,
        currentStep: 'Complete!',
        totalCost: newCost,
        costHistory: [...costHistory, newRecord],
        constraintsSynced: true,
      });

      // Bulk-validate all constraints via the backend quality endpoint
      try {
        const qualityMetrics = await apiClient.getDataQualityMetrics(dataset.id);
        set({ dataQualityMetrics: qualityMetrics });
      } catch (error) {
        console.warn('Data quality metrics not available:', error);
      }

      get().addToast({
        type: 'success',
        message: `Generated ${result.constraints.length} constraints`,
      });

      // Surface any partial-failure warnings from the backend
      for (const warning of result.statistics.warnings ?? []) {
        get().addToast({ type: 'error', message: warning });
      }
    } catch (error) {
      if (error instanceof CancelledError) {
        set({ isGenerating: false, generationProgress: 0, currentStep: '', currentJobId: null, isOverlayMinimized: false });
        get().addToast({ type: 'info', message: 'Generation cancelled' });
        return;
      }

      set({
        isGenerating: false,
        generationProgress: 0,
        currentStep: '',
        currentJobId: null,
        isOverlayMinimized: false,
      });

      get().addToast({
        type: 'error',
        message: `Constraint generation failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
      throw error;
    } finally {
      _currentAbortController = null;
    }
  },

  minimizeOverlay: () => set({ isOverlayMinimized: true }),
  restoreOverlay: () => set({ isOverlayMinimized: false }),

  cancelGeneration: async () => {
    const { currentJobId } = get();
    _currentAbortController?.abort();
    set({ isGenerating: false, generationProgress: 0, currentStep: '', currentJobId: null, isOverlayMinimized: false });
    if (currentJobId) {
      try {
        await apiClient.cancelGenerationJob(currentJobId);
      } catch (_) {
        // Ignore errors (job may have already completed)
      }
    }
  },

  startDetection: (controller: AbortController) => {
    _currentDetectAbortController = controller;
    set({ isDetecting: true });
  },

  stopDetection: () => {
    _currentDetectAbortController = null;
    set({ isDetecting: false, isOverlayMinimized: false });
  },

  cancelDetection: () => {
    _currentDetectAbortController?.abort();
    _currentDetectAbortController = null;
    set({ isDetecting: false, isOverlayMinimized: false });
  },

  useCachedResult: () => {
    const { pendingCachedResult: result } = get();
    if (!result) return;

    // Apply the cached result — merge constraintIds for duplicate lines
    const annotationsMap = new Map<number, any>();
    for (const ann of result.codeAnnotations) {
      const existing = annotationsMap.get(ann.lineNumber);
      if (existing) {
        existing.constraintIds = [...new Set([...existing.constraintIds, ...ann.constraintIds])];
      } else {
        annotationsMap.set(ann.lineNumber, { ...ann });
      }
    }

    // Don't accumulate cost for cached results (already counted)
    set({
      constraints: result.constraints,
      assumptions: result.assumptions ?? [],
      flowGraph: result.flowGraph,
      annotations: annotationsMap,
      showCacheDialog: false,
      pendingCachedResult: null,
      generationProgress: 1,
      currentStep: 'Complete! (cached)',
      constraintsSynced: true,
    });

    get().addToast({
      type: 'success',
      message: `Loaded ${result.constraints.length} cached constraints`,
    });
  },

  dismissCacheDialog: () => {
    set({
      showCacheDialog: false,
      pendingCachedResult: null,
    });
  },

  loadEIDBench: async (dataset: string, script: string) => {
    try {
      const { taskFile, dataset: datasetFile } = await apiClient.loadEIDBenchData(dataset, script);

      set({
        taskFile,
        dataset: datasetFile,
        code: taskFile.content,
        constraints: [],
        assumptions: [],
        selectedConstraintId: null,
        selectedAssumptionId: null,
        highlightedLines: [],
        annotations: new Map(),
        rawAnnotations: [],
        flowGraph: null,
        highlightedNodes: [],
        selectedColumn: null,
        columnStats: new Map(),
        dataQualityMetrics: null,
        deequValidationResults: new Map(),
        isGenerating: false,
        generationProgress: 0,
        currentStep: '',
        constraintsSynced: null,
        showCacheDialog: false,
        pendingCachedResult: null,
        currentJobId: null,
      });

      // Fetch completeness metrics right after loading
      apiClient.getDataQualityMetrics(datasetFile.id)
        .then((qualityMetrics) => set({ dataQualityMetrics: qualityMetrics }))
        .catch(() => {});

      get().addToast({
        type: 'success',
        message: `Loaded benchmark: ${dataset} / ${script}`,
      });
    } catch (error) {
      get().addToast({
        type: 'error',
        message: `Failed to load benchmark data: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    }
  },

  loadQuickExample: async () => {
    try {
      // Load EIDBench files from backend (registers in session storage + profiles CSV)
      const { taskFile, dataset: datasetFile } = await apiClient.loadEIDBenchData(
        QUICK_EXAMPLE_DATASET,
        QUICK_EXAMPLE_SCRIPT,
      );

      // Build annotations map from fixture
      const annotationsMap = new Map<number, CodeAnnotation>();
      for (const ann of quickExampleResult.codeAnnotations) {
        const existing = annotationsMap.get(ann.lineNumber);
        if (existing) {
          existing.constraintIds = [...new Set([...existing.constraintIds, ...ann.constraintIds])];
        } else {
          annotationsMap.set(ann.lineNumber, { ...ann });
        }
      }

      // Build cost record from fixture statistics
      const runCost = quickExampleResult.statistics.llmCost || 0;
      const costRecord: CostRecord = {
        id: crypto.randomUUID(),
        timestamp: new Date().toISOString(),
        taskFileName: QUICK_EXAMPLE_SCRIPT,
        datasetName: QUICK_EXAMPLE_DATASET,
        totalCost: runCost,
        breakdown: quickExampleResult.statistics.costBreakdown,
      };

      // Extract accessed columns from fixture flow graph
      const detectedAccessedColumns = (quickExampleResult.flowGraph?.nodes ?? [])
        .filter((n) => n.type === 'data')
        .map((n) => n.label);

      // Apply everything in one shot
      set({
        taskFile,
        dataset: datasetFile,
        code: taskFile.content,
        constraints: quickExampleResult.constraints,
        assumptions: quickExampleResult.assumptions ?? [],
        flowGraph: quickExampleResult.flowGraph,
        detectedAccessedColumns,
        annotations: annotationsMap,
        rawAnnotations: quickExampleResult.codeAnnotations ?? [],
        selectedConstraintId: null,
        selectedAssumptionId: null,
        highlightedLines: [],
        highlightedNodes: [],
        selectedColumn: null,
        columnStats: new Map(),
        dataQualityMetrics: null,
        deequValidationResults: new Map(),
        isGenerating: false,
        generationProgress: 1,
        currentStep: 'Complete! (quick example)',
        constraintsSynced: true,
        showCacheDialog: false,
        pendingCachedResult: null,
        currentJobId: null,
        totalCost: runCost,
        costHistory: [costRecord],
      });

      // 1. Fetch completeness immediately (no constraints needed)
      const loadedConstraints = quickExampleResult.constraints;
      const datasetId = datasetFile.id;
      apiClient.getDataQualityMetrics(datasetId)
        .then((qualityMetrics) => set({ dataQualityMetrics: qualityMetrics }))
        .catch(() => {});

      // 2. Validate all constraints in parallel, then apply results in one batch
      if (loadedConstraints.length > 0) {
        const validationPromises = loadedConstraints.map((c) =>
          apiClient.validateConstraint(datasetId, {
            constraintId: c.id,
            column: c.column,
            backend: 'great_expectations',
            greatExpectationsCode: c.code.greatExpectations,
          }).catch(() => null)
        );

        // Collect all results then apply at once
        Promise.all(validationPromises).then((results) => {
          const violationsByConstraint: Record<string, number> = {};
          const validationMessages: Record<string, string> = {};
          let violationCount = 0;

          for (const r of results) {
            if (!r) continue;
            const statusVal = r.status === 'passed' ? 0 : r.status === 'failed' ? 1 : 2;
            violationsByConstraint[r.constraintId] = statusVal;
            if (statusVal > 0) {
              violationCount++;
              validationMessages[r.constraintId] = r.error || r.message || '';
            }
          }

          const total = Object.keys(violationsByConstraint).length;
          const passed = Object.values(violationsByConstraint).filter((v) => v === 0).length;
          const existing = get().dataQualityMetrics;
          const completeness = existing?.metrics?.completeness ?? 0;

          set({
            dataQualityMetrics: {
              datasetId,
              metrics: {
                completeness,
                validity: total > 0 ? passed / total : 0,
                constraintCount: loadedConstraints.length,
                activeConstraints: loadedConstraints.filter((c) => c.enabled).length,
                disabledConstraints: loadedConstraints.filter((c) => !c.enabled).length,
                violationCount,
                violationsByConstraint,
                validationMessages,
                overallHealth: violationCount === 0 ? 'healthy' : violationCount <= 3 ? 'warning' : 'issues',
              },
            },
          });
        });
      }

      get().addToast({
        type: 'success',
        message: `Loaded quick example: ${QUICK_EXAMPLE_DATASET} / ${QUICK_EXAMPLE_SCRIPT} (${quickExampleResult.constraints.length} constraints)`,
      });
    } catch (error) {
      get().addToast({
        type: 'error',
        message: `Failed to load quick example: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    }
  },

  reset: () => {
    set({
      taskFile: null,
      dataset: null,
      constraints: [],
      assumptions: [],
      selectedConstraintId: null,
      selectedAssumptionId: null,
      code: '',
      highlightedLines: [],
      annotations: new Map(),
      rawAnnotations: [],
      flowGraph: null,
      highlightedNodes: [],
      selectedColumn: null,
      columnStats: new Map(),
      dataQualityMetrics: null,
      deequValidationResults: new Map(),
      isGenerating: false,
      isDetecting: false,
      generationProgress: 0,
      currentStep: '',
      totalCost: 0,
      costHistory: [],
      currentJobId: null,
      constraintsSynced: null,
    });

    get().addToast({
      type: 'info',
      message: 'Session reset',
    });
  },
});
