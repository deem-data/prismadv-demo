import { useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { X, Plus } from 'lucide-react';
import { useAppStore } from '@/store';
import type { Constraint, ConstraintType, ColumnType } from '@/types';

const CONSTRAINT_TYPES: ConstraintType[] = [
  'completeness', 'format', 'range', 'statistical', 'enum', 'uniqueness', 'relationship',
];

const GE_PLACEHOLDERS: Record<ConstraintType, string> = {
  completeness: "expect_column_values_to_not_be_null(column='col')",
  format: "expect_column_values_to_match_regex(column='col', regex='^\\d{4}-\\d{2}-\\d{2}$')",
  range: "expect_column_values_to_be_between(column='col', min_value=0, max_value=100)",
  statistical: "expect_column_mean_to_be_between(column='col', min_value=10, max_value=50)",
  enum: "expect_column_values_to_be_in_set(column='col', value_set=['A', 'B', 'C'])",
  uniqueness: "expect_column_values_to_be_unique(column='col')",
  relationship: "expect_column_pair_values_A_to_be_greater_than_B(column_A='a', column_B='b')",
};

interface AddConstraintDialogProps {
  open: boolean;
  onClose: () => void;
}

export function AddConstraintDialog({ open, onClose }: AddConstraintDialogProps) {
  const { dataset, addConstraint } = useAppStore();

  const [column, setColumn] = useState('');
  const [type, setType] = useState<ConstraintType>('completeness');
  const [label, setLabel] = useState('');
  const [geCode, setGeCode] = useState('');
  const [deequCode, setDeequCode] = useState('');
  const [error, setError] = useState('');

  const columnOptions = dataset?.columns.map((c) => c.name) ?? [];

  const inferColumnType = (colName: string): ColumnType => {
    const col = dataset?.columns.find((c) => c.name === colName);
    return col?.inferredType ?? 'textual';
  };

  const handleTypeChange = (t: ConstraintType) => {
    setType(t);
    if (!geCode) setGeCode(GE_PLACEHOLDERS[t]);
  };

  const handleSubmit = () => {
    if (!column.trim()) { setError('Column is required'); return; }
    if (!label.trim()) { setError('Label is required'); return; }
    if (!geCode.trim()) { setError('Great Expectations code is required'); return; }

    const constraint: Constraint = {
      id: crypto.randomUUID(),
      column: column.trim(),
      type,
      columnType: inferColumnType(column.trim()),
      label: label.trim(),
      enabled: true,
      code: {
        greatExpectations: geCode.trim(),
        deequ: deequCode.trim(),
      },
      assumption: {
        text: '(Manually added constraint)',
        sourceCodeLines: [],
        sourceFile: '',
      },
    };

    addConstraint(constraint);
    handleClose();
  };

  const handleClose = () => {
    setColumn('');
    setType('completeness');
    setLabel('');
    setGeCode('');
    setDeequCode('');
    setError('');
    onClose();
  };

  const inputCls = 'w-full bg-dark-darkest border border-dark-border rounded px-2.5 py-1.5 text-xs text-text-primary focus:outline-none focus:border-accent-textual transition-colors';

  return (
    <Dialog.Root open={open} onOpenChange={(v) => !v && handleClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-dark-light border border-dark-border rounded-lg shadow-xl w-[520px] max-h-[85vh] flex flex-col z-50">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-dark-border flex-shrink-0">
            <div className="flex items-center gap-2">
              <Plus className="w-4 h-4 text-accent-textual" />
              <Dialog.Title className="text-sm font-semibold text-text-primary">
                Add Constraint
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

            {/* Type */}
            <div className="space-y-1">
              <label className="text-[10px] text-text-muted uppercase tracking-wider">Constraint Type *</label>
              <select
                value={type}
                onChange={(e) => handleTypeChange(e.target.value as ConstraintType)}
                className={inputCls}
              >
                {CONSTRAINT_TYPES.map((t) => (
                  <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                ))}
              </select>
            </div>

            {/* Label */}
            <div className="space-y-1">
              <label className="text-[10px] text-text-muted uppercase tracking-wider">Label *</label>
              <input
                type="text"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                placeholder="e.g. Column must not be null"
                className={inputCls}
              />
            </div>

            {/* GE Code */}
            <div className="space-y-1">
              <label className="text-[10px] text-text-muted uppercase tracking-wider">Great Expectations Code *</label>
              <textarea
                value={geCode}
                onChange={(e) => setGeCode(e.target.value)}
                placeholder={GE_PLACEHOLDERS[type]}
                rows={3}
                className={`${inputCls} font-mono resize-none`}
              />
            </div>

            {/* Deequ Code */}
            <div className="space-y-1">
              <label className="text-[10px] text-text-muted uppercase tracking-wider">Deequ Code <span className="text-text-muted normal-case">(optional)</span></label>
              <textarea
                value={deequCode}
                onChange={(e) => setDeequCode(e.target.value)}
                placeholder='hasCompleteness("col", _ >= 0.95)'
                rows={2}
                className={`${inputCls} font-mono resize-none`}
              />
            </div>

            {error && (
              <p className="text-xs text-red-400">{error}</p>
            )}
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
              Add Constraint
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
