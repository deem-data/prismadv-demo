import { useMemo, useState } from 'react';
import { ChevronDown, ChevronRight, CheckCircle2, AlertTriangle, AlertCircle, Hash, Type, Tag } from 'lucide-react';
import type { DataQualityMetrics as DataQualityMetricsType, Dataset } from '@/types';

interface DataQualityMetricsProps {
  metrics: DataQualityMetricsType | null;
  dataset: Dataset | null;
}

export function DataQualityMetrics({ metrics, dataset }: DataQualityMetricsProps) {
  const [collapsed, setCollapsed] = useState(false);

  // Compute column type breakdown from dataset columns
  const columnBreakdown = useMemo(() => {
    if (!dataset?.columns?.length) return null;
    const total = dataset.columns.length;
    let numerical = 0;
    let categorical = 0;
    let textual = 0;
    for (const col of dataset.columns) {
      switch (col.inferredType) {
        case 'numerical': numerical++; break;
        case 'categorical': categorical++; break;
        case 'textual': textual++; break;
      }
    }
    return { total, numerical, categorical, textual };
  }, [dataset]);

  // Need at least a dataset or metrics to render
  if (!metrics && !dataset) {
    return null;
  }

  const completeness = metrics?.metrics?.completeness;
  const percentage = completeness !== undefined ? Math.round(completeness * 100) : null;

  const getHealthIcon = () => {
    if (percentage === null) return <AlertCircle size={14} className="text-text-muted" />;
    if (percentage >= 90) return <CheckCircle2 size={14} className="text-accent-green" />;
    if (percentage >= 70) return <AlertTriangle size={14} className="text-accent-orange" />;
    return <AlertCircle size={14} className="text-red-500" />;
  };

  const getBarColor = () => {
    if (percentage === null) return 'bg-text-muted';
    if (percentage >= 90) return 'bg-accent-green';
    if (percentage >= 70) return 'bg-accent-orange';
    return 'bg-red-500';
  };

  const getIcon = () => {
    if (percentage === null) return '-';
    if (percentage >= 90) return '\u2713';
    if (percentage >= 70) return '\u26A0';
    return '\u2717';
  };

  return (
    <section className="bg-dark-light rounded-lg border border-dark-border overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center gap-2 p-3 hover:bg-dark-border/50 transition-colors text-left"
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronDown size={16} />}
        {getHealthIcon()}
        <span className="font-medium text-sm text-text-secondary flex-1">
          Data Statistics
        </span>
        {dataset && (
          <span className="text-[10px] text-text-muted">
            {dataset.rowCount} rows, {dataset.columnCount} cols
          </span>
        )}
      </button>

      {/* Content */}
      {!collapsed && (
        <div className="p-3 pt-0 space-y-3">
          {/* Completeness */}
          {percentage !== null && (
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-text-secondary flex items-center gap-1">
                  <span>{getIcon()}</span>
                  <span>Completeness:</span>
                </span>
                <span className="text-text-primary font-medium">{percentage}%</span>
              </div>
              <div className="h-1.5 bg-dark-border rounded-full overflow-hidden">
                <div
                  className={`h-full ${getBarColor()} transition-all duration-300`}
                  style={{ width: `${percentage}%` }}
                />
              </div>
              <p className="text-[10px] text-text-muted mt-1">Proportion of non-null values across all columns</p>
            </div>
          )}

          {/* Column Type Breakdown */}
          {columnBreakdown && (
            <div>
              <div className="flex justify-between text-xs mb-1.5">
                <span className="text-text-secondary">Column Types</span>
                <span className="text-text-muted">{columnBreakdown.total} total</span>
              </div>

              {/* Stacked bar */}
              <div className="flex h-2 rounded-full overflow-hidden bg-dark-border">
                {columnBreakdown.numerical > 0 && (
                  <div
                    className="bg-accent-numerical transition-all duration-300"
                    style={{ width: `${(columnBreakdown.numerical / columnBreakdown.total) * 100}%` }}
                  />
                )}
                {columnBreakdown.categorical > 0 && (
                  <div
                    className="bg-accent-categorical transition-all duration-300"
                    style={{ width: `${(columnBreakdown.categorical / columnBreakdown.total) * 100}%` }}
                  />
                )}
                {columnBreakdown.textual > 0 && (
                  <div
                    className="bg-accent-textual transition-all duration-300"
                    style={{ width: `${(columnBreakdown.textual / columnBreakdown.total) * 100}%` }}
                  />
                )}
              </div>

              {/* Legend */}
              <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1.5">
                {columnBreakdown.numerical > 0 && (
                  <span className="flex items-center gap-1 text-[10px] text-text-muted">
                    <Hash size={10} className="text-accent-numerical" />
                    {columnBreakdown.numerical} numerical
                  </span>
                )}
                {columnBreakdown.categorical > 0 && (
                  <span className="flex items-center gap-1 text-[10px] text-text-muted">
                    <Tag size={10} className="text-accent-categorical" />
                    {columnBreakdown.categorical} categorical
                  </span>
                )}
                {columnBreakdown.textual > 0 && (
                  <span className="flex items-center gap-1 text-[10px] text-text-muted">
                    <Type size={10} className="text-accent-textual" />
                    {columnBreakdown.textual} textual
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Dataset dimensions (shown when no metrics yet) */}
          {dataset && !metrics && (
            <div className="text-[10px] text-text-muted">
              Upload constraints to see quality metrics
            </div>
          )}
        </div>
      )}
    </section>
  );
}
