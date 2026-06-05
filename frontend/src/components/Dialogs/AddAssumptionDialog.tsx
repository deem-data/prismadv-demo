import { useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { X, Plus } from 'lucide-react';
import { useAppStore } from '@/store';
import type { AssumptionItem } from '@/types';

interface AddAssumptionDialogProps {
  open: boolean;
  onClose: () => void;
}

export function AddAssumptionDialog({ open, onClose }: AddAssumptionDialogProps) {
  const { dataset, addAssumption } = useAppStore();

  const [column, setColumn] = useState('');
  const [text, setText] = useState('');
  const [error, setError] = useState('');

  const columnOptions = dataset?.columns.map((c) => c.name) ?? [];

  const handleSubmit = () => {
    if (!column.trim()) { setError('Column is required'); return; }
    if (!text.trim()) { setError('Assumption text is required'); return; }

    const assumption: AssumptionItem = {
      id: crypto.randomUUID(),
      text: text.trim(),
      column: column.trim(),
      columns: [column.trim()],
      sourceCodeLines: [],
      constraintIds: [],
    };

    addAssumption(assumption);
    handleClose();
  };

  const handleClose = () => {
    setColumn('');
    setText('');
    setError('');
    onClose();
  };

  const inputCls = 'w-full bg-dark-darkest border border-dark-border rounded px-2.5 py-1.5 text-xs text-text-primary focus:outline-none focus:border-accent-textual transition-colors';

  return (
    <Dialog.Root open={open} onOpenChange={(v) => !v && handleClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-dark-light border border-dark-border rounded-lg shadow-xl w-[480px] max-h-[85vh] flex flex-col z-50">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-dark-border flex-shrink-0">
            <div className="flex items-center gap-2">
              <Plus className="w-4 h-4 text-accent-textual" />
              <Dialog.Title className="text-sm font-semibold text-text-primary">
                Add Assumption
              </Dialog.Title>
            </div>
            <button onClick={handleClose} className="text-text-muted hover:text-text-primary transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Form */}
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
            {/* Column */}
            <div className="space-y-1">
              <label className="text-[10px] text-text-muted uppercase tracking-wider">Column *</label>
              {columnOptions.length > 0 ? (
                <select
                  value={column}
                  onChange={(e) => setColumn(e.target.value)}
                  className={inputCls}
                >
                  <option value="">Select a column...</option>
                  {columnOptions.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={column}
                  onChange={(e) => setColumn(e.target.value)}
                  placeholder="column_name"
                  className={inputCls}
                />
              )}
            </div>

            {/* Assumption text */}
            <div className="space-y-1">
              <label className="text-[10px] text-text-muted uppercase tracking-wider">Assumption *</label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Describe what you expect about this column's data quality..."
                rows={4}
                autoFocus
                className={`${inputCls} resize-none leading-relaxed`}
              />
            </div>

            {error && <p className="text-xs text-red-400">{error}</p>}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-dark-border flex-shrink-0">
            <button
              onClick={handleClose}
              className="px-3 py-1.5 text-xs text-text-muted hover:text-text-primary transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-accent-textual hover:bg-accent-textual/80 text-white rounded transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              Add Assumption
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
