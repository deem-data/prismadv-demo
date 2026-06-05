import * as Dialog from '@radix-ui/react-dialog';
import { useEffect, useState } from 'react';
import { Sparkles, X, Zap } from 'lucide-react';
import type { Column } from '@/types';

const COLUMN_TYPE_COLORS: Record<string, string> = {
  numerical: 'text-accent-numerical bg-accent-numerical/10 border-accent-numerical/30',
  textual: 'text-accent-textual bg-accent-textual/10 border-accent-textual/30',
  categorical: 'text-accent-categorical bg-accent-categorical/10 border-accent-categorical/30',
};

interface ColumnSelectionDialogProps {
  open: boolean;
  columns: Column[];
  /** Columns the LLM detected as accessed in the task code */
  accessedColumns: string[];
  onInfer: (selectedColumns: string[]) => void;
  onClose: () => void;
}

export function ColumnSelectionDialog({
  open,
  columns,
  accessedColumns,
  onInfer,
  onClose,
}: ColumnSelectionDialogProps) {
  const accessedSet = new Set(accessedColumns);

  const [checked, setChecked] = useState<Set<string>>(() => new Set(accessedColumns));

  // Re-initialise when dialog opens (columns / detected set may have changed)
  useEffect(() => {
    if (open) {
      setChecked(new Set(accessedColumns));
    }
  }, [open, accessedColumns]);

  const toggle = (name: string) => {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const allSelected = checked.size === columns.length;
  const allAccessedSelected =
    accessedColumns.length > 0 &&
    accessedColumns.every((c) => checked.has(c));

  const handleSelectAll = () => {
    if (allSelected) setChecked(new Set());
    else setChecked(new Set(columns.map((c) => c.name)));
  };

  const handleSelectAllAccessed = () => {
    setChecked(new Set(accessedColumns));
  };

  return (
    <Dialog.Root open={open} onOpenChange={onClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-dark-light border border-dark-border rounded-lg shadow-xl w-[500px] max-h-[72vh] flex flex-col z-50">

          {/* Header */}
          <div className="flex items-start justify-between p-5 pb-3">
            <div>
              <Dialog.Title className="text-base font-semibold text-text-primary">
                Select Columns
              </Dialog.Title>
              <Dialog.Description className="text-sm text-text-secondary mt-0.5">
                {accessedColumns.length > 0
                  ? `${accessedColumns.length} column${accessedColumns.length !== 1 ? 's' : ''} detected by the model. Adjust the selection if needed.`
                  : 'Choose which columns to generate constraints for.'}
              </Dialog.Description>
            </div>
            <button
              onClick={onClose}
              className="text-text-muted hover:text-text-secondary transition-colors ml-4 mt-0.5"
            >
              <X size={16} />
            </button>
          </div>

          {/* Toolbar */}
          <div className="px-5 pb-2 flex items-center justify-between gap-2">
            <span className="text-xs text-text-muted">
              {checked.size} of {columns.length} selected
            </span>
            <div className="flex items-center gap-3">
              {accessedColumns.length > 0 && (
                <button
                  onClick={handleSelectAllAccessed}
                  disabled={allAccessedSelected}
                  className="flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300 disabled:text-text-muted disabled:cursor-default transition-colors"
                  title="Select only detected columns"
                >
                  <Zap size={11} />
                  Select detected
                </button>
              )}
              <button
                onClick={handleSelectAll}
                className="text-xs text-accent-blue hover:text-accent-blue/80 transition-colors"
              >
                {allSelected ? 'Deselect all' : 'Select all'}
              </button>
            </div>
          </div>

          {/* Column list */}
          <div className="overflow-y-auto flex-1 px-3 pb-3">
            {columns.map((col) => {
              const isChecked = checked.has(col.name);
              const isAccessed = accessedSet.has(col.name);
              const typeColor = COLUMN_TYPE_COLORS[col.inferredType] ?? 'text-text-secondary bg-dark-base border-dark-border';
              return (
                <label
                  key={col.name}
                  className={`
                    flex items-center gap-3 px-3 py-2.5 rounded-md cursor-pointer
                    transition-colors select-none
                    ${isChecked ? 'bg-dark-base' : 'hover:bg-dark-base/50'}
                  `}
                >
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => toggle(col.name)}
                    className="w-4 h-4 rounded border-dark-border accent-accent-blue cursor-pointer flex-shrink-0"
                  />
                  <span className="text-sm text-text-primary flex-1 truncate">{col.name}</span>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    {isAccessed && (
                      <span
                        className="flex items-center gap-0.5 text-xs px-1.5 py-0.5 rounded border font-medium text-amber-400 bg-amber-400/10 border-amber-400/30"
                        title="Detected as accessed by the model"
                      >
                        <Zap size={10} />
                        detected
                      </span>
                    )}
                    <span className={`text-xs px-1.5 py-0.5 rounded border font-medium ${typeColor}`}>
                      {col.inferredType}
                    </span>
                  </div>
                </label>
              );
            })}
          </div>

          {/* Footer */}
          <div className="p-4 pt-3 border-t border-dark-border flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 rounded-md border border-dark-border bg-dark-base text-text-secondary hover:text-text-primary hover:border-text-secondary transition-colors text-sm font-medium"
            >
              Cancel
            </button>
            <button
              onClick={() => onInfer(Array.from(checked))}
              disabled={checked.size === 0}
              className={`
                flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors
                ${checked.size > 0
                  ? 'bg-accent-blue text-white hover:bg-accent-blue/90'
                  : 'bg-dark-border text-text-muted cursor-not-allowed'}
              `}
            >
              <Sparkles size={14} />
              Inference{checked.size > 0 ? ` (${checked.size})` : ''}
            </button>
          </div>

        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
