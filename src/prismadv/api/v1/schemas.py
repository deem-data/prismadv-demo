from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# Health thresholds used by both the data-quality API endpoint and the CSV profiler.
HEALTH_COMPLETENESS_HEALTHY = 0.98
HEALTH_COMPLETENESS_WARNING = 0.90
HEALTH_VALIDITY_HEALTHY = 0.80
HEALTH_VALIDITY_WARNING = 0.60


def _to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:] if p)


class APIModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class CodeLanguage(StrEnum):
    PYTHON = "python"
    SQL = "sql"


class ColumnType(StrEnum):
    TEXTUAL = "textual"
    NUMERICAL = "numerical"
    CATEGORICAL = "categorical"


class ConstraintType(StrEnum):
    COMPLETENESS = "completeness"
    FORMAT = "format"
    RANGE = "range"
    STATISTICAL = "statistical"
    ENUM = "enum"
    UNIQUENESS = "uniqueness"
    RELATIONSHIP = "relationship"


class InferredType(StrEnum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"


class LLMProvider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


class GenerationStatus(StrEnum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OverallHealth(StrEnum):
    HEALTHY = "healthy"
    WARNING = "warning"
    ISSUES = "issues"


class ExportFormat(StrEnum):
    GREAT_EXPECTATIONS = "great_expectations"
    DEEQU = "deequ"
    JSON = "json"


class CodeFile(APIModel):
    id: str
    name: str
    language: CodeLanguage
    size: int
    content: str
    uploaded_at: datetime


class Column(APIModel):
    name: str
    type: InferredType
    inferred_type: ColumnType
    nullable: bool


class Dataset(APIModel):
    id: str
    name: str
    size: int
    row_count: int
    column_count: int
    columns: list[Column]
    uploaded_at: datetime


class ConstraintCode(APIModel):
    great_expectations: str
    deequ: str


class Assumption(APIModel):
    text: str
    source_code_lines: list[int]
    source_file: str


class AssumptionItem(APIModel):
    """A standalone assumption as returned in GenerationResult.assumptions.

    Unlike the embedded Assumption inside each Constraint (which is merged
    from multiple sources), this represents a single raw assumption extracted
    per column, with references to the constraints it drove.
    """
    id: str
    text: str
    column: str
    columns: list[str]
    source_code_lines: list[int]
    constraint_ids: list[str]


class Constraint(APIModel):
    id: str
    column: str
    type: ConstraintType
    column_type: ColumnType
    label: str
    enabled: bool
    code: ConstraintCode
    assumption: Assumption
    assumption_id: str | None = None
    data_stats: dict[str, Any] | None = None


class Position(APIModel):
    x: float
    y: float


class FlowNodeType(StrEnum):
    DATA = "data"
    CODE = "code"
    ASSUMPTION = "assumption"
    CONSTRAINT = "constraint"


class FlowNode(APIModel):
    id: str
    type: FlowNodeType
    label: str
    column_type: ColumnType | None = None
    constraint_id: str | None = None
    assumption_id: str | None = None
    position: Position


class FlowEdge(APIModel):
    id: str
    source: str
    target: str
    label: str | None = None


class FlowGraphData(APIModel):
    nodes: list[FlowNode]
    edges: list[FlowEdge]


class CodeAnnotation(APIModel):
    line_number: int
    type: ConstraintType
    column_type: ColumnType
    column: str
    constraint_ids: list[str]
    highlight: bool


class CostBreakdown(APIModel):
    column_detection: float = 0.0
    data_flow_detection: float = 0.0
    assumption_extraction: float = 0.0
    constraint_generation: float = 0.0


class GenerationStatistics(APIModel):
    constraint_count: int
    assumption_count: int
    code_lines_covered: int
    columns_covered: int
    processing_time_ms: int
    llm_cost: float
    warnings: list[str] = []
    cost_breakdown: CostBreakdown = Field(default_factory=CostBreakdown)


class GenerationResult(APIModel):
    constraints: list[Constraint]
    assumptions: list[AssumptionItem] = []
    flow_graph: FlowGraphData
    code_annotations: list[CodeAnnotation]
    statistics: GenerationStatistics


class GenerateConstraintsOptions(APIModel):
    llm_provider: LLMProvider | None = None
    model: str | None = None
    api_key: str | None = None
    force_regenerate: bool = Field(
        default=False,
        description="Skip cache and force regeneration even if cached result exists",
    )
    max_parallel_calls: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of concurrent LLM calls during generation",
    )
    selected_columns: list[str] | None = Field(
        default=None,
        description="If provided, skip LLM column detection and use these columns directly",
    )


class DetectColumnsRequest(APIModel):
    task_file_id: str
    dataset_id: str
    options: GenerateConstraintsOptions | None = None
    force_redetect: bool = False


class DetectColumnsResponse(APIModel):
    all_columns: list[str]
    accessed_columns: list[str]
    cached: bool = False


class GenerateConstraintsRequest(APIModel):
    task_file_id: str
    dataset_id: str
    options: GenerateConstraintsOptions | None = None


class GenerateConstraintsResponse(APIModel):
    job_id: str
    status: GenerationStatus
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    current_step: str = "Initializing..."
    cached: bool = Field(default=False, description="Whether result came from cache")
    result: GenerationResult | None = None
    intermediate_result: dict | None = Field(default=None, description="Partial result during processing for progressive UI")


class GetJobStatusResponse(APIModel):
    job_id: str
    status: JobStatus
    progress: float = Field(ge=0.0, le=1.0)
    current_step: str
    started_at: datetime
    completed_at: datetime | None = None
    error: str | None = None


class DatasetPreviewColumn(APIModel):
    name: str
    type: InferredType
    inferred_type: ColumnType


class DatasetPreviewResponse(APIModel):
    dataset_id: str
    name: str
    columns: list[DatasetPreviewColumn]
    rows: list[dict[str, Any]]
    total_rows: int


class ColumnStatsBase(APIModel):
    count: int
    null_count: int
    null_percentage: float
    unique_count: int
    constraint_ids: list[str]


class TextualColumnStats(ColumnStatsBase):
    avg_length: float
    min_length: int
    max_length: int
    length_distribution: dict[str, int]
    sample_values: list[str]
    pattern: str | None = None
    completeness: float


class NumericalColumnStats(ColumnStatsBase):
    min: float
    max: float
    mean: float
    median: float
    mode: float | None = None
    std_dev: float
    q1: float
    q3: float
    distribution: dict[str, int]
    outliers: list[float]


class CategoricalColumnStats(ColumnStatsBase):
    unique_values: list[str]
    distribution: dict[str, int]


class ColumnStatsResponseBase(APIModel):
    dataset_id: str
    column_name: str
    type: InferredType


class TextualColumnStatsResponse(ColumnStatsResponseBase):
    inferred_type: Literal[ColumnType.TEXTUAL] = ColumnType.TEXTUAL
    stats: TextualColumnStats


class NumericalColumnStatsResponse(ColumnStatsResponseBase):
    inferred_type: Literal[ColumnType.NUMERICAL] = ColumnType.NUMERICAL
    stats: NumericalColumnStats


class CategoricalColumnStatsResponse(ColumnStatsResponseBase):
    inferred_type: Literal[ColumnType.CATEGORICAL] = ColumnType.CATEGORICAL
    stats: CategoricalColumnStats


ColumnStatsResponse = TextualColumnStatsResponse | NumericalColumnStatsResponse | CategoricalColumnStatsResponse


class DataQualityMetrics(APIModel):
    completeness: float
    validity: float
    constraint_count: int
    active_constraints: int
    disabled_constraints: int
    violation_count: int
    violations_by_constraint: dict[str, int]
    validation_messages: dict[str, str] = {}
    overall_health: OverallHealth


class DatasetQualityResponse(APIModel):
    dataset_id: str
    metrics: DataQualityMetrics


class ValidateConstraintRequest(APIModel):
    constraint_id: str
    column: str
    backend: str = "great_expectations"  # "great_expectations" or "deequ"
    great_expectations_code: str = ""
    deequ_code: str = ""


class ValidateConstraintResponse(APIModel):
    constraint_id: str
    backend: str
    status: str  # "passed", "failed", "error"
    message: str = ""
    error: str | None = None
    duration_ms: int = 0


class ExistingConstraintCode(APIModel):
    great_expectations: str = ""
    deequ: str = ""


class GenerateFromAssumptionRequest(APIModel):
    assumption_text: str
    column: str
    task_file_id: str
    dataset_id: str
    options: GenerateConstraintsOptions | None = None
    existing_constraints: list[ExistingConstraintCode] | None = None


class GenerateFromAssumptionResponse(APIModel):
    constraints: list[Constraint]
    message: str | None = None


class ExportConstraintsRequest(APIModel):
    constraint_ids: list[str] | None = None
    format: ExportFormat


class SaveProjectRequest(APIModel):
    name: str
    task_file_id: str
    dataset_id: str
    constraint_ids: list[str]


class ProjectSummary(APIModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime


class ListProjectsResponse(APIModel):
    projects: list[ProjectSummary]


class ProjectDetailResponse(ProjectSummary):
    task_file: CodeFile
    dataset: Dataset
    constraints: list[Constraint]


# ---------------------------------------------------------------------------
# Optimization schemas
# ---------------------------------------------------------------------------

class PromptInstructions(APIModel):
    """Current instruction texts for the three generation modules."""
    column_access: str
    assumption_extraction: str
    constraint_generation: str


class OptimizationLLMOptions(APIModel):
    llm_provider: str | None = None
    model: str | None = None
    proposer_model: str | None = None
    api_key: str | None = None


class OptimizationRequest(APIModel):
    dataset: str = "sleep_health"
    n_rounds: int = Field(default=3, ge=1, le=5)
    n_train: int = Field(default=3, ge=1, le=10)
    budget: int = Field(default=3, ge=1, le=20)
    max_units: int = Field(default=40, ge=5, le=200)
    options: OptimizationLLMOptions | None = None


class OptimizationJobResult(APIModel):
    before_instructions: PromptInstructions
    after_instructions: PromptInstructions
    eval_score_before: float
    eval_score_after: float
    improved: bool
    n_rounds_completed: int
    llm_cost: float = 0.0


class OptimizationJobStatus(APIModel):
    job_id: str
    status: GenerationStatus
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    current_step: str = "Initializing..."
    step_log: list[str] = Field(default_factory=list)
    result: OptimizationJobResult | None = None


class PromptsResponse(APIModel):
    """Current and (if any) active optimized instructions."""
    current: PromptInstructions
    optimized: PromptInstructions | None = None
    optimization_active: bool = False


# ---------------------------------------------------------------------------
# Cached optimization runs
# ---------------------------------------------------------------------------

class CachedRunSummary(APIModel):
    """Summary of a pre-computed GEPA optimization run."""
    run_id: str
    timestamp: str
    llm_name: str
    reflection_llm_name: str | None = None
    baseline_type: str | None = None
    metric_type: str | None = None
    train_dataset: str
    max_rounds: int
    initial_score: float
    final_score: float
    improved: bool


class CachedRunListResponse(APIModel):
    runs: list[CachedRunSummary]


class OptimizationConfig(APIModel):
    """Configuration details of a GEPA optimization run."""
    execution_llm: str
    proposer_llm: str | None = None
    max_rounds: int = 1
    train_scripts: list[str] = []
    eval_scripts: list[str] = []
    test_scripts: list[str] = []
    train_error_configs: list[str] = []
    test_error_configs: list[str] = []


class CachedRunDetail(APIModel):
    """Full detail of a cached run including before/after instructions."""
    run_id: str
    timestamp: str
    llm_name: str
    train_dataset: str
    initial_score: float
    final_score: float
    baseline_instructions: PromptInstructions
    optimized_instructions: PromptInstructions
    config: OptimizationConfig


# ---------------------------------------------------------------------------


class DeequSuggestion(APIModel):
    """A single constraint suggestion produced by the Deequ baseline suggester."""

    id: str
    column: str
    constraint_type: ConstraintType
    deequ_code: str
    description: str


class DeequSuggestionsRequest(APIModel):
    dataset_id: str


class DeequSuggestionsResponse(APIModel):
    dataset_id: str
    suggestions: list[DeequSuggestion]


class APIErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    RATE_LIMIT = "RATE_LIMIT"
    GENERATION_FAILED = "GENERATION_FAILED"


class APIErrorDetails(APIModel):
    field: str | None = None
    reason: str | None = None


class APIError(APIModel):
    code: APIErrorCode
    message: str
    details: APIErrorDetails | None = None


class ErrorResponse(APIModel):
    error: APIError


# ---------------------------------------------------------------------------
# Error-batch benchmark (PrismaDV vs Deequ)
# ---------------------------------------------------------------------------


class ErrorBenchmarkConstraintCode(APIModel):
    id: str
    deequ_code: str


class ErrorBenchmarkRequest(APIModel):
    dataset_name: str  # EIDBench dataset name (e.g. "hr_analytics")
    task_name: str  # EIDBench task/script name (e.g. "general_task_1")
    prismadv_constraints: list[ErrorBenchmarkConstraintCode]
    deequ_suggestions: list[ErrorBenchmarkConstraintCode]
    sample_rows: int | None = None


class BatchResult(APIModel):
    batch_id: str
    error_description: str
    harmful: bool  # True = error actually affects the task (ground truth)
    prismadv_violations: int
    prismadv_total: int
    deequ_violations: int
    deequ_total: int


class ErrorBenchmarkResult(APIModel):
    dataset_name: str
    total_batches: int  # only harmful batches
    prismadv_constraint_count: int
    deequ_suggestion_count: int
    batches: list[BatchResult]
    prismadv_detection_rate: float  # % of harmful batches detected
    deequ_detection_rate: float
    prismadv_false_alarm_rate: float  # % of non-harmful batches incorrectly flagged
    deequ_false_alarm_rate: float
    prismadv_clean_violations: int
    deequ_clean_violations: int


class ErrorBenchmarkJobStatus(APIModel):
    job_id: str
    status: str
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    current_step: str = ""
    result: ErrorBenchmarkResult | None = None
    error: str | None = None

