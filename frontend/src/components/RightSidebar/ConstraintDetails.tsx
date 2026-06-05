import React, { useState, useEffect } from 'react';
import { Constraint, ConstraintCode } from '@/types';
import ConstraintCodeView from './ConstraintCodeView';
import AssumptionCard from './AssumptionCard';
import { X, Pencil, Trash2, Check, MapPin } from 'lucide-react';
import { useAppStore } from '@/store';

function toLineRanges(lines: number[]): { start: number; end: number }[] {
  if (lines.length === 0) return [];
  const sorted = [...lines].sort((a, b) => a - b);
  const ranges: { start: number; end: number }[] = [];
  let start = sorted[0], end = sorted[0];
  for (let i = 1; i < sorted.length; i++) {
    if (sorted[i] === end + 1) { end = sorted[i]; }
    else { ranges.push({ start, end }); start = end = sorted[i]; }
  }
  ranges.push({ start, end });
  return ranges;
}

interface ConstraintDetailsProps {
  constraint: Constraint | null;
  onClose?: () => void;
  onDelete?: (id: string) => void;
  onUpdate?: (id: string, patch: { label?: string; code?: ConstraintCode }) => void;
}

const ConstraintDetails: React.FC<ConstraintDetailsProps> = ({
  constraint,
  onClose,
  onDelete,
  onUpdate,
}) => {
  const { scrollToLine, dataQualityMetrics, deequValidationResults, validateConstraint } = useAppStore();
  const [isEditing, setIsEditing] = useState(false);
  const [editLabel, setEditLabel] = useState('');
  const [editGe, setEditGe] = useState('');
  const [editDeequ, setEditDeequ] = useState('');
  const [isValidatingGe, setIsValidatingGe] = useState(false);
  const [isValidatingDeequ, setIsValidatingDeequ] = useState(false);

  // Reset edit/validation state whenever the selected constraint changes
  useEffect(() => {
    setIsEditing(false);
    setIsValidatingGe(false);
    setIsValidatingDeequ(false);
  }, [constraint?.id]);

  if (!constraint) {
    return (
      <div className="flex-1 flex items-center justify-center p-6 text-center text-text-muted">
        <p>Select a constraint to view details</p>
      </div>
    );
  }

  const handleEdit = () => {
    setEditLabel(constraint.label);
    setEditGe(constraint.code.greatExpectations);
    setEditDeequ(constraint.code.deequ);
    setIsEditing(true);
  };

  const handleSave = () => {
    onUpdate?.(constraint.id, {
      label: editLabel.trim() || constraint.label,
      code: { greatExpectations: editGe, deequ: editDeequ },
    });
    setIsEditing(false);
  };

  const handleCancel = () => {
    setIsEditing(false);
  };

  const handleValidateGe = async () => {
    setIsValidatingGe(true);
    try {
      await validateConstraint(constraint.id, 'great_expectations');
    } finally {
      setIsValidatingGe(false);
    }
  };

  const handleValidateDeequ = async () => {
    setIsValidatingDeequ(true);
    try {
      await validateConstraint(constraint.id, 'deequ');
    } finally {
      setIsValidatingDeequ(false);
    }
  };

  // Derive GE validation state from global metrics
  const violations = dataQualityMetrics?.metrics?.violationsByConstraint?.[constraint.id];
  const message = dataQualityMetrics?.metrics?.validationMessages?.[constraint.id];
  const geValidation = violations !== undefined
    ? {
        status: (violations === 0 ? 'pass' : violations === 2 ? 'error' : 'fail') as 'pass' | 'fail' | 'error',
        message: message || undefined,
      }
    : null;

  // Derive Deequ validation state from the dedicated map
  const deequResult = deequValidationResults.get(constraint.id);
  const deequValidation = deequResult || null;

  const textareaCls = 'w-full bg-dark-darkest border border-dark-border rounded p-2 text-xs font-mono text-text-secondary resize-none focus:outline-none focus:border-accent-textual transition-colors leading-relaxed';

  return (
    <div className="flex flex-col h-full bg-dark-medium overflow-x-hidden overflow-y-auto min-w-0">
      {/* Header */}
      <div className="p-3 border-b border-dark-darkest flex items-center justify-between sticky top-0 bg-dark-medium z-10">
        <h3 className="text-sm font-bold uppercase tracking-wider text-text-secondary">Details</h3>
        <div className="flex items-center gap-1">
          {isEditing ? (
            <>
              <button
                onClick={handleSave}
                className="flex items-center gap-1 px-2 py-1 text-[10px] bg-accent-textual hover:bg-accent-textual/80 text-white rounded transition-colors"
              >
                <Check size={10} />
                Save
              </button>
              <button
                onClick={handleCancel}
                className="px-2 py-1 text-[10px] text-text-muted hover:text-text-primary transition-colors"
              >
                Cancel
              </button>
            </>
          ) : (
            <>
              {onUpdate && (
                <button
                  onClick={handleEdit}
                  className="p-1 text-text-muted hover:text-text-primary transition-colors"
                  title="Edit constraint"
                >
                  <Pencil size={13} />
                </button>
              )}
              {onDelete && (
                <button
                  onClick={() => onDelete(constraint.id)}
                  className="p-1 text-text-muted hover:text-red-400 transition-colors"
                  title="Delete constraint"
                >
                  <Trash2 size={13} />
                </button>
              )}
            </>
          )}
          {onClose && (
            <button onClick={onClose} className="p-1 text-text-muted hover:text-text-primary transition-colors">
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      <div className="p-4 space-y-5 min-w-0">
        {/* Label */}
        <section>
          <h4 className="text-xs font-bold text-text-muted uppercase mb-1.5">Label</h4>
          {isEditing ? (
            <input
              type="text"
              value={editLabel}
              onChange={(e) => setEditLabel(e.target.value)}
              className="w-full bg-dark-darkest border border-dark-border rounded px-2.5 py-1.5 text-xs text-text-primary focus:outline-none focus:border-accent-textual transition-colors"
            />
          ) : (
            <p className="text-xs text-text-primary">{constraint.label}</p>
          )}
        </section>

        {/* Assumption Section */}
        <section>
          <h4 className="text-xs font-bold text-text-muted uppercase mb-2">Inferred Assumption</h4>
          <AssumptionCard assumption={constraint.assumption} assumptionId={constraint.assumptionId} />
        </section>

        {/* Source Lines */}
        {constraint.assumption.sourceCodeLines.length > 0 && (
          <section>
            <h4 className="text-xs font-bold text-text-muted uppercase mb-1.5">Source Lines</h4>
            <div className="flex flex-wrap gap-1.5">
              {toLineRanges(constraint.assumption.sourceCodeLines).map(({ start, end }) => (
                <button
                  key={`${start}-${end}`}
                  onClick={() => scrollToLine(start)}
                  className="flex items-center gap-1 px-2 py-0.5 rounded bg-dark-darkest border border-dark-border text-[10px] font-mono text-text-secondary hover:text-accent-textual hover:border-accent-textual transition-colors"
                  title={start === end ? `Jump to line ${start}` : `Jump to lines ${start}–${end}`}
                >
                  <MapPin size={9} />
                  {start === end ? `L${start}` : `L${start}–${end}`}
                </button>
              ))}
            </div>
          </section>
        )}

        {/* Code Section — with per-tab validation */}
        <section>
          <h4 className="text-xs font-bold text-text-muted uppercase mb-2">Generated Constraint</h4>
          {isEditing ? (
            <div className="space-y-2">
              <div>
                <p className="text-[10px] text-text-muted mb-1">Great Expectations</p>
                <textarea
                  value={editGe}
                  onChange={(e) => setEditGe(e.target.value)}
                  rows={3}
                  className={textareaCls}
                />
              </div>
              <div>
                <p className="text-[10px] text-text-muted mb-1">Deequ</p>
                <textarea
                  value={editDeequ}
                  onChange={(e) => setEditDeequ(e.target.value)}
                  rows={2}
                  className={textareaCls}
                />
              </div>
            </div>
          ) : (
            <ConstraintCodeView
              code={constraint.code}
              geValidation={geValidation}
              deequValidation={deequValidation}
              onValidateGe={handleValidateGe}
              onValidateDeequ={handleValidateDeequ}
              isValidatingGe={isValidatingGe}
              isValidatingDeequ={isValidatingDeequ}
            />
          )}
        </section>

        {/* Data Stats Section */}
        {constraint.dataStats && (
          <section>
            <h4 className="text-xs font-bold text-text-muted uppercase mb-2">Data Evidence</h4>
            <div className="bg-dark-light border border-dark-border rounded p-3 text-xs">
              <div className="grid grid-cols-2 gap-2">
                <div className="text-text-muted">Column:</div>
                <div className="text-right text-text-primary font-mono">{constraint.column}</div>
                <div className="text-text-muted">Null Count:</div>
                <div className="text-right text-text-primary font-mono">{constraint.dataStats.nullCount}</div>
                <div className="text-text-muted">Unique Values:</div>
                <div className="text-right text-text-primary font-mono">{constraint.dataStats.uniqueCount}</div>
              </div>
            </div>
          </section>
        )}
      </div>
    </div>
  );
};

export default ConstraintDetails;
