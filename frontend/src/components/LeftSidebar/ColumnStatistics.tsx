import { useState } from 'react';
import { ChevronDown, ChevronRight, BarChart3 } from 'lucide-react';
import type { ColumnStats } from '@/types';

interface ColumnStatisticsProps {
  column: string | null;
  stats: ColumnStats | null;
}

export function ColumnStatistics({ column, stats }: ColumnStatisticsProps) {
  const [collapsed, setCollapsed] = useState(false);

  if (!column || !stats) {
    return (
      <section className="bg-dark-light rounded-lg p-3 border border-dark-border">
        <div className="flex items-center gap-2 text-text-muted text-sm">
          <BarChart3 size={16} />
          <span>Select a column to view statistics</span>
        </div>
      </section>
    );
  }

  // Determine column type color
  const getColumnColorClassName = () => {
    if ('avgLength' in stats) return 'text-accent-textual';
    if ('mean' in stats) return 'text-accent-numerical';
    if ('uniqueValues' in stats) return 'text-accent-categorical';
    return 'text-text-muted';
  };

  const columnColorClassName = getColumnColorClassName();

  return (
    <section className="bg-dark-light rounded-lg border border-dark-border overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center gap-2 p-3 hover:bg-dark-border/50 transition-colors text-left"
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronDown size={16} />}
        <BarChart3 size={16} className="text-accent-orange" />
        <span className="font-medium text-sm text-text-secondary flex-1">
          Column Statistics
        </span>
      </button>

      {/* Content */}
      {!collapsed && (
        <div className="p-3 pt-0 space-y-3">
          {/* Column Name */}
          <div>
            <span
              className={`text-sm font-medium ${columnColorClassName}`}
            >
              {column}
            </span>
          </div>

          {/* Stats Grid */}
          <div className="space-y-1.5 text-xs">
            <StatRow label="Count" value={stats.count.toLocaleString()} />
            <StatRow
              label="Null"
              value={`${stats.nullCount} (${(stats.nullPercentage * 100).toFixed(1)}%)`}
            />
            <StatRow label="Unique" value={stats.uniqueCount.toLocaleString()} />

            {/* Textual Stats */}
            {'avgLength' in stats && (
              <>
                <StatRow
                  label="Completeness"
                  value={`${(stats.completeness * 100).toFixed(0)}%`}
                  valueClassName="text-accent-categorical"
                />
                <StatRow label="Avg Length" value={`${stats.avgLength.toFixed(1)} chars`} />
                <StatRow label="Min/Max" value={`${stats.minLength} / ${stats.maxLength} chars`} />
              </>
            )}

            {/* Numerical Stats */}
            {'mean' in stats && (
              <>
                <StatRow label="Mean" value={stats.mean.toFixed(2)} />
                <StatRow label="Median" value={stats.median.toFixed(2)} />
                <StatRow label="Std Dev" value={stats.stdDev.toFixed(2)} />
                <StatRow label="Range" value={`${stats.min} - ${stats.max}`} />
              </>
            )}

            {/* Categorical Stats */}
            {'uniqueValues' in stats && stats.uniqueValues.length <= 5 && (
              <div className="mt-2">
                <div className="text-text-muted mb-1">Values:</div>
                <div className="space-y-0.5">
                  {stats.uniqueValues.map((value) => (
                    <div key={value} className="text-text-primary flex justify-between">
                      <span>{value}</span>
                      <span className="text-text-muted">
                        {stats.distribution[value]}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Related Constraints */}
          {stats.constraintIds.length > 0 && (
            <div className="pt-2 border-t border-dark-border">
              <div className="text-xs text-text-muted mb-1">
                Related Constraints: {stats.constraintIds.length}
              </div>
              {/* Could add links to constraints here */}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function StatRow({
  label,
  value,
  valueClassName,
}: {
  label: string;
  value: string;
  valueClassName?: string;
}) {
  return (
    <div className="flex justify-between">
      <span className="text-text-muted">{label}:</span>
      <span
        className={`text-text-primary font-medium ${valueClassName || ''}`}
      >
        {value}
      </span>
    </div>
  );
}
