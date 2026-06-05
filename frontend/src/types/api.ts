// Core Types
export type ColumnType = "textual" | "numerical" | "categorical";

export type ConstraintType =
  | "completeness"
  | "format"
  | "range"
  | "statistical"
  | "enum"
  | "uniqueness"
  | "relationship";

export type InferredType = "string" | "integer" | "float" | "boolean" | "date";

export type Language = "python" | "sql";

export type ExportFormat = "great_expectations" | "deequ" | "json";

export type JobStatus = "pending" | "processing" | "completed" | "failed" | "cancelled";

// File Models
export interface CodeFile {
  id: string;
  name: string;
  language: Language;
  size: number;
  content: string;
  uploadedAt: string;
}

export interface Column {
  name: string;
  type: InferredType;
  inferredType: ColumnType;
  nullable: boolean;
}

export interface Dataset {
  id: string;
  name: string;
  size: number;
  rowCount: number;
  columnCount: number;
  columns: Column[];
  uploadedAt: string;
}

// Constraint Models
export interface Assumption {
  text: string;
  sourceCodeLines: number[];
  sourceFile: string;
}

/** Standalone assumption as returned in GenerationResult.assumptions */
export interface AssumptionItem {
  id: string;
  text: string;
  column: string;
  columns: string[];
  sourceCodeLines: number[];
  constraintIds: string[];
}

export interface ConstraintCode {
  greatExpectations: string;
  deequ: string;
}

export interface Constraint {
  id: string;
  column: string;
  type: ConstraintType;
  columnType: ColumnType;
  label: string;
  enabled: boolean;
  code: ConstraintCode;
  assumption: Assumption;
  assumptionId?: string;
  dataStats?: TextualColumnStats | NumericalColumnStats | CategoricalColumnStats;
}

// Flow Graph Models
export type NodeType = "data" | "code" | "assumption" | "constraint";

export interface Node {
  id: string;
  type: NodeType;
  label: string;
  columnType?: ColumnType;
  constraintId?: string;
  assumptionId?: string;
  position: { x: number; y: number };
}

export interface Edge {
  id: string;
  source: string;
  target: string;
  label?: string;
}

export interface FlowGraphData {
  nodes: Node[];
  edges: Edge[];
}

// Code Annotations
export interface CodeAnnotation {
  lineNumber: number;
  type: ConstraintType;
  columnType: ColumnType;
  column: string;
  constraintIds: string[];
  highlight: boolean;
}

// Column Statistics
export interface ColumnStatsBase {
  count: number;
  nullCount: number;
  nullPercentage: number;
  uniqueCount: number;
  constraintIds: string[];
}

export interface TextualColumnStats extends ColumnStatsBase {
  avgLength: number;
  minLength: number;
  maxLength: number;
  lengthDistribution: Record<string, number>;
  sampleValues: string[];
  pattern?: string;
  completeness: number;
}

export interface NumericalColumnStats extends ColumnStatsBase {
  min: number;
  max: number;
  mean: number;
  median: number;
  mode?: number;
  stdDev: number;
  q1: number;
  q3: number;
  distribution: Record<string, number>;
  outliers: number[];
}

export interface CategoricalColumnStats extends ColumnStatsBase {
  uniqueValues: string[];
  distribution: Record<string, number>;
}

export type ColumnStats = TextualColumnStats | NumericalColumnStats | CategoricalColumnStats;

export interface ColumnStatsResponse {
  datasetId: string;
  columnName: string;
  type: InferredType;
  inferredType: ColumnType;
  stats: ColumnStats;
}

// Data Quality Metrics
export interface DataQualityMetrics {
  datasetId: string;
  metrics: {
    completeness: number;
    validity: number;
    constraintCount: number;
    activeConstraints: number;
    disabledConstraints: number;
    violationCount: number;
    violationsByConstraint: Record<string, number>;
    validationMessages?: Record<string, string>;
    overallHealth: "healthy" | "warning" | "issues";
  };
}

// API Response Models
export interface DatasetPreview {
  datasetId: string;
  name: string;
  columns: Column[];
  rows: Record<string, any>[];
  totalRows: number;
}

export interface CostBreakdown {
  columnDetection: number;
  dataFlowDetection: number;
  assumptionExtraction: number;
  constraintGeneration: number;
}

export interface GenerationStatistics {
  constraintCount: number;
  assumptionCount: number;
  codeLinesCovered: number;
  columnsCovered: number;
  processingTimeMs: number;
  llmCost: number;
  warnings: string[];
  costBreakdown?: CostBreakdown;
}

export interface GenerationResult {
  constraints: Constraint[];
  assumptions: AssumptionItem[];
  flowGraph: FlowGraphData;
  codeAnnotations: CodeAnnotation[];
  statistics: GenerationStatistics;
  cached?: boolean;
}

export interface GenerationJobResponse {
  jobId: string;
  status: JobStatus;
  progress: number;
  currentStep: string;
  cached?: boolean;
  startedAt?: string;
  completedAt?: string;
  error?: string;
  result?: GenerationResult;
  intermediateResult?: GenerationResult;
}

// Column Detection
export interface DetectColumnsRequest {
  taskFileId: string;
  datasetId: string;
  options?: {
    llmProvider?: 'openai' | 'anthropic' | 'local';
    model?: string;
    apiKey?: string;
  };
  forceRedetect?: boolean;
}

export interface DetectColumnsResponse {
  allColumns: string[];
  accessedColumns: string[];
  cached?: boolean;
}

// Request Models
export interface GenerateConstraintsRequest {
  taskFileId: string;
  datasetId: string;
  options?: {
    llmProvider?: "openai" | "anthropic" | "local";
    model?: string;
    maxParallelCalls?: number;
    forceRegenerate?: boolean;
    selectedColumns?: string[];
  };
}

export interface ExportConstraintsRequest {
  constraintIds?: string[];
  format: ExportFormat;
}

export interface SaveProjectRequest {
  name: string;
  taskFileId: string;
  datasetId: string;
  constraintIds: string[];
}

export interface Project {
  id: string;
  name: string;
  taskFile?: CodeFile;
  dataset?: Dataset;
  constraints?: Constraint[];
  createdAt: string;
  updatedAt: string;
}

// EIDBench
export interface EIDBenchDataset {
  name: string;
  displayName: string;
  csvFile: string;
  scripts: string[];
  description?: string;
  domain?: string;
  source?: string;
}

export interface EIDBenchListResponse {
  datasets: EIDBenchDataset[];
}

// Optimization
export interface PromptInstructions {
  columnAccess: string;
  assumptionExtraction: string;
  constraintGeneration: string;
}

export interface OptimizationLLMOptions {
  llmProvider?: string;
  model?: string;
  proposerModel?: string;
  apiKey?: string;
}

export interface OptimizationRequest {
  dataset?: string;
  nRounds?: number;
  nTrain?: number;
  budget?: number;
  maxUnits?: number;
  options?: OptimizationLLMOptions;
}

export interface OptimizationJobResult {
  beforeInstructions: PromptInstructions;
  afterInstructions: PromptInstructions;
  evalScoreBefore: number;
  evalScoreAfter: number;
  improved: boolean;
  nRoundsCompleted: number;
  llmCost: number;
}

export interface OptimizationJobStatus {
  jobId: string;
  status: JobStatus;
  progress: number;
  currentStep: string;
  stepLog: string[];
  result?: OptimizationJobResult;
}

export interface PromptsResponse {
  current: PromptInstructions;
  optimized?: PromptInstructions;
  optimizationActive: boolean;
}

// Cached Optimization Runs
export interface CachedRunSummary {
  runId: string;
  timestamp: string;
  llmName: string;
  reflectionLlmName?: string;
  baselineType?: string;
  metricType?: string;
  trainDataset: string;
  maxRounds: number;
  initialScore: number;
  finalScore: number;
  improved: boolean;
}

export interface CachedRunListResponse {
  runs: CachedRunSummary[];
}

export interface OptimizationConfig {
  executionLlm: string;
  proposerLlm?: string;
  maxRounds: number;
  trainScripts: string[];
  evalScripts: string[];
  testScripts: string[];
  trainErrorConfigs: string[];
  testErrorConfigs: string[];
}

export interface CachedRunDetail {
  runId: string;
  timestamp: string;
  llmName: string;
  trainDataset: string;
  initialScore: number;
  finalScore: number;
  baselineInstructions: PromptInstructions;
  optimizedInstructions: PromptInstructions;
  config: OptimizationConfig;
}

// Deequ Baseline Suggestions
export interface DeequSuggestion {
  id: string;
  /** Column name, or "_dataset_" for dataset-level constraints (e.g. hasSize). */
  column: string;
  constraintType: ConstraintType;
  deequCode: string;
  description: string;
}

export interface DeequSuggestionsResponse {
  datasetId: string;
  suggestions: DeequSuggestion[];
}

// Single-constraint validation
export interface ValidateConstraintRequest {
  constraintId: string;
  column: string;
  backend: 'great_expectations' | 'deequ';
  greatExpectationsCode?: string;
  deequCode?: string;
}

export interface ValidateConstraintResponse {
  constraintId: string;
  backend: string;
  status: 'passed' | 'failed' | 'error';
  message: string;
  error?: string;
  durationMs: number;
}

// Error-batch benchmark (PrismaDV vs Deequ)
export interface BatchResult {
  batchId: string;
  errorDescription: string;
  harmful: boolean;
  prismadvViolations: number;
  prismadvTotal: number;
  deequViolations: number;
  deequTotal: number;
}

export interface ErrorBenchmarkResult {
  datasetName: string;
  totalBatches: number;
  prismadvConstraintCount: number;
  deequSuggestionCount: number;
  batches: BatchResult[];
  prismadvDetectionRate: number;
  deequDetectionRate: number;
  prismadvFalseAlarmRate: number;
  deequFalseAlarmRate: number;
  prismadvCleanViolations: number;
  deequCleanViolations: number;
}

export interface ErrorBenchmarkJobStatus {
  jobId: string;
  status: string;
  progress: number;
  currentStep: string;
  result?: ErrorBenchmarkResult;
  error?: string;
}

// Error Response
export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
  };
}
