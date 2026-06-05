import axios, { AxiosInstance, AxiosError } from 'axios';

export class CancelledError extends Error {
  readonly cancelled = true;
  constructor() {
    super('Generation cancelled by user');
    this.name = 'CancelledError';
  }
}
import type {
  CodeFile,
  Constraint,
  Dataset,
  DatasetPreview,
  GenerationResult,
  GenerationJobResponse,
  ColumnStatsResponse,
  DataQualityMetrics,
  DetectColumnsRequest,
  DetectColumnsResponse,
  GenerateConstraintsRequest,
  ExportConstraintsRequest,
  SaveProjectRequest,
  Project,
  ExportFormat,
  ApiError,
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

/**
 * PrismaDV API Client
 *
 * Implements the API contract defined in plan/03-api-specification.md
 * Base URL: /api/v1 (proxied to http://localhost:8000 in development)
 */
export class PrismaDVClient {
  private client: AxiosInstance;

  constructor(baseURL: string = '/api/v1') {
    this.client = axios.create({
      baseURL,
      timeout: 600000, // 10 minutes for LLM constraint generation
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ApiError>) => {
        if (error.response?.data?.error) {
          throw new Error(error.response.data.error.message);
        }
        throw error;
      }
    );
  }

  // ========== File Upload Endpoints ==========

  /**
   * Upload task code file (Python or SQL)
   */
  async uploadTaskFile(file: File, name?: string): Promise<CodeFile> {
    const formData = new FormData();
    formData.append('file', file);
    if (name) {
      formData.append('name', name);
    }

    const response = await this.client.post<CodeFile>('/files/task', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });

    return response.data;
  }

  /**
   * Upload dataset file (CSV)
   */
  async uploadDataset(file: File, name?: string): Promise<Dataset> {
    const formData = new FormData();
    formData.append('file', file);
    if (name) {
      formData.append('name', name);
    }

    const response = await this.client.post<Dataset>('/files/dataset', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });

    return response.data;
  }

  // ========== Constraint Generation Endpoints ==========

  /**
   * Detect which columns are accessed by the task code (pre-flight before generation).
   * Runs dataset profiling + LLM column access detection only.
   */
  async detectColumns(
    request: DetectColumnsRequest,
    signal?: AbortSignal,
  ): Promise<DetectColumnsResponse> {
    const response = await this.client.post<DetectColumnsResponse>(
      '/constraints/detect-columns',
      request,
      { signal },
    );
    return response.data;
  }

  async generateFromAssumption(request: {
    assumptionText: string;
    column: string;
    taskFileId: string;
    datasetId: string;
    options?: Record<string, unknown>;
    existingConstraints?: { greatExpectations: string; deequ: string }[];
  }): Promise<{ constraints: Constraint[]; message?: string }> {
    const response = await this.client.post<{ constraints: Constraint[]; message?: string }>(
      '/constraints/generate-from-assumption',
      request,
    );
    return response.data;
  }

  /**
   * Generate constraints by analyzing task code and dataset
   * Returns result with `cached` flag indicating if it came from cache
   */
  async generateConstraints(
    request: GenerateConstraintsRequest,
    onProgress?: (progress: number, step: string) => void,
    signal?: AbortSignal,
    onJobId?: (jobId: string) => void,
    onIntermediateResult?: (result: GenerationResult) => void,
  ): Promise<GenerationResult & { cached?: boolean }> {
    const response = await this.client.post<GenerationJobResponse>(
      '/constraints/generate',
      request,
      { signal },
    );

    const jobId = response.data.jobId;
    onJobId?.(jobId);

    // Poll for completion if job is processing
    if (response.data.status === 'processing' || response.data.status === 'pending') {
      return await this.pollGenerationJob(jobId, onProgress, signal, onIntermediateResult);
    }

    if (response.data.status === 'completed' && response.data.result) {
      // Include cached flag in result
      return { ...response.data.result, cached: response.data.cached };
    }

    throw new Error(response.data.error || 'Generation failed');
  }

  /**
   * Poll generation job status until completion.
   * Respects the AbortSignal for cancellation.
   */
  private async pollGenerationJob(
    jobId: string,
    onProgress?: (progress: number, step: string) => void,
    signal?: AbortSignal,
    onIntermediateResult?: (result: GenerationResult) => void,
  ): Promise<GenerationResult> {
    // Track last intermediate result to avoid duplicate callbacks
    let lastIntermediateStage = '';

    // No timeout — rely on the Cancel button (AbortSignal) to stop polling.
    while (true) {
      if (signal?.aborted) throw new CancelledError();

      let response;
      try {
        response = await this.client.get<GenerationJobResponse>(
          `/constraints/jobs/${jobId}`,
          { signal },
        );
      } catch (e) {
        if (axios.isCancel(e) || signal?.aborted) throw new CancelledError();
        throw e;
      }

      const { status, progress, currentStep, result, intermediateResult, error } = response.data;

      // Call progress callback
      if (onProgress && progress !== undefined) {
        onProgress(progress, currentStep);
      }

      // Apply intermediate results progressively
      if (onIntermediateResult && intermediateResult) {
        // Detect stage change by checking node/assumption/constraint counts
        const stageKey = `${intermediateResult.flowGraph?.nodes?.length ?? 0}-${intermediateResult.assumptions?.length ?? 0}-${intermediateResult.constraints?.length ?? 0}`;
        if (stageKey !== lastIntermediateStage) {
          lastIntermediateStage = stageKey;
          onIntermediateResult(intermediateResult);
        }
      }

      // Check completion
      if (status === 'completed' && result) {
        return result;
      }

      if (status === 'failed') {
        throw new Error(error || 'Generation failed');
      }

      if (status === 'cancelled') {
        throw new CancelledError();
      }

      // Wait 1 second before next poll, but wake early if aborted
      await new Promise<void>((resolve) => {
        const id = setTimeout(resolve, 1000);
        signal?.addEventListener('abort', () => { clearTimeout(id); resolve(); }, { once: true });
      });

    }
  }

  /**
   * Cancel a running generation job.
   */
  async cancelGenerationJob(jobId: string): Promise<void> {
    await this.client.delete(`/constraints/jobs/${jobId}`);
  }

  /**
   * Get generation job status (for manual polling)
   */
  async getGenerationJobStatus(jobId: string): Promise<GenerationJobResponse> {
    const response = await this.client.get<GenerationJobResponse>(
      `/constraints/jobs/${jobId}`
    );
    return response.data;
  }

  /**
   * Get Deequ baseline constraint suggestions for a dataset.
   * These are purely data-driven suggestions (no LLM, no task code).
   */
  async getDeequSuggestions(datasetId: string): Promise<DeequSuggestionsResponse> {
    const response = await this.client.post<DeequSuggestionsResponse>(
      '/constraints/deequ-suggestions',
      { datasetId },
    );
    return response.data;
  }

  // ========== Dataset Endpoints ==========

  /**
   * Get dataset preview (first N rows)
   */
  async getDatasetPreview(datasetId: string, limit: number = 10): Promise<DatasetPreview> {
    const response = await this.client.get<DatasetPreview>(
      `/datasets/${datasetId}/preview`,
      { params: { limit } }
    );
    return response.data;
  }

  /**
   * Get column statistics
   */
  async getColumnStats(datasetId: string, columnName: string): Promise<ColumnStatsResponse> {
    const response = await this.client.get<ColumnStatsResponse>(
      `/datasets/${datasetId}/columns/${columnName}/stats`
    );
    return response.data;
  }

  /**
   * Get overall data quality metrics
   */
  async getDataQualityMetrics(datasetId: string): Promise<DataQualityMetrics> {
    const response = await this.client.get<DataQualityMetrics>(
      `/datasets/${datasetId}/quality`
    );
    return response.data;
  }

  /**
   * Validate a single constraint against the dataset
   */
  async validateConstraint(
    datasetId: string,
    request: ValidateConstraintRequest,
  ): Promise<ValidateConstraintResponse> {
    const response = await this.client.post<ValidateConstraintResponse>(
      `/datasets/${datasetId}/validate-constraint`,
      request,
    );
    return response.data;
  }

  // ========== Export Endpoints ==========

  /**
   * Export constraints in specified format
   * Returns a Blob that can be downloaded
   */
  async exportConstraints(request: ExportConstraintsRequest): Promise<Blob> {
    const response = await this.client.post<Blob>('/constraints/export', request, {
      responseType: 'blob',
    });

    return response.data;
  }

  /**
   * Helper to download exported constraints
   */
  downloadExport(blob: Blob, format: ExportFormat) {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;

    // Set filename based on format
    const extensions: Record<ExportFormat, string> = {
      great_expectations: 'py',
      deequ: 'scala',
      json: 'json',
    };
    link.download = `prismadv_constraints.${extensions[format]}`;

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  // ========== Project Management Endpoints (Optional) ==========

  /**
   * Save current project state
   */
  async saveProject(request: SaveProjectRequest): Promise<Project> {
    const response = await this.client.post<Project>('/projects', request);
    return response.data;
  }

  /**
   * List recent projects
   */
  async listProjects(limit: number = 10): Promise<Project[]> {
    const response = await this.client.get<{ projects: Project[] }>('/projects', {
      params: { limit },
    });
    return response.data.projects;
  }

  /**
   * Load a saved project
   */
  async loadProject(projectId: string): Promise<Project> {
    const response = await this.client.get<Project>(`/projects/${projectId}`);
    return response.data;
  }

  // ========== EIDBench ==========

  /**
   * List available EIDBench datasets and their scripts.
   * Returns an empty list if the backend has no EIDBENCH_PATH configured.
   */
  async getEIDBenchDatasets(): Promise<EIDBenchListResponse> {
    try {
      const response = await this.client.get<EIDBenchListResponse>('/examples/eidbench');
      return response.data;
    } catch {
      return { datasets: [] };
    }
  }

  /**
   * Load a specific EIDBench dataset + script into the current session.
   */
  async loadEIDBenchData(dataset: string, script: string): Promise<{
    taskFile: CodeFile;
    dataset: Dataset;
  }> {
    const response = await this.client.post<{
      task_file_id: string;
      dataset_id: string;
    }>('/examples/eidbench/load', { dataset, script });

    const { task_file_id, dataset_id } = response.data;

    const [taskFile, datasetFile] = await Promise.all([
      this.client.get<CodeFile>(`/files/${task_file_id}`).then((r) => r.data),
      this.client.get<Dataset>(`/files/${dataset_id}`).then((r) => r.data),
    ]);

    return { taskFile, dataset: datasetFile };
  }

  // ========== Optimization Endpoints ==========

  async getPrompts(): Promise<PromptsResponse> {
    const response = await this.client.get<PromptsResponse>('/optimization/prompts');
    return response.data;
  }

  async startOptimization(request: OptimizationRequest): Promise<OptimizationJobStatus> {
    const response = await this.client.post<OptimizationJobStatus>('/optimization/run', request);
    return response.data;
  }

  async getOptimizationJob(jobId: string): Promise<OptimizationJobStatus> {
    const response = await this.client.get<OptimizationJobStatus>(`/optimization/jobs/${jobId}`);
    return response.data;
  }

  async cancelOptimizationJob(jobId: string): Promise<void> {
    await this.client.post(`/optimization/jobs/${jobId}/cancel`);
  }

  async applyOptimizedPrompts(jobId: string): Promise<void> {
    await this.client.post('/optimization/apply', null, { params: { job_id: jobId } });
  }

  async resetPrompts(): Promise<void> {
    await this.client.post('/optimization/reset');
  }

  // ========== Cached Optimization Runs ==========

  async getCachedRuns(): Promise<CachedRunListResponse> {
    const response = await this.client.get<CachedRunListResponse>('/optimization/cached-runs');
    return response.data;
  }

  async getCachedRunDetail(runId: string): Promise<CachedRunDetail> {
    const response = await this.client.get<CachedRunDetail>(`/optimization/cached-runs/${runId}`);
    return response.data;
  }

  async applyCachedRun(runId: string): Promise<void> {
    await this.client.post(`/optimization/cached-runs/${runId}/apply`);
  }

  async getDatasetInfo(dataset: string): Promise<{ dataset: string; scripts: string[]; errorConfigs: string[] }> {
    const response = await this.client.get(`/optimization/cached-runs/dataset-info/${dataset}`);
    return response.data;
  }

  async getErrorConfig(runId: string, configId: string): Promise<{ configId: string; dataset: string; content: string }> {
    const response = await this.client.get(`/optimization/cached-runs/${runId}/error-config/${configId}`);
    return response.data;
  }

  // Error-batch benchmark
  async startErrorBenchmark(
    datasetName: string,
    taskName: string,
    prismadvConstraints: { id: string; deequCode: string }[],
    deequSuggestions: { id: string; deequCode: string }[],
  ): Promise<ErrorBenchmarkJobStatus> {
    const response = await this.client.post<ErrorBenchmarkJobStatus>(
      '/constraints/error-benchmark',
      { datasetName, taskName, prismadvConstraints, deequSuggestions },
    );
    return response.data;
  }

  async getErrorBenchmarkJob(jobId: string): Promise<ErrorBenchmarkJobStatus> {
    const response = await this.client.get<ErrorBenchmarkJobStatus>(
      `/constraints/error-benchmark/jobs/${jobId}`,
    );
    return response.data;
  }

}

// Create singleton instance
export const apiClient = new PrismaDVClient();

// Export for testing/mocking
export default apiClient;
