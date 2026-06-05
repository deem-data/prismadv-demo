import React, { useState, useMemo } from 'react';
import { ChevronDown, ChevronRight, Database, Circle, Layers, FileCode, AlertTriangle, Code2, FlaskConical, Loader2 } from 'lucide-react';
import * as Dialog from '@radix-ui/react-dialog';
import { Constraint, ConstraintType, DeequSuggestion } from '@/types';

interface DeequComparisonViewProps {
  constraints: Constraint[];
  deequSuggestions: DeequSuggestion[];
  selectedConstraintId: string | null;
  selectedDeequSuggestionId: string | null;
  onSelectConstraint: (id: string) => void;
  onSelectDeequSuggestion: (id: string) => void;
  filter: string;
  onStartBenchmark?: () => void;
  isBenchmarkRunning?: boolean;
  benchmarkProgress?: number;
  benchmarkWarning?: string | null;
}

interface ComparisonRow {
  type: 'matched' | 'prisma-only' | 'deequ-only';
  constraint?: Constraint;
  deequSuggestion?: DeequSuggestion;
  sortKey: string;
}

interface ComparisonGroup {
  column: string;
  displayName: string;
  rows: ComparisonRow[];
  prismaCount: number;
  deequCount: number;
  matchCount: number;
}

function getTypeIcon(type: ConstraintType) {
  switch (type) {
    case 'completeness': return <Layers size={12} className="text-green-500" />;
    case 'format': return <FileCode size={12} className="text-blue-500" />;
    case 'range': return <AlertTriangle size={12} className="text-orange-500" />;
    case 'statistical': return <AlertTriangle size={12} className="text-purple-500" />;
    default: return <Circle size={12} className="text-gray-500" />;
  }
}

const DeequComparisonView: React.FC<DeequComparisonViewProps> = ({
  constraints,
  deequSuggestions,
  selectedConstraintId,
  selectedDeequSuggestionId,
  onSelectConstraint,
  onSelectDeequSuggestion,
  filter,
  onStartBenchmark,
  isBenchmarkRunning,
  benchmarkProgress,
  benchmarkWarning,
}) => {
  const [collapsedColumns, setCollapsedColumns] = useState<Set<string>>(new Set());
  const [showBenchmarkConfirm, setShowBenchmarkConfirm] = useState(false);

  const toggleColumn = (col: string) => {
    setCollapsedColumns((prev) => {
      const next = new Set(prev);
      if (next.has(col)) next.delete(col);
      else next.add(col);
      return next;
    });
  };

  // Build grouped comparison data
  const { groups, summary } = useMemo(() => {
    const lowerFilter = filter.toLowerCase();
    const matchedDeequIds = new Set<string>();
    const groupMap = new Map<string, ComparisonRow[]>();

    const ensureGroup = (col: string) => {
      if (!groupMap.has(col)) groupMap.set(col, []);
    };

    // Match PrismaDV constraints to Deequ suggestions
    for (const constraint of constraints) {
      // Apply filter
      if (lowerFilter && !constraint.column.toLowerCase().includes(lowerFilter)
          && !constraint.label.toLowerCase().includes(lowerFilter)
          && !constraint.type.toLowerCase().includes(lowerFilter)) {
        continue;
      }

      ensureGroup(constraint.column);
      const match = deequSuggestions.find(
        (s) => s.column === constraint.column && s.constraintType === constraint.type
          && !matchedDeequIds.has(s.id),
      );

      if (match) {
        matchedDeequIds.add(match.id);
        groupMap.get(constraint.column)!.push({
          type: 'matched',
          constraint,
          deequSuggestion: match,
          sortKey: constraint.type,
        });
      } else {
        groupMap.get(constraint.column)!.push({
          type: 'prisma-only',
          constraint,
          sortKey: constraint.type,
        });
      }
    }

    // Remaining Deequ-only suggestions (deduplicated by column+type)
    const seenDeequKeys = new Set<string>();
    for (const s of deequSuggestions) {
      if (matchedDeequIds.has(s.id)) continue;
      const key = `${s.column}|${s.constraintType}`;
      if (seenDeequKeys.has(key)) continue;
      seenDeequKeys.add(key);

      // Apply filter
      if (lowerFilter && !s.column.toLowerCase().includes(lowerFilter)
          && !s.constraintType.toLowerCase().includes(lowerFilter)
          && !s.description.toLowerCase().includes(lowerFilter)) {
        continue;
      }

      ensureGroup(s.column);
      groupMap.get(s.column)!.push({
        type: 'deequ-only',
        deequSuggestion: s,
        sortKey: s.constraintType,
      });
    }

    // Build sorted groups
    const groups: ComparisonGroup[] = [];
    let totalMatch = 0, totalPrisma = 0, totalDeequ = 0;

    for (const [column, rows] of groupMap.entries()) {
      const matchCount = rows.filter((r) => r.type === 'matched').length;
      const prismaCount = rows.filter((r) => r.type === 'prisma-only').length;
      const deequCount = rows.filter((r) => r.type === 'deequ-only').length;
      totalMatch += matchCount;
      totalPrisma += prismaCount;
      totalDeequ += deequCount;

      groups.push({
        column,
        displayName: column === '_dataset_' ? 'Dataset-level' : column,
        rows: rows.sort((a, b) => {
          // matched first, then prisma-only, then deequ-only
          const order = { matched: 0, 'prisma-only': 1, 'deequ-only': 2 };
          return order[a.type] - order[b.type] || a.sortKey.localeCompare(b.sortKey);
        }),
        prismaCount: matchCount + prismaCount,
        deequCount: matchCount + deequCount,
        matchCount,
      });
    }

    // Sort: regular columns alphabetically, _dataset_ last
    groups.sort((a, b) => {
      if (a.column === '_dataset_') return 1;
      if (b.column === '_dataset_') return -1;
      return a.column.localeCompare(b.column);
    });

    return {
      groups,
      summary: {
        overlap: totalMatch,
        prismaOnly: totalPrisma,
        deequOnly: totalDeequ,
      },
    };
  }, [constraints, deequSuggestions, filter]);

  return (
    <div className="flex-1 overflow-y-auto">
      {/* Summary Card */}
      <div className="px-3 py-2.5 border-b border-dark-darkest bg-dark-medium/50">
        <div className="grid grid-cols-3 gap-1.5 text-center">
          <div className="rounded-md bg-amber-500/10 px-2 py-1.5">
            <div className="text-base font-bold text-amber-400">{summary.prismaOnly}</div>
            <div className="text-[9px] text-amber-400/70 uppercase tracking-wider font-medium">PrismaDV only</div>
          </div>
          <div className="rounded-md bg-emerald-500/10 px-2 py-1.5">
            <div className="text-base font-bold text-emerald-400">{summary.overlap}</div>
            <div className="text-[9px] text-emerald-400/70 uppercase tracking-wider font-medium">Overlap</div>
          </div>
          <div className="rounded-md bg-sky-500/10 px-2 py-1.5">
            <div className="text-base font-bold text-sky-400">{summary.deequOnly}</div>
            <div className="text-[9px] text-sky-400/70 uppercase tracking-wider font-medium">Deequ only</div>
          </div>
        </div>
        {onStartBenchmark && (
          <button
            onClick={() => {
              if (benchmarkWarning) {
                setShowBenchmarkConfirm(true);
              } else {
                onStartBenchmark();
              }
            }}
            disabled={isBenchmarkRunning}
            className="mt-2 w-full flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md
              bg-accent-textual/10 hover:bg-accent-textual/20 text-accent-textual text-[10px] font-medium
              uppercase tracking-wider transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isBenchmarkRunning ? (
              <>
                <Loader2 size={11} className="animate-spin" />
                <span>Running... {benchmarkProgress != null ? `${Math.round(benchmarkProgress * 100)}%` : ''}</span>
              </>
            ) : (
              <>
                <FlaskConical size={11} />
                <span>Run Error Benchmark</span>
              </>
            )}
          </button>
        )}
      </div>

      {/* Grouped list */}
      {groups.length === 0 ? (
        <div className="p-4 text-center text-text-muted text-sm">No matches found</div>
      ) : (
        groups.map((group) => {
          const isCollapsed = collapsedColumns.has(group.column);
          return (
            <div key={group.column}>
              {/* Column group header */}
              <button
                onClick={() => toggleColumn(group.column)}
                className="w-full flex items-center gap-2 px-3 py-1.5 bg-dark-darkest/60 hover:bg-dark-darkest/80 transition-colors text-left border-b border-dark-border"
              >
                {isCollapsed
                  ? <ChevronRight size={12} className="text-text-muted flex-shrink-0" />
                  : <ChevronDown size={12} className="text-text-muted flex-shrink-0" />
                }
                <span className="text-xs font-semibold text-accent-textual truncate">{group.displayName}</span>
                <div className="ml-auto flex items-center gap-1.5">
                  {group.matchCount > 0 && (
                    <span className="text-[9px] px-1 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-medium">{group.matchCount}</span>
                  )}
                  <span className="text-[9px] text-text-muted">{group.rows.length}</span>
                </div>
              </button>

              {/* Rows */}
              {!isCollapsed && group.rows.map((row, idx) => (
                <ComparisonRowItem
                  key={`${group.column}-${idx}`}
                  row={row}
                  selectedConstraintId={selectedConstraintId}
                  selectedDeequSuggestionId={selectedDeequSuggestionId}
                  onSelectConstraint={onSelectConstraint}
                  onSelectDeequSuggestion={onSelectDeequSuggestion}
                />
              ))}
            </div>
          );
        })
      )}

      {/* Benchmark confirm dialog */}
      <Dialog.Root open={showBenchmarkConfirm} onOpenChange={setShowBenchmarkConfirm}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50" />
          <Dialog.Content className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-dark-light border border-dark-border rounded-lg shadow-xl p-6 w-[400px] z-50">
            <Dialog.Title className="text-lg font-semibold text-text-primary mb-2">
              Incomplete Column Coverage
            </Dialog.Title>
            <Dialog.Description className="text-sm text-text-secondary mb-6">
              {benchmarkWarning}
            </Dialog.Description>
            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowBenchmarkConfirm(false);
                  onStartBenchmark?.();
                }}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-md bg-accent-textual text-white font-medium hover:bg-accent-textual/90 transition-colors"
              >
                <FlaskConical size={16} />
                Run Anyway
              </button>
              <button
                onClick={() => setShowBenchmarkConfirm(false)}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-md border border-dark-border bg-dark-base text-text-secondary hover:text-text-primary hover:border-text-secondary transition-colors"
              >
                Cancel
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
};

// Individual row component
const ComparisonRowItem: React.FC<{
  row: ComparisonRow;
  selectedConstraintId: string | null;
  selectedDeequSuggestionId: string | null;
  onSelectConstraint: (id: string) => void;
  onSelectDeequSuggestion: (id: string) => void;
}> = ({ row, selectedConstraintId, selectedDeequSuggestionId, onSelectConstraint, onSelectDeequSuggestion }) => {
  if (row.type === 'matched') {
    const c = row.constraint!;
    const s = row.deequSuggestion!;
    const isConstraintSelected = selectedConstraintId === c.id;
    const isDeequSelected = selectedDeequSuggestionId === s.id;

    return (
      <div className="border-b border-dark-border/50">
        {/* PrismaDV constraint */}
        <div
          onClick={() => onSelectConstraint(c.id)}
          className={`flex items-center gap-2 px-3 py-1.5 cursor-pointer transition-colors
            ${isConstraintSelected ? 'bg-dark-light border-l-2 border-amber-400' : 'hover:bg-dark-light/50 border-l-2 border-amber-400/30'}`}
        >
          <Code2 size={11} className="text-amber-400 flex-shrink-0" />
          {getTypeIcon(c.type as ConstraintType)}
          <span className="text-xs text-text-primary truncate flex-1">{c.label}</span>
          <span className="text-[9px] px-1 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-medium flex-shrink-0">Match</span>
        </div>
        {/* Deequ suggestion */}
        <div
          onClick={() => onSelectDeequSuggestion(s.id)}
          className={`flex items-center gap-2 px-3 py-1.5 cursor-pointer transition-colors
            ${isDeequSelected ? 'bg-dark-light border-l-2 border-sky-400' : 'hover:bg-dark-light/50 border-l-2 border-sky-400/30'}`}
        >
          <Database size={11} className="text-sky-400 flex-shrink-0" />
          {getTypeIcon(s.constraintType as ConstraintType)}
          <span className="text-xs text-text-secondary truncate flex-1">{s.description}</span>
        </div>
      </div>
    );
  }

  if (row.type === 'prisma-only') {
    const c = row.constraint!;
    const isSelected = selectedConstraintId === c.id;
    return (
      <div
        onClick={() => onSelectConstraint(c.id)}
        className={`flex items-center gap-2 px-3 py-1.5 cursor-pointer transition-colors border-b border-dark-border/50
          ${isSelected ? 'bg-dark-light border-l-2 border-amber-400' : 'hover:bg-dark-light/50 border-l-2 border-amber-400/30'}`}
      >
        <Code2 size={11} className="text-amber-400 flex-shrink-0" />
        {getTypeIcon(c.type as ConstraintType)}
        <span className="text-xs text-text-primary truncate flex-1">{c.label}</span>
        <span className="text-[9px] px-1 py-0.5 rounded bg-amber-500/10 text-amber-400 font-medium flex-shrink-0">PrismaDV</span>
      </div>
    );
  }

  // deequ-only
  const s = row.deequSuggestion!;
  const isSelected = selectedDeequSuggestionId === s.id;
  return (
    <div
      onClick={() => onSelectDeequSuggestion(s.id)}
      className={`flex items-center gap-2 px-3 py-1.5 cursor-pointer transition-colors border-b border-dark-border/50
        ${isSelected ? 'bg-dark-light border-l-2 border-sky-400' : 'hover:bg-dark-light/50 border-l-2 border-sky-400/30'}`}
    >
      <Database size={11} className="text-sky-400 flex-shrink-0" />
      {getTypeIcon(s.constraintType as ConstraintType)}
      <span className="text-xs text-text-secondary truncate flex-1">{s.description}</span>
      <span className="text-[9px] px-1 py-0.5 rounded bg-sky-500/10 text-sky-400 font-medium flex-shrink-0">Deequ</span>
    </div>
  );
};

export default DeequComparisonView;
