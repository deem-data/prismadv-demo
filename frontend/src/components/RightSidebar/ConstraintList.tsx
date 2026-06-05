import React, { useState, useMemo, useRef, useEffect } from 'react';
import { Search, CheckCircle2, Circle, AlertTriangle, FileCode, XCircle, Info, AlertCircle, Layers, X, Trash2, Plus, Database, Loader2 } from 'lucide-react';
import * as Tooltip from '@radix-ui/react-tooltip';
import { Constraint, ConstraintType, DataQualityMetrics, DeequSuggestion } from '@/types';
import DeequComparisonView from './DeequComparisonView';

interface ConstraintListProps {
  constraints: Constraint[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onDelete?: (id: string) => void;
  onAddClick?: () => void;
  dataQualityMetrics: DataQualityMetrics | null;
  constraintsSynced: boolean | null;
  previousConstraints?: Constraint[] | null;
  onClearComparison?: () => void;
  // Deequ comparison
  deequSuggestions?: DeequSuggestion[] | null;
  isLoadingDeequSuggestions?: boolean;
  showDeequComparison?: boolean;
  onToggleDeequComparison?: () => void;
  selectedDeequSuggestionId?: string | null;
  onSelectDeequSuggestion?: (id: string) => void;
  // Error benchmark
  onStartBenchmark?: () => void;
  isBenchmarkRunning?: boolean;
  benchmarkProgress?: number;
  benchmarkWarning?: string | null;
}

type DiffTag = 'new' | 'removed' | 'kept';

function constraintKey(c: Constraint) {
  return `${c.column}|${c.label}`;
}

function computeDiffTags(
  previous: Constraint[],
  current: Constraint[],
): { currentTags: Map<string, DiffTag>; removedConstraints: Constraint[] } {
  const prevKeys = new Set(previous.map(constraintKey));
  const currKeys = new Set(current.map(constraintKey));

  const currentTags = new Map<string, DiffTag>();
  for (const c of current) {
    currentTags.set(c.id, prevKeys.has(constraintKey(c)) ? 'kept' : 'new');
  }

  const removedConstraints = previous.filter((c) => !currKeys.has(constraintKey(c)));
  return { currentTags, removedConstraints };
}


const ConstraintList: React.FC<ConstraintListProps> = ({
  constraints,
  selectedId,
  onSelect,
  onDelete,
  onAddClick,
  dataQualityMetrics,
  constraintsSynced,
  previousConstraints,
  onClearComparison,
  deequSuggestions,
  isLoadingDeequSuggestions,
  showDeequComparison,
  onToggleDeequComparison,
  selectedDeequSuggestionId,
  onSelectDeequSuggestion,
  onStartBenchmark,
  isBenchmarkRunning,
  benchmarkProgress,
  benchmarkWarning,
}) => {
  const [filter, setFilter] = useState('');
  const [showLegend, setShowLegend] = useState(false);
  const [showBefore, setShowBefore] = useState(false);
  const legendRef = useRef<HTMLDivElement>(null);

  const hasComparison = !!previousConstraints && previousConstraints.length > 0;
  const hasDeequComparison = !!showDeequComparison && !!deequSuggestions;

  const { currentTags, removedConstraints } = useMemo(() => {
    if (!hasComparison) return { currentTags: new Map<string, DiffTag>(), removedConstraints: [] };
    return computeDiffTags(previousConstraints!, constraints);
  }, [hasComparison, previousConstraints, constraints]);

  // Reset to "After" view when comparison is cleared
  useEffect(() => {
    if (!hasComparison) setShowBefore(false);
  }, [hasComparison]);

  // Close legend when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (legendRef.current && !legendRef.current.contains(event.target as Node)) {
        setShowLegend(false);
      }
    };
    if (showLegend) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showLegend]);

  // Helper to get validation state: 'pass' | 'fail' | 'error' | null
  const getValidationState = (constraintId: string): 'pass' | 'fail' | 'error' | null => {
    if (!dataQualityMetrics) return null;
    if (!dataQualityMetrics.metrics.violationsByConstraint) return null;
    const violations = dataQualityMetrics.metrics.violationsByConstraint[constraintId];
    if (violations === undefined) return null;
    if (violations === 2) return 'error';
    return violations === 0 ? 'pass' : 'fail';
  };

  // Which list to show: "before" (previous) or "after" (current + removed placeholders)
  const displayConstraints = useMemo(() => {
    const source = hasComparison && showBefore ? previousConstraints! : constraints;
    if (!filter) return source;
    const lowerFilter = filter.toLowerCase();
    return source.filter(
      (c) =>
        c.column.toLowerCase().includes(lowerFilter) ||
        c.label.toLowerCase().includes(lowerFilter) ||
        c.type.toLowerCase().includes(lowerFilter)
    );
  }, [constraints, previousConstraints, hasComparison, showBefore, filter]);

  // In "after" view, append removed constraints at the bottom (greyed out)
  const filteredRemoved = useMemo(() => {
    if (!hasComparison || showBefore || !filter) return hasComparison && !showBefore ? removedConstraints : [];
    const lowerFilter = filter.toLowerCase();
    return removedConstraints.filter(
      (c) =>
        c.column.toLowerCase().includes(lowerFilter) ||
        c.label.toLowerCase().includes(lowerFilter) ||
        c.type.toLowerCase().includes(lowerFilter)
    );
  }, [hasComparison, showBefore, removedConstraints, filter]);

  const getTypeIcon = (type: ConstraintType) => {
    switch (type) {
      case 'completeness': return <Layers size={14} className="text-green-500" />;
      case 'format': return <FileCode size={14} className="text-blue-500" />;
      case 'range': return <AlertTriangle size={14} className="text-orange-500" />;
      case 'statistical': return <AlertTriangle size={14} className="text-purple-500" />;
      default: return <Circle size={14} className="text-gray-500" />;
    }
  };

  return (
    <div className="flex flex-col h-full border-b border-dark-darkest">
      {/* Header & Filter */}
      <div className="p-3 bg-dark-medium border-b border-dark-darkest">
        {/* Before/After comparison bar (optimization) */}
        {hasComparison && (
          <div className="flex items-center gap-1.5 mb-2 pb-2 border-b border-dark-darkest">
            <span className="text-[10px] text-text-muted uppercase tracking-wider">Comparison:</span>
            <div className="flex items-center rounded overflow-hidden border border-dark-border text-xs">
              <button
                onClick={() => setShowBefore(false)}
                className={`px-2 py-0.5 transition-colors ${!showBefore ? 'bg-violet-600 text-white' : 'text-text-muted hover:text-text-primary'}`}
              >
                After
              </button>
              <button
                onClick={() => setShowBefore(true)}
                className={`px-2 py-0.5 transition-colors ${showBefore ? 'bg-dark-border text-text-secondary' : 'text-text-muted hover:text-text-primary'}`}
              >
                Before
              </button>
            </div>
            <button
              onClick={onClearComparison}
              className="ml-auto text-text-muted hover:text-text-primary transition-colors"
              title="Dismiss comparison"
            >
              <X size={12} />
            </button>
          </div>
        )}

        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-1.5 relative" ref={legendRef}>
            <h3 className="text-sm font-bold uppercase tracking-wider text-text-secondary">Constraints</h3>
            <button
              onClick={() => setShowLegend(!showLegend)}
              className="text-text-muted hover:text-text-secondary transition-colors"
              title="Icon legend"
            >
              <Info size={14} />
            </button>
            {showLegend && (
              <div className="absolute top-6 left-0 z-50 bg-dark-light border border-dark-border rounded-md shadow-lg p-3 min-w-[180px]">
                <div className="text-xs font-semibold text-text-secondary mb-2">Icon Legend</div>
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2 text-xs text-text-primary">
                    <Layers size={14} className="text-green-500" />
                    <span>Completeness</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-text-primary">
                    <FileCode size={14} className="text-blue-500" />
                    <span>Format</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-text-primary">
                    <AlertTriangle size={14} className="text-orange-500" />
                    <span>Range</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-text-primary">
                    <AlertTriangle size={14} className="text-purple-500" />
                    <span>Statistical</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-text-primary">
                    <Circle size={14} className="text-gray-500" />
                    <span>Other</span>
                  </div>
                </div>
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            {constraintsSynced === true && (
              <Tooltip.Provider delayDuration={200}>
                <Tooltip.Root>
                  <Tooltip.Trigger asChild>
                    <div className="flex items-center gap-1 text-xs text-green-400 opacity-70 cursor-default">
                      <CheckCircle2 size={12} />
                      <span>Synced</span>
                    </div>
                  </Tooltip.Trigger>
                  <Tooltip.Portal>
                    <Tooltip.Content
                      side="bottom"
                      align="end"
                      className="max-w-[220px] bg-dark-light border border-dark-border rounded-md shadow-lg px-3 py-2 z-50"
                      sideOffset={6}
                    >
                      <p className="text-xs font-semibold text-green-400 mb-1">Up to date</p>
                      <p className="text-xs text-text-secondary leading-relaxed">
                        The constraints were generated from the current version of the task code. No changes have been made since the last inference run.
                      </p>
                      <Tooltip.Arrow className="fill-dark-border" />
                    </Tooltip.Content>
                  </Tooltip.Portal>
                </Tooltip.Root>
              </Tooltip.Provider>
            )}
            {constraintsSynced === false && (
              <Tooltip.Provider delayDuration={200}>
                <Tooltip.Root>
                  <Tooltip.Trigger asChild>
                    <div className="flex items-center gap-1 text-xs text-amber-400 cursor-default">
                      <AlertTriangle size={12} />
                      <span>Out of sync</span>
                    </div>
                  </Tooltip.Trigger>
                  <Tooltip.Portal>
                    <Tooltip.Content
                      side="bottom"
                      align="end"
                      className="max-w-[220px] bg-dark-light border border-dark-border rounded-md shadow-lg px-3 py-2 z-50"
                      sideOffset={6}
                    >
                      <p className="text-xs font-semibold text-amber-400 mb-1">Code has changed</p>
                      <p className="text-xs text-text-secondary leading-relaxed">
                        The task code was modified after the last inference run. The displayed constraints may no longer reflect the current code. Click <span className="text-text-primary font-medium">Inference</span> to regenerate.
                      </p>
                      <Tooltip.Arrow className="fill-dark-border" />
                    </Tooltip.Content>
                  </Tooltip.Portal>
                </Tooltip.Root>
              </Tooltip.Provider>
            )}
            <span className="text-xs text-text-muted bg-dark-darkest px-1.5 py-0.5 rounded-full">
              {displayConstraints.length} / {(hasComparison && showBefore ? previousConstraints! : constraints).length}
            </span>
            {/* Deequ compare button */}
            {onToggleDeequComparison && (
              <Tooltip.Provider delayDuration={200}>
                <Tooltip.Root>
                  <Tooltip.Trigger asChild>
                    <button
                      onClick={onToggleDeequComparison}
                      className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium transition-colors ${
                        showDeequComparison
                          ? 'bg-sky-600/30 text-sky-300 border border-sky-500/40'
                          : 'text-text-muted hover:text-sky-400 border border-transparent hover:border-sky-500/30'
                      }`}
                      title="Compare with Deequ baseline"
                    >
                      {isLoadingDeequSuggestions ? (
                        <Loader2 size={11} className="animate-spin" />
                      ) : (
                        <Database size={11} />
                      )}
                      <span>Deequ</span>
                    </button>
                  </Tooltip.Trigger>
                  <Tooltip.Portal>
                    <Tooltip.Content
                      side="bottom"
                      align="end"
                      className="max-w-[240px] bg-dark-light border border-dark-border rounded-md shadow-lg px-3 py-2 z-50"
                      sideOffset={6}
                    >
                      <p className="text-xs font-semibold text-sky-400 mb-1">Compare with Deequ baseline</p>
                      <p className="text-xs text-text-secondary leading-relaxed">
                        Show which constraints overlap with Deequ's built-in data-driven suggestions, and which are unique to PrismaDV's code-aware analysis.
                      </p>
                      <Tooltip.Arrow className="fill-dark-border" />
                    </Tooltip.Content>
                  </Tooltip.Portal>
                </Tooltip.Root>
              </Tooltip.Provider>
            )}
            {onAddClick && (
              <button
                onClick={onAddClick}
                className="p-1 text-text-muted hover:text-accent-textual transition-colors"
                title="Add constraint"
              >
                <Plus size={14} />
              </button>
            )}
          </div>
        </div>
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-1/2 transform -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            placeholder="Filter by column or type..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full bg-dark-darkest border border-dark-border rounded text-xs py-1.5 pl-8 pr-2 text-text-primary focus:outline-none focus:border-accent-textual transition-colors"
          />
        </div>
      </div>

      {/* Loading state for Deequ */}
      {showDeequComparison && isLoadingDeequSuggestions && (
        <div className="px-3 py-2 flex items-center gap-2 text-xs text-text-muted border-b border-dark-darkest bg-dark-medium/50">
          <Loader2 size={12} className="animate-spin text-sky-400" />
          <span>Loading Deequ baseline suggestions…</span>
        </div>
      )}

      {/* Constraint Validity Summary */}
      {dataQualityMetrics && constraints.length > 0 && (() => {
        const vbc = dataQualityMetrics.metrics.violationsByConstraint || {};
        const entries = Object.values(vbc);
        if (entries.length === 0) return null;
        const passed = entries.filter((v) => v === 0).length;
        const failed = entries.filter((v) => v === 1).length;
        const errored = entries.filter((v) => v === 2).length;
        const total = entries.length;
        const validity = Math.round((passed / total) * 100);
        return (
          <div className="px-3 py-2 border-b border-dark-darkest bg-dark-medium/50">
            <div className="flex items-center justify-between text-[10px] text-text-muted mb-1">
              <span>Constraint Validity</span>
              <span className={`font-semibold ${validity >= 80 ? 'text-green-400' : validity >= 50 ? 'text-amber-400' : 'text-red-400'}`}>{validity}%</span>
            </div>
            <div className="flex h-1.5 rounded-full overflow-hidden bg-dark-darkest">
              {passed > 0 && <div className="bg-green-500" style={{ width: `${(passed / total) * 100}%` }} />}
              {failed > 0 && <div className="bg-red-500" style={{ width: `${(failed / total) * 100}%` }} />}
              {errored > 0 && <div className="bg-yellow-500" style={{ width: `${(errored / total) * 100}%` }} />}
            </div>
            <div className="flex gap-3 mt-1 text-[10px] text-text-muted">
              {passed > 0 && <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-green-500" />{passed} passed</span>}
              {failed > 0 && <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-red-500" />{failed} violated</span>}
              {errored > 0 && <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-yellow-500" />{errored} error</span>}
            </div>
          </div>
        );
      })()}

      {/* List — switch between comparison view and normal view */}
      {hasDeequComparison && deequSuggestions && onSelectDeequSuggestion ? (
        <DeequComparisonView
          constraints={constraints}
          deequSuggestions={deequSuggestions}
          selectedConstraintId={selectedId}
          selectedDeequSuggestionId={selectedDeequSuggestionId ?? null}
          onSelectConstraint={onSelect}
          onSelectDeequSuggestion={onSelectDeequSuggestion}
          filter={filter}
          onStartBenchmark={onStartBenchmark}
          isBenchmarkRunning={isBenchmarkRunning}
          benchmarkProgress={benchmarkProgress}
          benchmarkWarning={benchmarkWarning}
        />
      ) : (
        <div className="flex-1 overflow-y-auto">
          {displayConstraints.length === 0 && filteredRemoved.length === 0 ? (
            <div className="p-4 text-center text-text-muted text-sm">
              No constraints found
            </div>
          ) : (
            <div className="divide-y divide-dark-border">
              {displayConstraints.map((constraint) => {
                const diffTag = hasComparison && !showBefore ? currentTags.get(constraint.id) : undefined;
                const isNew = diffTag === 'new';

                return (
                  <div
                    key={constraint.id}
                    onClick={() => onSelect(constraint.id)}
                    className={`
                      flex items-center px-3 py-2 cursor-pointer transition-colors group
                      ${selectedId === constraint.id ? 'bg-dark-light border-l-2 border-accent-textual' : 'hover:bg-dark-light border-l-2 border-transparent'}
                      ${isNew ? 'border-l-2 !border-green-500/60' : ''}
                    `}
                  >
                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center mb-0.5 gap-1.5">
                        {getTypeIcon(constraint.type)}
                        <span className="text-xs font-medium truncate text-text-primary">
                          {constraint.label}
                        </span>
                        {isNew && (
                          <span className="flex-shrink-0 text-[9px] font-semibold px-1 py-0.5 rounded bg-green-500/15 text-green-400 uppercase tracking-wider">
                            New
                          </span>
                        )}
                      </div>
                      <div className="text-[10px] text-text-muted truncate">
                        Column: <span className="text-accent-textual">{constraint.column}</span>
                      </div>
                    </div>

                    {/* Validation Status */}
                    {(() => {
                      const state = getValidationState(constraint.id);
                      if (state === null) return null;
                      const msg = dataQualityMetrics?.metrics?.validationMessages?.[constraint.id];
                      if (state === 'pass') return (
                        <div className="ml-2 flex items-center" title="Passed: No violations detected">
                          <CheckCircle2 size={16} className="text-green-500" strokeWidth={2} />
                        </div>
                      );
                      if (state === 'fail') return (
                        <div className="ml-2 flex items-center" title={msg ? `Violated: ${msg}` : 'Violated: Constraint not satisfied'}>
                          <XCircle size={16} className="text-red-500" strokeWidth={2} />
                        </div>
                      );
                      return (
                        <div className="ml-2 flex items-center" title={msg ? `Error: ${msg}` : 'Evaluation error: Could not run this constraint'}>
                          <AlertCircle size={16} className="text-yellow-500" strokeWidth={2} />
                        </div>
                      );
                    })()}

                    {/* Delete button — visible on hover */}
                    {onDelete && (
                      <button
                        onClick={(e) => { e.stopPropagation(); onDelete(constraint.id); }}
                        className="ml-1 p-0.5 opacity-0 group-hover:opacity-100 text-text-muted hover:text-red-400 transition-all flex-shrink-0"
                        title="Delete constraint"
                      >
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                );
              })}

              {/* Removed constraints (optimization diff — after view only) */}
              {filteredRemoved.map((constraint) => (
                <div
                  key={`removed-${constraint.id}`}
                  className="flex items-center px-3 py-2 opacity-40 border-l-2 border-red-500/50 cursor-default"
                >
                  <div className="mr-3 w-4 h-4 rounded border border-text-muted flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center mb-0.5 gap-1.5">
                      {getTypeIcon(constraint.type)}
                      <span className="text-xs font-medium truncate text-text-primary line-through">
                        {constraint.label}
                      </span>
                      <span className="flex-shrink-0 text-[9px] font-semibold px-1 py-0.5 rounded bg-red-500/15 text-red-400 uppercase tracking-wider">
                        Removed
                      </span>
                    </div>
                    <div className="text-[10px] text-text-muted truncate">
                      Column: <span className="text-accent-textual">{constraint.column}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ConstraintList;
