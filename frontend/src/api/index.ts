import { PrismaDVClient, CancelledError } from './client';
import type {
  CodeFile,
  Constraint,
  Dataset,
  DatasetPreview,
  GenerationResult,
  ColumnStatsResponse,
  DataQualityMetrics,
  DetectColumnsResponse,
  GenerateConstraintsRequest,
  ExportConstraintsRequest,
  EIDBenchListResponse,
  OptimizationRequest,
  OptimizationJobStatus,
  PromptsResponse,
  DeequSuggestionsResponse,
  ValidateConstraintRequest,
  ValidateConstraintResponse,
  CachedRunListResponse,
  CachedRunDetail,
  ErrorBenchmarkJobStatus,
} from '@/types';
import {
  mockCodeFile,
  mockDataset,
  mockDatasetPreview,
  mockGenerationResult,
  mockNameColumnStats,
  mockAgeColumnStats,
  mockCategoryColumnStats,
  mockDataQualityMetrics,
} from './mock';

// Feature flag to toggle between real API and mock data
const USE_MOCK_API = import.meta.env.VITE_USE_MOCK_API === 'true';

/**
 * Mock API Client
 * Simulates API responses with realistic delays
 */
class MockPrismaDVClient {
  private delay(ms: number = 500): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async uploadTaskFile(file: File, name?: string): Promise<CodeFile> {
    await this.delay(800);
    return { ...mockCodeFile, name: name || file.name };
  }

  async uploadDataset(file: File, name?: string): Promise<Dataset> {
    await this.delay(1000);
    return { ...mockDataset, name: name || file.name };
  }

  async detectColumns(_request: any, _signal?: AbortSignal): Promise<DetectColumnsResponse> {
    await this.delay(1500);
    // Return mock detected columns (subset of all)
    return {
      allColumns: mockDataset.columns.map((c) => c.name),
      accessedColumns: ['name', 'age', 'category'],
      cached: false,
    };
  }

  async generateConstraints(
    _request: GenerateConstraintsRequest,
    onProgress?: (progress: number, step: string) => void,
    _signal?: AbortSignal,
    _onJobId?: (jobId: string) => void,
    _onIntermediateResult?: (result: GenerationResult) => void,
  ): Promise<GenerationResult> {
    // Simulate progressive generation with callbacks
    const steps = [
      { progress: 0.0, step: 'Initializing analysis...' },
      { progress: 0.2, step: 'Parsing task code...' },
      { progress: 0.4, step: 'Analyzing data patterns...' },
      { progress: 0.6, step: 'Extracting assumptions...' },
      { progress: 0.8, step: 'Generating constraints...' },
      { progress: 1.0, step: 'Complete!' },
    ];

    for (const { progress, step } of steps) {
      onProgress?.(progress, step);
      await this.delay(400);
    }

    return mockGenerationResult;
  }

  async getDatasetPreview(_datasetId: string, limit: number = 10): Promise<DatasetPreview> {
    await this.delay(200);
    return {
      ...mockDatasetPreview,
      rows: mockDatasetPreview.rows.slice(0, limit),
    };
  }

  async getColumnStats(datasetId: string, columnName: string): Promise<ColumnStatsResponse> {
    await this.delay(300);

    const statsMap: Record<string, any> = {
      name: mockNameColumnStats,
      age: mockAgeColumnStats,
      category: mockCategoryColumnStats,
    };

    const stats = statsMap[columnName] || mockNameColumnStats;

    return {
      datasetId,
      columnName,
      type: 'string',
      inferredType: stats.constraintIds.includes('constraint-1') ? 'textual' : 'numerical',
      stats,
    };
  }

  async getDataQualityMetrics(_datasetId: string): Promise<DataQualityMetrics> {
    await this.delay(250);
    return mockDataQualityMetrics;
  }

  async exportConstraints(request: ExportConstraintsRequest): Promise<Blob> {
    await this.delay(400);
    const content = `# Mock ${request.format} export\n# Generated constraints would go here`;
    return new Blob([content], { type: 'text/plain' });
  }

  downloadExport(blob: Blob, format: string) {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `prismadv_constraints.${format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  // Project management methods (optional)
  async saveProject(): Promise<any> {
    await this.delay(500);
    return { id: 'project-1', name: 'Mock Project' };
  }

  async listProjects(): Promise<any[]> {
    await this.delay(300);
    return [];
  }

  async loadProject(): Promise<any> {
    await this.delay(500);
    return { id: 'project-1', name: 'Mock Project' };
  }

  async getEIDBenchDatasets(): Promise<EIDBenchListResponse> {
    return { datasets: [] };
  }

  async loadEIDBenchData(_dataset: string, _script: string): Promise<{
    taskFile: CodeFile;
    dataset: Dataset;
  }> {
    await this.delay(600);
    return { taskFile: mockCodeFile, dataset: mockDataset };
  }

  async generateFromAssumption(_request: any): Promise<{ constraints: Constraint[]; message?: string }> {
    await this.delay(1000);
    return { constraints: [] }; // Mock returns empty — real API needed for actual generation
  }

  async validateConstraint(
    _datasetId: string,
    request: ValidateConstraintRequest,
  ): Promise<ValidateConstraintResponse> {
    await this.delay(800);
    return {
      constraintId: request.constraintId,
      backend: request.backend,
      status: 'passed',
      message: 'Constraint satisfied — no violations detected.',
      durationMs: 250,
    };
  }

  async cancelGenerationJob(_jobId: string): Promise<void> {
    // No-op in mock — generation isn't actually running
  }

  async getPrompts(): Promise<PromptsResponse> {
    await this.delay(200);
    return {
      current: {
        columnAccess: 'Identify which columns are accessed by the task code.',
        assumptionExtraction: 'Extract data quality assumptions for the given column.',
        constraintGeneration: 'Generate constraint code for the given assumption.',
      },
      optimized: undefined,
      optimizationActive: false,
    };
  }

  async startOptimization(_request: OptimizationRequest): Promise<OptimizationJobStatus> {
    await this.delay(300);
    return {
      jobId: 'mock-opt-job-1',
      status: 'processing',
      progress: 0,
      currentStep: 'Starting optimization...',
      stepLog: [],
    };
  }

  async getOptimizationJob(_jobId: string): Promise<OptimizationJobStatus> {
    await this.delay(500);
    return {
      jobId: 'mock-opt-job-1',
      status: 'completed',
      progress: 1.0,
      currentStep: 'Complete!',
      stepLog: ['Baseline score: 0.450', 'Condensed: 12/40 units', 'R1 iter 1: ACCEPTED — eval score 0.520'],
      result: {
        beforeInstructions: {
          columnAccess: 'Identify which columns are accessed by the task code.',
          assumptionExtraction: 'Extract data quality assumptions for the given column.',
          constraintGeneration: 'Generate constraint code for the given assumption.',
        },
        afterInstructions: {
          columnAccess: 'Carefully identify which columns are directly accessed by the task code, focusing on read operations.',
          assumptionExtraction: 'Extract precise, testable data quality assumptions for the given column based on its usage in the task.',
          constraintGeneration: 'Generate robust constraint code that validates the assumption using appropriate checks.',
        },
        evalScoreBefore: 0.62,
        evalScoreAfter: 0.78,
        improved: true,
        nRoundsCompleted: 2,
        llmCost: 0.0042,
      },
    };
  }

  async cancelOptimizationJob(_jobId: string): Promise<void> {
    await this.delay(100);
  }

  async applyOptimizedPrompts(_jobId: string): Promise<void> {
    await this.delay(200);
  }

  async resetPrompts(): Promise<void> {
    await this.delay(200);
  }

  async getCachedRuns(): Promise<CachedRunListResponse> {
    await this.delay(300);
    return {
      runs: [
        {
          runId: 'gepa_column_run_20260114_145506',
          timestamp: '20260114_145506',
          llmName: 'gpt-4.1-mini',
          reflectionLlmName: 'gpt-5',
          baselineType: 'gepa_column',
          metricType: 'f1_score',
          trainDataset: 'hr_analytics',
          maxRounds: 1,
          initialScore: 23.83,
          finalScore: 28.5,
          improved: true,
        },
        {
          runId: 'baseline_gepa_run_20260113_150805',
          timestamp: '20260113_150805',
          llmName: 'gpt-4.1-mini',
          trainDataset: 'students',
          maxRounds: 1,
          initialScore: 68.07,
          finalScore: 68.07,
          improved: false,
        },
      ],
    };
  }

  async getCachedRunDetail(_runId: string): Promise<CachedRunDetail> {
    await this.delay(300);
    return {
      runId: 'gepa_column_run_20260114_145506',
      timestamp: '20260114_145506',
      llmName: 'gpt-4.1-mini',
      trainDataset: 'hr_analytics',
      initialScore: 23.83,
      finalScore: 28.5,
      baselineInstructions: {
        columnAccess: 'Identify lines where a target column is used in a code snippet.',
        assumptionExtraction: 'Generate assumptions for the target column.',
        constraintGeneration: 'Generate PyDeequ validation code from assumptions and requirements.',
      },
      optimizedInstructions: {
        columnAccess: 'Identify lines where a target column is used in a code snippet.\nInclude every line that reads, writes, filters, transforms, merges, or passes through the target column.',
        assumptionExtraction: 'Generate precise, testable assumptions for the target column based on its usage patterns in the code.',
        constraintGeneration: 'Generate robust PyDeequ validation constraints that catch data quality issues while minimizing false alarms.',
      },
      config: {
        executionLlm: 'gpt-4.1-mini',
        proposerLlm: undefined,
        maxRounds: 1,
        trainScripts: ['general_task_21', 'general_task_9', 'general_task_16'],
        evalScripts: ['general_task_6', 'general_task_11', 'general_task_3'],
        testScripts: ['general_task_26', 'general_task_12', 'general_task_1'],
        trainErrorConfigs: ['17', '13', '10', '20', '19', '7'],
        testErrorConfigs: ['2', '15', '23', '14', '3', '24'],
      },
    };
  }

  async applyCachedRun(_runId: string): Promise<void> {
    await this.delay(200);
  }

  async getDatasetInfo(dataset: string): Promise<{ dataset: string; scripts: string[]; errorConfigs: string[] }> {
    await this.delay(200);
    return { dataset, scripts: ['general_task_1', 'general_task_2', 'general_task_3'], errorConfigs: ['1','2','3','4','5'] };
  }

  async getErrorConfig(_runId: string, configId: string): Promise<{ configId: string; dataset: string; content: string }> {
    await this.delay(200);
    return { configId, dataset: 'mock_dataset', content: `- GaussianNoise:\n    Columns:\n      - col_${configId}\n    Params:\n      severity: 0.05\n      sampling: CAR` };
  }

  async getDeequSuggestions(datasetId: string): Promise<DeequSuggestionsResponse> {
    await this.delay(400);
    return {
      datasetId,
      suggestions: [
        {
          id: 'deequ-mock-1',
          column: '_dataset_',
          constraintType: 'statistical',
          deequCode: 'hasSize(lambda x: x >= 100)',
          description: 'Dataset must have at least 100 rows',
        },
        {
          id: 'deequ-mock-2',
          column: 'name',
          constraintType: 'completeness',
          deequCode: 'isComplete("name")',
          description: '"name" must be complete (no nulls)',
        },
        {
          id: 'deequ-mock-3',
          column: 'age',
          constraintType: 'completeness',
          deequCode: 'isComplete("age")',
          description: '"age" must be complete (no nulls)',
        },
        {
          id: 'deequ-mock-4',
          column: 'age',
          constraintType: 'range',
          deequCode: 'isNonNegative("age")',
          description: '"age" must be non-negative',
        },
        {
          id: 'deequ-mock-5',
          column: 'age',
          constraintType: 'range',
          deequCode: 'hasMin("age", lambda x: x >= 18)',
          description: '"age" minimum must be ≥ 18',
        },
        {
          id: 'deequ-mock-6',
          column: 'category',
          constraintType: 'enum',
          deequCode: 'isContainedIn("category", ["A", "B", "C"])',
          description: '"category" must be one of 3 known values',
        },
      ],
    };
  }

  // Error-batch benchmark (mock)
  async startErrorBenchmark(_datasetName: string, _taskName: string, _prismadvConstraints: any[], _deequSuggestions: any[]): Promise<ErrorBenchmarkJobStatus> {
    return { jobId: 'mock-bench-1', status: 'completed', progress: 1, currentStep: 'Complete!', result: {
      datasetName: 'mock_dataset', totalBatches: 3, prismadvConstraintCount: 5, deequSuggestionCount: 4,
      batches: [
        { batchId: 'clean', errorDescription: 'Clean baseline', harmful: false, prismadvViolations: 0, prismadvTotal: 5, deequViolations: 1, deequTotal: 4 },
        { batchId: '1', errorDescription: 'GaussianNoise on col', harmful: true, prismadvViolations: 3, prismadvTotal: 5, deequViolations: 0, deequTotal: 4 },
        { batchId: '2', errorDescription: 'MaskValues on col', harmful: false, prismadvViolations: 2, prismadvTotal: 5, deequViolations: 1, deequTotal: 4 },
      ],
      prismadvDetectionRate: 1.0, deequDetectionRate: 0.33, prismadvFalseAlarmRate: 0.5, deequFalseAlarmRate: 0.5, prismadvCleanViolations: 0, deequCleanViolations: 1,
    }};
  }

  async getErrorBenchmarkJob(_jobId: string): Promise<ErrorBenchmarkJobStatus> {
    return { jobId: 'mock-bench-1', status: 'completed', progress: 1, currentStep: 'Complete!' };
  }
}

// Export appropriate client based on feature flag
export const apiClient = USE_MOCK_API ? new MockPrismaDVClient() : new PrismaDVClient();

// Export for testing
export { PrismaDVClient, MockPrismaDVClient, CancelledError };
export default apiClient;
