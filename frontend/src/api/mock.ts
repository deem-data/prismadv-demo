import type {
  CodeFile,
  Dataset,
  DatasetPreview,
  GenerationResult,
  Constraint,
  FlowGraphData,
  CodeAnnotation,
  TextualColumnStats,
  NumericalColumnStats,
  CategoricalColumnStats,
  DataQualityMetrics,
} from '@/types';

// Sample Python task code
export const MOCK_TASK_CODE = `def customer_analytics():
    """Generate customer analytics report."""
    # Load customer data
    df = load_data("customers.csv")

    # Filter by category
    premium_customers = df[df["category"] == "PREMIUM"]

    # Validate name completeness
    if premium_customers["name"].isnull().any():
        raise ValueError("Premium customers must have names")

    # Check age range for analysis
    valid_ages = premium_customers[
        (premium_customers["age"] >= 18) &
        (premium_customers["age"] <= 65)
    ]

    # Calculate age statistics
    age_mean = valid_ages["age"].mean()
    age_std = valid_ages["age"].std()

    return generate_report(valid_ages, age_mean, age_std)`;

// Mock CodeFile
export const mockCodeFile: CodeFile = {
  id: 'task-file-1',
  name: 'customer_analytics.py',
  language: 'python',
  size: MOCK_TASK_CODE.length,
  content: MOCK_TASK_CODE,
  uploadedAt: new Date().toISOString(),
};

// Mock Dataset
export const mockDataset: Dataset = {
  id: 'dataset-1',
  name: 'customers.csv',
  size: 524288,
  rowCount: 1000,
  columnCount: 5,
  columns: [
    { name: 'id', type: 'integer', inferredType: 'numerical', nullable: false },
    { name: 'name', type: 'string', inferredType: 'textual', nullable: false },
    { name: 'age', type: 'integer', inferredType: 'numerical', nullable: true },
    { name: 'category', type: 'string', inferredType: 'categorical', nullable: false },
    { name: 'description', type: 'string', inferredType: 'textual', nullable: true },
  ],
  uploadedAt: new Date().toISOString(),
};

// Mock Dataset Preview
export const mockDatasetPreview: DatasetPreview = {
  datasetId: 'dataset-1',
  name: 'customers.csv',
  columns: mockDataset.columns,
  rows: [
    { id: 1, name: 'Alice Smith', age: 28, category: 'PREMIUM', description: 'Regular customer' },
    { id: 2, name: 'Bob Jones', age: 35, category: 'STANDARD', description: 'New customer' },
    { id: 3, name: 'Carol White', age: 42, category: 'PREMIUM', description: 'VIP member' },
    { id: 4, name: 'David Brown', age: 31, category: 'STANDARD', description: 'Regular customer' },
    { id: 5, name: 'Eve Davis', age: 29, category: 'PREMIUM', description: 'Long-term member' },
    { id: 6, name: 'Frank Miller', age: 45, category: 'BASIC', description: 'Occasional buyer' },
    { id: 7, name: 'Grace Wilson', age: 38, category: 'PREMIUM', description: 'Loyal customer' },
    { id: 8, name: 'Henry Moore', age: 52, category: 'STANDARD', description: 'Active member' },
    { id: 9, name: 'Iris Taylor', age: 26, category: 'BASIC', description: 'New member' },
    { id: 10, name: 'Jack Anderson', age: 41, category: 'PREMIUM', description: 'VIP customer' },
  ],
  totalRows: 1000,
};

// Mock Constraints
export const mockConstraints: Constraint[] = [
  {
    id: 'constraint-1',
    column: 'name',
    type: 'completeness',
    columnType: 'textual',
    label: 'name (Completeness)',
    enabled: true,
    code: {
      greatExpectations: `validator.expect_column_values_to_not_be_null(column="name")`,
      deequ: `Check(df, CheckLevel.Error).isComplete("name")`,
    },
    assumption: {
      text: 'Inferred from code analysis that premium customers must have complete name values. The null check on line 10 indicates name is required for premium category customers in the analytics workflow.',
      sourceCodeLines: [10, 11],
      sourceFile: 'customer_analytics.py',
    },
  },
  {
    id: 'constraint-2',
    column: 'name',
    type: 'format',
    columnType: 'textual',
    label: 'name (Format)',
    enabled: true,
    code: {
      greatExpectations: `validator.expect_column_values_to_match_regex(column="name", regex="^[A-Za-z\\\\s]+$")`,
      deequ: `Check(df, CheckLevel.Error).hasPattern("name", "^[A-Za-z\\\\s]+$".r)`,
    },
    assumption: {
      text: 'Names appear to follow alphabetic pattern with spaces. No special characters observed in sample data.',
      sourceCodeLines: [],
      sourceFile: 'customer_analytics.py',
    },
  },
  {
    id: 'constraint-3',
    column: 'age',
    type: 'range',
    columnType: 'numerical',
    label: 'age (Range)',
    enabled: true,
    code: {
      greatExpectations: `validator.expect_column_values_to_be_between(column="age", min_value=18, max_value=65)`,
      deequ: `Check(df, CheckLevel.Error).isContainedIn("age", 18.0, 65.0)`,
    },
    assumption: {
      text: 'Age range constraint inferred from filtering logic on lines 15-16. Code filters for ages between 18 and 65 for valid analysis.',
      sourceCodeLines: [15, 16],
      sourceFile: 'customer_analytics.py',
    },
  },
  {
    id: 'constraint-4',
    column: 'age',
    type: 'statistical',
    columnType: 'numerical',
    label: 'age (Statistical)',
    enabled: true,
    code: {
      greatExpectations: `validator.expect_column_mean_to_be_between(column="age", min_value=30, max_value=50)`,
      deequ: `Check(df, CheckLevel.Error).hasMin("age", _ >= 30).hasMax("age", _ <= 50)`,
    },
    assumption: {
      text: 'Statistical analysis performed on age column suggests mean and standard deviation are used for insights.',
      sourceCodeLines: [20, 21],
      sourceFile: 'customer_analytics.py',
    },
  },
  {
    id: 'constraint-5',
    column: 'category',
    type: 'enum',
    columnType: 'categorical',
    label: 'category (Enum)',
    enabled: true,
    code: {
      greatExpectations: `validator.expect_column_values_to_be_in_set(column="category", value_set=["PREMIUM", "STANDARD", "BASIC"])`,
      deequ: `Check(df, CheckLevel.Error).isContainedIn("category", Array("PREMIUM", "STANDARD", "BASIC"))`,
    },
    assumption: {
      text: 'Categorical values inferred from filtering on line 7. Code expects category to be "PREMIUM" for this analysis branch. Other categories found in data: STANDARD, BASIC.',
      sourceCodeLines: [7],
      sourceFile: 'customer_analytics.py',
    },
  },
];

// Mock Code Annotations
export const mockCodeAnnotations: CodeAnnotation[] = [
  {
    lineNumber: 7,
    type: 'enum',
    columnType: 'categorical',
    column: 'category',
    constraintIds: ['constraint-5'],
    highlight: true,
  },
  {
    lineNumber: 10,
    type: 'completeness',
    columnType: 'textual',
    column: 'name',
    constraintIds: ['constraint-1'],
    highlight: true,
  },
  {
    lineNumber: 15,
    type: 'range',
    columnType: 'numerical',
    column: 'age',
    constraintIds: ['constraint-3'],
    highlight: true,
  },
  {
    lineNumber: 16,
    type: 'range',
    columnType: 'numerical',
    column: 'age',
    constraintIds: ['constraint-3'],
    highlight: true,
  },
  {
    lineNumber: 20,
    type: 'statistical',
    columnType: 'numerical',
    column: 'age',
    constraintIds: ['constraint-4'],
    highlight: true,
  },
  {
    lineNumber: 21,
    type: 'statistical',
    columnType: 'numerical',
    column: 'age',
    constraintIds: ['constraint-4'],
    highlight: true,
  },
];

// Mock Flow Graph
export const mockFlowGraph: FlowGraphData = {
  nodes: [
    // Data nodes
    {
      id: 'data-name',
      type: 'data',
      label: 'name',
      columnType: 'textual',
      position: { x: 0, y: 0 },
    },
    {
      id: 'data-age',
      type: 'data',
      label: 'age',
      columnType: 'numerical',
      position: { x: 0, y: 100 },
    },
    {
      id: 'data-category',
      type: 'data',
      label: 'category',
      columnType: 'categorical',
      position: { x: 0, y: 200 },
    },
    // Code node
    {
      id: 'code-main',
      type: 'code',
      label: 'customer_analytics.py',
      position: { x: 200, y: 100 },
    },
    // Assumption nodes
    {
      id: 'assumption-1',
      type: 'assumption',
      label: 'Name Completeness',
      columnType: 'textual',
      position: { x: 400, y: 0 },
    },
    {
      id: 'assumption-2',
      type: 'assumption',
      label: 'Age Range',
      columnType: 'numerical',
      position: { x: 400, y: 100 },
    },
    {
      id: 'assumption-3',
      type: 'assumption',
      label: 'Category Enum',
      columnType: 'categorical',
      position: { x: 400, y: 200 },
    },
    // Constraint nodes
    {
      id: 'constraint-1',
      type: 'constraint',
      label: 'expect_column_values_to_not_be_null',
      columnType: 'textual',
      constraintId: 'constraint-1',
      position: { x: 600, y: 0 },
    },
    {
      id: 'constraint-3',
      type: 'constraint',
      label: 'expect_column_values_to_be_between',
      columnType: 'numerical',
      constraintId: 'constraint-3',
      position: { x: 600, y: 100 },
    },
    {
      id: 'constraint-5',
      type: 'constraint',
      label: 'expect_column_values_to_be_in_set',
      columnType: 'categorical',
      constraintId: 'constraint-5',
      position: { x: 600, y: 200 },
    },
  ],
  edges: [
    { id: 'e1', source: 'data-name', target: 'code-main' },
    { id: 'e2', source: 'data-age', target: 'code-main' },
    { id: 'e3', source: 'data-category', target: 'code-main' },
    { id: 'e4', source: 'code-main', target: 'assumption-1' },
    { id: 'e5', source: 'code-main', target: 'assumption-2' },
    { id: 'e6', source: 'code-main', target: 'assumption-3' },
    { id: 'e7', source: 'assumption-1', target: 'constraint-1' },
    { id: 'e8', source: 'assumption-2', target: 'constraint-3' },
    { id: 'e9', source: 'assumption-3', target: 'constraint-5' },
  ],
};

// Mock Column Stats
export const mockNameColumnStats: TextualColumnStats = {
  count: 1000,
  nullCount: 0,
  nullPercentage: 0,
  uniqueCount: 847,
  constraintIds: ['constraint-1', 'constraint-2'],
  avgLength: 12.3,
  minLength: 5,
  maxLength: 24,
  lengthDistribution: {
    '5': 12,
    '6': 45,
    '7': 89,
    '8': 123,
    '9': 156,
    '10': 178,
    '11': 134,
    '12': 98,
    '13': 67,
    '14': 45,
    '15': 32,
    '16': 21,
  },
  sampleValues: ['Alice Smith', 'Bob Jones', 'Carol White'],
  pattern: 'alphanumeric with spaces',
  completeness: 1.0,
};

export const mockAgeColumnStats: NumericalColumnStats = {
  count: 1000,
  nullCount: 15,
  nullPercentage: 0.015,
  uniqueCount: 48,
  constraintIds: ['constraint-3', 'constraint-4'],
  min: 18,
  max: 65,
  mean: 38.5,
  median: 37,
  mode: 35,
  stdDev: 12.3,
  q1: 28,
  q3: 48,
  distribution: {
    '18-25': 150,
    '26-35': 280,
    '36-45': 320,
    '46-55': 180,
    '56-65': 70,
  },
  outliers: [],
};

export const mockCategoryColumnStats: CategoricalColumnStats = {
  count: 1000,
  nullCount: 0,
  nullPercentage: 0,
  uniqueCount: 3,
  constraintIds: ['constraint-5'],
  uniqueValues: ['PREMIUM', 'STANDARD', 'BASIC'],
  distribution: {
    PREMIUM: 350,
    STANDARD: 450,
    BASIC: 200,
  },
};

// Mock Data Quality Metrics
export const mockDataQualityMetrics: DataQualityMetrics = {
  datasetId: 'dataset-1',
  metrics: {
    completeness: 0.98,
    validity: 0.95,
    constraintCount: 5,
    activeConstraints: 5,
    disabledConstraints: 0,
    violationCount: 12,
    violationsByConstraint: {
      'constraint-1': 0,
      'constraint-2': 2,
      'constraint-3': 5,
      'constraint-4': 3,
      'constraint-5': 2,
    },
    overallHealth: 'healthy',
  },
};

// Mock Generation Result
export const mockGenerationResult: GenerationResult = {
  constraints: mockConstraints,
  assumptions: [
    {
      id: 'assumption-1',
      text: 'The name column should contain non-empty string values representing customer names.',
      column: 'name',
      columns: ['name'],
      sourceCodeLines: [12, 15],
      constraintIds: ['constraint-1'],
    },
    {
      id: 'assumption-2',
      text: 'The age column should contain integer values within a realistic human age range (0–120).',
      column: 'age',
      columns: ['age'],
      sourceCodeLines: [18],
      constraintIds: ['constraint-2', 'constraint-3'],
    },
    {
      id: 'assumption-3',
      text: 'The category column should only contain values from a known set of product categories.',
      column: 'category',
      columns: ['category'],
      sourceCodeLines: [22, 24],
      constraintIds: ['constraint-4', 'constraint-5'],
    },
  ],
  flowGraph: mockFlowGraph,
  codeAnnotations: mockCodeAnnotations,
  statistics: {
    constraintCount: 5,
    assumptionCount: 3,
    codeLinesCovered: 6,
    columnsCovered: 3,
    processingTimeMs: 2500,
    llmCost: 0.05,
    warnings: [],
  },
};
