import * as Dialog from '@radix-ui/react-dialog';
import { X, DollarSign, FileCode, Database } from 'lucide-react';
import { useAppStore } from '@/store';
import type { CostRecord } from '@/types';

interface CostDialogProps {
  open: boolean;
  onClose: () => void;
}

const STAGE_COLORS = {
  columnDetection: 'bg-amber-400',
  dataFlowDetection: 'bg-orange-400',
  assumptionExtraction: 'bg-sky-400',
  constraintGeneration: 'bg-violet-400',
} as const;

const STAGE_LABELS = {
  columnDetection: 'Column Detection',
  dataFlowDetection: 'Data Flow Detection',
  assumptionExtraction: 'Assumption Extraction',
  constraintGeneration: 'Constraint Generation',
} as const;

function formatCost(cost: number): string {
  if (cost === 0) return '$0.0000';
  if (cost < 0.0001) return `$${cost.toExponential(2)}`;
  return `$${cost.toFixed(4)}`;
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function RunCard({ record, index }: { record: CostRecord; index: number }) {
  const { breakdown, totalCost } = record;

  const hasBreakdown =
    breakdown &&
    (breakdown.columnDetection + breakdown.dataFlowDetection +
     breakdown.assumptionExtraction + breakdown.constraintGeneration) > 0;

  const stages = breakdown
    ? [
        { key: 'columnDetection' as const, value: breakdown.columnDetection },
        { key: 'dataFlowDetection' as const, value: breakdown.dataFlowDetection },
        { key: 'assumptionExtraction' as const, value: breakdown.assumptionExtraction },
        { key: 'constraintGeneration' as const, value: breakdown.constraintGeneration },
      ]
    : [];

  const total = stages.reduce((s, x) => s + x.value, 0) || 1;

  return (
    <div className="border border-dark-border rounded-md p-3 space-y-2.5">
      {/* Run header */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-text-muted">
          Run #{index + 1} · {formatTimestamp(record.timestamp)}
        </span>
        <span className="text-sm font-mono font-semibold text-text-primary">
          {formatCost(totalCost)}
        </span>
      </div>

      {/* File + Dataset chips */}
      <div className="flex flex-wrap gap-1.5">
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-dark-darkest border border-dark-border text-xs text-text-secondary">
          <FileCode className="w-3 h-3 text-blue-400" />
          {record.taskFileName}
        </span>
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-dark-darkest border border-dark-border text-xs text-text-secondary">
          <Database className="w-3 h-3 text-emerald-400" />
          {record.datasetName}
        </span>
      </div>

      {/* Stacked bar + legend */}
      {hasBreakdown ? (
        <div className="space-y-1.5">
          {/* Bar */}
          <div className="flex h-2 rounded-full overflow-hidden bg-dark-darkest">
            {stages.map(({ key, value }) => {
              const pct = (value / total) * 100;
              if (pct < 0.5) return null;
              return (
                <div
                  key={key}
                  className={`${STAGE_COLORS[key]} transition-all`}
                  style={{ width: `${pct}%` }}
                />
              );
            })}
          </div>

          {/* Legend */}
          <div className="flex flex-wrap gap-x-3 gap-y-1">
            {stages.map(({ key, value }) => {
              const pct = ((value / total) * 100).toFixed(1);
              return (
                <div key={key} className="flex items-center gap-1">
                  <span className={`w-2 h-2 rounded-sm flex-shrink-0 ${STAGE_COLORS[key]}`} />
                  <span className="text-xs text-text-muted">
                    {STAGE_LABELS[key]}
                  </span>
                  <span className="text-xs text-text-secondary font-mono">
                    {pct}%
                  </span>
                  <span className="text-xs text-text-muted font-mono">
                    ({formatCost(value)})
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <p className="text-xs text-text-muted italic">No stage breakdown available</p>
      )}
    </div>
  );
}

export function CostDialog({ open, onClose }: CostDialogProps) {
  const { totalCost, costHistory } = useAppStore();

  return (
    <Dialog.Root open={open} onOpenChange={(v) => !v && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-dark-light border border-dark-border rounded-lg shadow-xl w-[480px] max-h-[80vh] flex flex-col z-50">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-dark-border flex-shrink-0">
            <div className="flex items-center gap-2">
              <DollarSign className="w-4 h-4 text-emerald-400" />
              <Dialog.Title className="text-sm font-semibold text-text-primary">
                LLM Cost Summary
              </Dialog.Title>
            </div>
            <button
              onClick={onClose}
              className="text-text-muted hover:text-text-primary transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Session total */}
          <div className="px-4 py-3 border-b border-dark-border flex-shrink-0 flex items-center justify-between">
            <span className="text-xs text-text-muted">Session total</span>
            <span className="text-base font-mono font-semibold text-emerald-400">
              {formatCost(totalCost)}
            </span>
          </div>

          {/* Run list */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
            {costHistory.length === 0 ? (
              <p className="text-sm text-text-muted text-center py-6">
                No inference runs yet this session.
              </p>
            ) : (
              [...costHistory].reverse().map((record, i) => (
                <RunCard
                  key={record.id}
                  record={record}
                  index={costHistory.length - 1 - i}
                />
              ))
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
