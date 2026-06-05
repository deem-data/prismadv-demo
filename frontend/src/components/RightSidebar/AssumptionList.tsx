import React, { useState, useMemo } from 'react';
import { Search, Lightbulb, Plus, Trash2 } from 'lucide-react';
import type { AssumptionItem } from '@/types';

interface AssumptionListProps {
  assumptions: AssumptionItem[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  onAddClick?: () => void;
  onDelete?: (id: string) => void;
}

function columnBadgeColor(column: string): string {
  // Stable color from column name hash
  const colors = [
    'bg-accent-textual/20 text-accent-textual',
    'bg-accent-numerical/20 text-accent-numerical',
    'bg-accent-categorical/20 text-accent-categorical',
    'bg-accent-blue/20 text-accent-blue',
    'bg-accent-purple/20 text-accent-purple',
  ];
  let hash = 0;
  for (let i = 0; i < column.length; i++) hash = (hash * 31 + column.charCodeAt(i)) >>> 0;
  return colors[hash % colors.length];
}

const AssumptionList: React.FC<AssumptionListProps> = ({ assumptions, selectedId, onSelect, onAddClick, onDelete }) => {
  const [filter, setFilter] = useState('');

  const displayed = useMemo(() => {
    if (!filter) return assumptions;
    const q = filter.toLowerCase();
    return assumptions.filter(
      (a) => a.column.toLowerCase().includes(q) || a.text.toLowerCase().includes(q)
    );
  }, [assumptions, filter]);

  return (
    <div className="flex flex-col h-full border-b border-dark-darkest">
      {/* Header */}
      <div className="p-3 bg-dark-medium border-b border-dark-darkest">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-bold uppercase tracking-wider text-text-secondary">Assumptions</h3>
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-text-muted bg-dark-darkest px-1.5 py-0.5 rounded-full">
              {displayed.length} / {assumptions.length}
            </span>
            {onAddClick && (
              <button
                onClick={onAddClick}
                className="p-1 text-text-muted hover:text-accent-textual transition-colors"
                title="Add assumption"
              >
                <Plus size={14} />
              </button>
            )}
          </div>
        </div>
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            placeholder="Filter by column or text..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full bg-dark-darkest border border-dark-border rounded text-xs py-1.5 pl-8 pr-2 text-text-primary focus:outline-none focus:border-accent-textual transition-colors"
          />
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {displayed.length === 0 ? (
          <div className="p-4 text-center text-text-muted text-sm">
            {assumptions.length === 0 ? 'No assumptions generated yet' : 'No matches'}
          </div>
        ) : (
          <div className="divide-y divide-dark-border">
            {displayed.map((assumption) => (
              <div
                key={assumption.id}
                onClick={() => onSelect(assumption.id === selectedId ? null : assumption.id)}
                className={`
                  flex items-start gap-2.5 px-3 py-2.5 cursor-pointer transition-colors group
                  ${selectedId === assumption.id
                    ? 'bg-dark-light border-l-2 border-accent-textual'
                    : 'hover:bg-dark-light border-l-2 border-transparent'}
                `}
              >
                <Lightbulb size={13} className="text-amber-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 mb-0.5 flex-wrap">
                    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${columnBadgeColor(assumption.column)}`}>
                      {assumption.column}
                    </span>
                    {assumption.constraintIds.length > 0 && (
                      <span className="text-[10px] text-text-muted">
                        → {assumption.constraintIds.length} constraint{assumption.constraintIds.length !== 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-text-primary leading-relaxed line-clamp-2">
                    {assumption.text}
                  </p>
                </div>
                {onDelete && (
                  <button
                    onClick={(e) => { e.stopPropagation(); onDelete(assumption.id); }}
                    className="p-0.5 opacity-0 group-hover:opacity-100 text-text-muted hover:text-red-400 transition-all flex-shrink-0 mt-0.5"
                    title="Delete assumption"
                  >
                    <Trash2 size={13} />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AssumptionList;
