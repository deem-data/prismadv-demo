import React, { useState, useRef, useCallback, useMemo } from 'react';
import ConstraintList from './ConstraintList';
import ConstraintDetails from './ConstraintDetails';
import DeequSuggestionDetails from './DeequSuggestionDetails';
import PerformanceBenchmarkPanel from './PerformanceBenchmarkPanel';
import AssumptionList from './AssumptionList';
import AssumptionDetails from './AssumptionDetails';
import { AddConstraintDialog } from '@/components/Dialogs/AddConstraintDialog';
import { AddAssumptionDialog } from '@/components/Dialogs/AddAssumptionDialog';
import { DeleteAssumptionDialog } from '@/components/Dialogs/DeleteAssumptionDialog';
import { useAppStore } from '@/store';
import type { AssumptionItem } from '@/types';

const MIN_PCT = 15;
const MAX_PCT = 85;

const RightSidebar: React.FC = () => {
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showAddAssumptionDialog, setShowAddAssumptionDialog] = useState(false);
  const [pendingDeleteAssumption, setPendingDeleteAssumption] = useState<AssumptionItem | null>(null);
  // List panel height as % of the content area (below tab bar)
  const [splitPct, setSplitPct] = useState(50);
  const containerRef = useRef<HTMLDivElement>(null);

  const startDrag = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    const container = containerRef.current;
    if (!container) return;

    const onMove = (ev: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      const pct = ((ev.clientY - rect.top) / rect.height) * 100;
      setSplitPct(Math.min(MAX_PCT, Math.max(MIN_PCT, pct)));
    };
    const onUp = () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  }, []);

  const {
    constraints,
    selectedConstraintId,
    selectConstraint,
    deleteConstraint,
    updateConstraint,
    dataQualityMetrics,
    constraintsSynced,
    previousConstraints,
    clearComparison,
    assumptions,
    selectedAssumptionId,
    selectAssumption,
    deleteAssumption,
    sidebarTab,
    setSidebarTab,
    deequSuggestions,
    isLoadingDeequSuggestions,
    showDeequComparison,
    toggleDeequComparison,
    selectedDeequSuggestionId,
    selectDeequSuggestion,
    errorBenchmarkStatus,
    errorBenchmarkProgress,
    errorBenchmarkStep,
    errorBenchmarkResult,
    startErrorBenchmark,
    clearErrorBenchmark,
  } = useAppStore();

  const selectedConstraint = selectedConstraintId
    ? constraints.find((c) => c.id === selectedConstraintId) ?? null
    : null;

  const selectedAssumption = selectedAssumptionId
    ? assumptions.find((a) => a.id === selectedAssumptionId) ?? null
    : null;

  const detectedAccessedColumns = useAppStore((s) => s.detectedAccessedColumns);
  const benchmarkWarning = useMemo(() => {
    if (detectedAccessedColumns.length === 0) return null;
    const constraintColumns = new Set(constraints.map((c) => c.column));
    const missing = detectedAccessedColumns.filter((col) => !constraintColumns.has(col));
    if (missing.length > 0) {
      return `Constraints are not generated on all accessed columns. Missing: ${missing.join(', ')}.\n\nThe comparison may not be fair.`;
    }
    return null;
  }, [detectedAccessedColumns, constraints]);

  const handleSelectConstraint = (id: string) => {
    selectConstraint(id);
    selectDeequSuggestion(null);
  };

  const handleSelectDeequSuggestion = (id: string) => {
    selectDeequSuggestion(id);
    selectConstraint(null);
  };

  const handleSwitchToConstraint = (constraintId: string) => {
    selectConstraint(constraintId); // also sets sidebarTab: 'constraints'
  };

  const selectedDeequSuggestion = selectedDeequSuggestionId
    ? deequSuggestions?.find((s) => s.id === selectedDeequSuggestionId) ?? null
    : null;

  const handleDeleteAssumption = (id: string) => {
    const assumption = assumptions.find((a) => a.id === id);
    if (!assumption) return;
    const linked = constraints.filter((c) => assumption.constraintIds.includes(c.id));
    if (linked.length > 0) {
      setPendingDeleteAssumption(assumption);
    } else {
      deleteAssumption(id);
    }
  };

  const confirmDeleteAssumption = (alsoDeleteConstraints: boolean) => {
    if (!pendingDeleteAssumption) return;
    if (alsoDeleteConstraints) {
      for (const cid of pendingDeleteAssumption.constraintIds) {
        deleteConstraint(cid);
      }
    }
    deleteAssumption(pendingDeleteAssumption.id);
    setPendingDeleteAssumption(null);
  };

  return (
    <div className="flex flex-col h-full bg-dark-medium border-l border-dark-darkest overflow-hidden min-w-0">
      {/* Tab bar — Assumptions first, Constraints second */}
      <div className="flex border-b border-dark-darkest flex-shrink-0">
        <button
          onClick={() => setSidebarTab('assumptions')}
          className={`
            flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-semibold uppercase tracking-wider transition-colors
            ${sidebarTab === 'assumptions'
              ? 'text-accent-textual border-b-2 border-accent-textual bg-dark-light'
              : 'text-text-muted hover:text-text-secondary border-b-2 border-transparent'}
          `}
        >
          Assumptions
          {assumptions.length > 0 && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-dark-darkest">
              {assumptions.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setSidebarTab('constraints')}
          className={`
            flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-semibold uppercase tracking-wider transition-colors
            ${sidebarTab === 'constraints'
              ? 'text-accent-textual border-b-2 border-accent-textual bg-dark-light'
              : 'text-text-muted hover:text-text-secondary border-b-2 border-transparent'}
          `}
        >
          Constraints
          {constraints.length > 0 && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-dark-darkest">
              {constraints.length}
            </span>
          )}
        </button>
      </div>

      {/* Content — split pane */}
      <div ref={containerRef} className="flex flex-col flex-1 overflow-hidden min-h-0">
        {sidebarTab === 'constraints' ? (
          <>
            <div style={{ height: `${splitPct}%` }} className="overflow-hidden min-h-0">
              <ConstraintList
                constraints={constraints}
                selectedId={selectedConstraintId}
                onSelect={handleSelectConstraint}
                onDelete={deleteConstraint}
                onAddClick={() => setShowAddDialog(true)}
                dataQualityMetrics={dataQualityMetrics}
                constraintsSynced={constraintsSynced}
                previousConstraints={previousConstraints}
                onClearComparison={clearComparison}
                deequSuggestions={deequSuggestions}
                isLoadingDeequSuggestions={isLoadingDeequSuggestions}
                showDeequComparison={showDeequComparison}
                onToggleDeequComparison={toggleDeequComparison}
                selectedDeequSuggestionId={selectedDeequSuggestionId}
                onSelectDeequSuggestion={handleSelectDeequSuggestion}
                onStartBenchmark={startErrorBenchmark}
                isBenchmarkRunning={errorBenchmarkStatus === 'running'}
                benchmarkProgress={errorBenchmarkProgress}
                benchmarkWarning={benchmarkWarning}
              />
            </div>
            <div
              onMouseDown={startDrag}
              className="h-1.5 flex-shrink-0 bg-dark-darkest hover:bg-accent-blue/40 cursor-row-resize transition-colors"
            />
            <div style={{ height: `${100 - splitPct}%` }} className="overflow-hidden min-h-0">
              {errorBenchmarkStatus !== 'idle' ? (
                <PerformanceBenchmarkPanel
                  result={errorBenchmarkResult}
                  isRunning={errorBenchmarkStatus === 'running'}
                  progress={errorBenchmarkProgress}
                  step={errorBenchmarkStep}
                  onClose={clearErrorBenchmark}
                />
              ) : showDeequComparison && selectedDeequSuggestion ? (
                <DeequSuggestionDetails
                  suggestion={selectedDeequSuggestion}
                  onClose={() => selectDeequSuggestion(null)}
                />
              ) : (
                <ConstraintDetails
                  constraint={selectedConstraint}
                  onClose={() => selectConstraint(null)}
                  onDelete={deleteConstraint}
                  onUpdate={updateConstraint}
                />
              )}
            </div>
          </>
        ) : (
          <>
            <div style={{ height: `${splitPct}%` }} className="overflow-hidden min-h-0">
              <AssumptionList
                assumptions={assumptions}
                selectedId={selectedAssumptionId}
                onSelect={selectAssumption}
                onAddClick={() => setShowAddAssumptionDialog(true)}
                onDelete={handleDeleteAssumption}
              />
            </div>
            <div
              onMouseDown={startDrag}
              className="h-1.5 flex-shrink-0 bg-dark-darkest hover:bg-accent-blue/40 cursor-row-resize transition-colors"
            />
            <div style={{ height: `${100 - splitPct}%` }} className="overflow-hidden min-h-0">
              <AssumptionDetails
                assumption={selectedAssumption}
                onClose={() => selectAssumption(null)}
                onSwitchToConstraint={handleSwitchToConstraint}
                onDelete={handleDeleteAssumption}
              />
            </div>
          </>
        )}
      </div>

      <AddConstraintDialog
        open={showAddDialog}
        onClose={() => setShowAddDialog(false)}
      />
      <AddAssumptionDialog
        open={showAddAssumptionDialog}
        onClose={() => setShowAddAssumptionDialog(false)}
      />

      {pendingDeleteAssumption && (
        <DeleteAssumptionDialog
          open={!!pendingDeleteAssumption}
          assumption={pendingDeleteAssumption}
          linkedConstraints={constraints.filter((c) => pendingDeleteAssumption.constraintIds.includes(c.id))}
          onDeleteAssumptionOnly={() => confirmDeleteAssumption(false)}
          onDeleteWithConstraints={() => confirmDeleteAssumption(true)}
          onClose={() => setPendingDeleteAssumption(null)}
        />
      )}
    </div>
  );
};

export default RightSidebar;
