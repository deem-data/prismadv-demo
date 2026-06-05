import React, { useState, useEffect } from 'react';
import { X, Pencil, Check, ArrowRight, MapPin, Trash2, Sparkles, Loader2 } from 'lucide-react';
import type { AssumptionItem } from '@/types';
import { useAppStore } from '@/store';

interface AssumptionDetailsProps {
  assumption: AssumptionItem | null;
  onClose: () => void;
  onSwitchToConstraint: (constraintId: string) => void;
  onDelete?: (id: string) => void;
}

/** Collapse a sorted list of line numbers into contiguous ranges. */
function toLineRanges(lines: number[]): { start: number; end: number }[] {
  if (lines.length === 0) return [];
  const sorted = [...lines].sort((a, b) => a - b);
  const ranges: { start: number; end: number }[] = [];
  let start = sorted[0], end = sorted[0];
  for (let i = 1; i < sorted.length; i++) {
    if (sorted[i] === end + 1) {
      end = sorted[i];
    } else {
      ranges.push({ start, end });
      start = end = sorted[i];
    }
  }
  ranges.push({ start, end });
  return ranges;
}

const AssumptionDetails: React.FC<AssumptionDetailsProps> = ({
  assumption,
  onClose,
  onSwitchToConstraint,
  onDelete,
}) => {
  const { updateAssumptionText, scrollToLine, constraints, taskFile, dataset, generatingAssumptionId, generateConstraintsFromAssumption } = useAppStore();
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState('');
  const isGenerating = generatingAssumptionId === assumption?.id;

  useEffect(() => {
    setIsEditing(false);
  }, [assumption?.id]);

  if (!assumption) {
    return (
      <div className="flex-1 flex items-center justify-center p-6 text-center text-text-muted">
        <p>Select an assumption to view details</p>
      </div>
    );
  }

  const handleEdit = () => {
    setEditText(assumption.text);
    setIsEditing(true);
  };

  const handleSave = () => {
    const trimmed = editText.trim();
    if (trimmed) updateAssumptionText(assumption.id, trimmed);
    setIsEditing(false);
  };

  const handleCancel = () => setIsEditing(false);

  const linkedConstraints = constraints.filter((c) =>
    assumption.constraintIds.includes(c.id)
  );

  const handleGenerateConstraints = () => {
    if (!assumption) return;
    generateConstraintsFromAssumption(assumption.id);
  };

  return (
    <div className="flex flex-col h-full bg-dark-medium overflow-x-hidden overflow-y-auto min-w-0">
      {/* Header */}
      <div className="p-3 border-b border-dark-darkest flex items-center justify-between sticky top-0 bg-dark-medium z-10">
        <h3 className="text-sm font-bold uppercase tracking-wider text-text-secondary">Assumption</h3>
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
              <button
                onClick={handleEdit}
                className="p-1 text-text-muted hover:text-text-primary transition-colors"
                title="Edit assumption text"
              >
                <Pencil size={13} />
              </button>
              {onDelete && (
                <button
                  onClick={() => { onDelete(assumption.id); onClose(); }}
                  className="p-1 text-text-muted hover:text-red-400 transition-colors"
                  title="Delete assumption"
                >
                  <Trash2 size={13} />
                </button>
              )}
            </>
          )}
          <button onClick={onClose} className="p-1 text-text-muted hover:text-text-primary transition-colors">
            <X size={14} />
          </button>
        </div>
      </div>

      <div className="p-4 space-y-5 min-w-0">
        {/* Column */}
        <section>
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-xs font-semibold px-2 py-1 rounded bg-accent-textual/20 text-accent-textual">
              {assumption.column}
            </span>
          </div>
        </section>

        {/* Assumption Text */}
        <section>
          <h4 className="text-xs font-bold text-text-muted uppercase mb-1.5">Assumption</h4>
          {isEditing ? (
            <textarea
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              rows={5}
              autoFocus
              className="w-full bg-dark-darkest border border-accent-textual rounded p-2.5 text-xs text-text-primary resize-none focus:outline-none leading-relaxed"
            />
          ) : (
            <p className="text-xs text-text-primary leading-relaxed">{assumption.text}</p>
          )}
        </section>

        {/* Source Lines */}
        {assumption.sourceCodeLines.length > 0 && (
          <section>
            <h4 className="text-xs font-bold text-text-muted uppercase mb-1.5">Source Lines</h4>
            <div className="flex flex-wrap gap-1.5">
              {toLineRanges(assumption.sourceCodeLines).map(({ start, end }) => (
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

        {/* Linked Constraints */}
        <section>
          <div className="flex items-center justify-between mb-1.5">
            <h4 className="text-xs font-bold text-text-muted uppercase">
              Derived Constraints
              {linkedConstraints.length > 0 && (
                <span className="ml-1.5 text-text-muted font-normal normal-case">({linkedConstraints.length})</span>
              )}
            </h4>
            {taskFile && dataset && (
              <button
                onClick={handleGenerateConstraints}
                disabled={isGenerating}
                className="flex items-center gap-1 px-2 py-1 text-[10px] text-accent-blue hover:bg-accent-blue/10 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title="Generate constraints from this assumption using LLM"
              >
                {isGenerating ? <Loader2 size={10} className="animate-spin" /> : <Sparkles size={10} />}
                {isGenerating ? 'Generating...' : 'Infer'}
              </button>
            )}
          </div>
          {linkedConstraints.length === 0 && !isGenerating ? (
            <p className="text-xs text-text-muted italic">No constraints derived from this assumption</p>
          ) : (
            <div className="space-y-1.5">
              {linkedConstraints.map((c) => (
                <button
                  key={c.id}
                  onClick={() => onSwitchToConstraint(c.id)}
                  className="w-full flex items-center justify-between gap-2 px-2.5 py-1.5 rounded bg-dark-darkest border border-dark-border text-xs text-text-secondary hover:text-text-primary hover:border-accent-textual transition-colors text-left"
                >
                  <span className="truncate">{c.label}</span>
                  <ArrowRight size={11} className="flex-shrink-0 text-text-muted" />
                </button>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
};

export default AssumptionDetails;
