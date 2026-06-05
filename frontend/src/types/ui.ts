import type {
  CodeFile,
  Dataset,
  Constraint,
  ConstraintCode,
  FlowGraphData,
  CodeAnnotation,
  ColumnStats,
  DataQualityMetrics,
  CostBreakdown,
  GenerationResult,
  AssumptionItem,
  PromptInstructions,
  OptimizationRequest,
  CachedRunSummary,
  CachedRunDetail,
  DeequSuggestion,
  ValidateConstraintResponse,
  ErrorBenchmarkResult,
} from './api';

export interface CostRecord {
  id: string;
  timestamp: string;
  taskFileName: string;
  datasetName: string;
  totalCost: number;
  breakdown?: CostBreakdown;
}

// Panel Visibility
export interface PanelVisibility {
  data: boolean;
  constraints: boolean;
  flow: boolean;
}

export type PanelType = keyof PanelVisibility;

export type ThemePreference = "system" | "light" | "dark";

// UI State
export interface UIState {
  // Panel visibility
  leftSidebarCollapsed: boolean;
  rightSidebarCollapsed: boolean;
  bottomPanelCollapsed: boolean;

  // Section collapse states
  dataTableCollapsed: boolean;
  columnStatsCollapsed: boolean;
  dataQualityCollapsed: boolean;
  constraintListCollapsed: boolean;
  flowGraphCollapsed: boolean;

  // Panel sizes (for resizable panels)
  leftSidebarWidth: number;
  rightSidebarWidth: number;
  bottomPanelHeight: number;

  // Theme
  themePreference: ThemePreference;
}

// Selection State
export interface SelectionState {
  selectedConstraintId: string | null;
  selectedColumn: string | null;
  highlightedLines: number[];
  highlightedNodes: string[];
}

// Loading State
export interface LoadingState {
  isGenerating: boolean;
  generationProgress: number;
  currentStep: string;
}

// Toast Notification
export interface Toast {
  id: string;
  type: "success" | "error" | "warning" | "info";
  message: string;
  duration?: number;
}

// App State (combines all state slices)
export interface AppState {
  // Files
  taskFile: CodeFile | null;
  dataset: Dataset | null;

  // Constraints
  constraints: Constraint[];
  selectedConstraintId: string | null;

  // Assumptions
  assumptions: AssumptionItem[];
  selectedAssumptionId: string | null;
  generatingAssumptionId: string | null;
  selectAssumption: (id: string | null) => void;
  updateAssumptionText: (id: string, text: string) => void;
  addAssumption: (assumption: AssumptionItem) => void;
  deleteAssumption: (id: string) => void;
  generateConstraintsFromAssumption: (assumptionId: string) => Promise<void>;

  // Right sidebar tab
  sidebarTab: 'constraints' | 'assumptions';
  setSidebarTab: (tab: 'constraints' | 'assumptions') => void;

  // Code Editor
  code: string;
  codeEditable: boolean;
  constraintsSynced: boolean | null;
  highlightedLines: number[];
  annotations: Map<number, CodeAnnotation>;
  rawAnnotations: CodeAnnotation[];
  assumptionDisplayMode: 'all' | 'selected' | 'none';

  // Flow Graph
  flowGraph: FlowGraphData | null;
  highlightedNodes: string[];

  // Data
  selectedColumn: string | null;
  columnStats: Map<string, ColumnStats>;
  dataQualityMetrics: DataQualityMetrics | null;
  // Deequ validation results (per-constraint, separate from bulk GE metrics)
  deequValidationResults: Map<string, { status: 'pass' | 'fail' | 'error'; message?: string }>;

  // UI State
  ui: UIState;

  // LLM Settings
  llmSettings: {
    provider: 'openai' | 'anthropic' | 'gemini';
    model: string;
    useOwnKey: boolean;
    apiKey: string;
  };

  // Preferences
  preferences: {
    maxParallelCalls: number;
    autoSelectDetectedColumns: boolean;
    editorFontSize: number;
    editorWordWrap: boolean;
  };
  setPreferences: (patch: Partial<AppState['preferences']>) => void;

  // Execution
  detectedAccessedColumns: string[];
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

  // Optimization
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
  fetchCachedRuns: () => Promise<void>;
  selectCachedRun: (runId: string | null) => Promise<void>;
  applyCachedRun: () => Promise<void>;

  // Deequ Baseline Comparison
  deequSuggestions: DeequSuggestion[] | null;
  deequSuggestionsDatasetId: string | null;
  isLoadingDeequSuggestions: boolean;
  showDeequComparison: boolean;
  selectedDeequSuggestionId: string | null;
  fetchDeequSuggestions: () => Promise<void>;
  toggleDeequComparison: () => void;
  clearDeequSuggestions: () => void;
  selectDeequSuggestion: (id: string | null) => void;

  // Error-batch benchmark (PrismaDV vs Deequ)
  errorBenchmarkJobId: string | null;
  errorBenchmarkStatus: 'idle' | 'running' | 'completed' | 'failed';
  errorBenchmarkProgress: number;
  errorBenchmarkStep: string;
  errorBenchmarkResult: ErrorBenchmarkResult | null;
  startErrorBenchmark: () => Promise<void>;
  clearErrorBenchmark: () => void;

  // Toasts
  toasts: Toast[];

  // Actions
  uploadTaskFile: (file: File) => Promise<void>;
  uploadDataset: (file: File) => Promise<void>;
  generateConstraints: (forceRegenerate?: boolean, selectedColumns?: string[]) => Promise<void>;
  cancelGeneration: () => Promise<void>;
  startDetection: (controller: AbortController) => void;
  stopDetection: () => void;
  cancelDetection: () => void;
  minimizeOverlay: () => void;
  restoreOverlay: () => void;
  useCachedResult: () => void;
  dismissCacheDialog: () => void;
  selectConstraint: (id: string | null) => void;
  toggleConstraint: (id: string, enabled: boolean) => void;
  deleteConstraint: (id: string) => void;
  updateConstraint: (id: string, patch: { label?: string; code?: ConstraintCode }) => void;
  addConstraint: (constraint: Constraint) => void;
  validateConstraint: (constraintId: string, backend: 'great_expectations' | 'deequ') => Promise<ValidateConstraintResponse | null>;
  selectColumn: (column: string | null) => void;
  setCodeEditable: (editable: boolean) => void;
  setCode: (code: string) => void;
  setConstraintsSynced: (synced: boolean | null) => void;
  highlightCodeLine: (lineNumber: number) => void;
  scrollToLine: (lineNumber: number) => void;
  setAssumptionDisplayMode: (mode: 'all' | 'selected' | 'none') => void;
  togglePanel: (panel: PanelType) => void;
  setThemePreference: (themePreference: ThemePreference) => void;
  loadEIDBench: (dataset: string, script: string) => Promise<void>;
  loadQuickExample: () => Promise<void>;
  addToast: (toast: Omit<Toast, "id">) => void;
  removeToast: (id: string) => void;
  setLLMProvider: (provider: 'openai' | 'anthropic' | 'gemini') => void;
  setLLMModel: (model: string) => void;
  setUseOwnKey: (useOwnKey: boolean) => void;
  setAPIKey: (apiKey: string) => void;
  reset: () => void;
}

// Component Props Types
export interface HeaderProps {
  projectName?: string;
  cost?: number;
  onFileAction: (action: FileAction) => void;
  onEditAction: (action: EditAction) => void;
  panelVisibility: PanelVisibility;
  onTogglePanel: (panel: PanelType) => void;
}

export type FileAction =
  | { type: "upload-task"; file: File }
  | { type: "upload-dataset"; file: File }
  | { type: "save-project" };

export type EditAction =
  | { type: "preferences" }
  | { type: "theme" }
  | { type: "about" };

export interface ExportButtonProps {
  constraints: Constraint[];
  onExport: (format: string) => void;
}

export interface DataTablePreviewProps {
  dataset: Dataset | null;
  onColumnClick?: (column: string) => void;
  collapsed?: boolean;
}

export interface ColumnStatisticsProps {
  column: string | null;
  stats: ColumnStats | null;
  collapsed?: boolean;
  onConstraintClick?: (constraintId: string) => void;
}

export interface DataQualityMetricsProps {
  metrics: DataQualityMetrics | null;
  collapsed?: boolean;
}

export interface CodeEditorProps {
  code: string;
  language: string;
  highlightedLines?: number[];
  annotations?: Map<number, CodeAnnotation>;
  onLineClick?: (lineNumber: number) => void;
  onLineHover?: (lineNumber: number) => void;
  readOnly?: boolean;
}

export interface ConstraintListProps {
  constraints: Constraint[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  collapsed?: boolean;
}

export interface ConstraintDetailsProps {
  constraint: Constraint | null;
  onClose?: () => void;
}

export interface FlowGraphProps {
  data: FlowGraphData | null;
  highlightedNodes?: string[];
  onNodeClick: (nodeId: string) => void;
  collapsed?: boolean;
}

export interface LoadingOverlayProps {
  visible: boolean;
  progress: number;
  currentStep: string;
  onCancel: () => void;
}

// Menu Item Types
export interface MenuItem {
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
  divider?: boolean;
}

// Layout Constants
export const LAYOUT_DEFAULTS = {
  HEADER_HEIGHT: 44,
  LEFT_SIDEBAR_WIDTH: 280,
  RIGHT_SIDEBAR_WIDTH: 320,
  BOTTOM_PANEL_HEIGHT: 280,
  MIN_SIDEBAR_WIDTH: 200,
  MIN_PANEL_HEIGHT: 150,
} as const;
