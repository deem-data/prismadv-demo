import React, { useState } from 'react';
import { X, Database, Copy, Check } from 'lucide-react';
import type { DeequSuggestion } from '@/types';

interface DeequSuggestionDetailsProps {
  suggestion: DeequSuggestion | null;
  onClose?: () => void;
}

const DeequSuggestionDetails: React.FC<DeequSuggestionDetailsProps> = ({ suggestion, onClose }) => {
  const [copied, setCopied] = useState(false);

  if (!suggestion) {
    return (
      <div className="flex-1 flex items-center justify-center p-6 text-center text-text-muted">
        <p>Select a Deequ suggestion to view details</p>
      </div>
    );
  }

  const handleCopy = async () => {
    await navigator.clipboard.writeText(suggestion.deequCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="flex flex-col h-full bg-dark-medium overflow-x-hidden overflow-y-auto min-w-0">
      {/* Header */}
      <div className="p-3 border-b border-dark-darkest flex items-center justify-between sticky top-0 bg-dark-medium z-10">
        <div className="flex items-center gap-1.5">
          <Database size={13} className="text-sky-400" />
          <h3 className="text-sm font-bold uppercase tracking-wider text-sky-400">Deequ Suggestion</h3>
        </div>
        {onClose && (
          <button onClick={onClose} className="p-1 text-text-muted hover:text-text-primary transition-colors">
            <X size={14} />
          </button>
        )}
      </div>

      <div className="p-4 space-y-5 min-w-0">
        {/* Description */}
        <section>
          <h4 className="text-xs font-bold text-text-muted uppercase mb-1.5">Description</h4>
          <p className="text-xs text-text-primary leading-relaxed">{suggestion.description}</p>
        </section>

        {/* Column */}
        <section>
          <h4 className="text-xs font-bold text-text-muted uppercase mb-1.5">Column</h4>
          <span className="text-xs text-accent-textual font-mono">
            {suggestion.column === '_dataset_' ? 'Dataset-level' : suggestion.column}
          </span>
        </section>

        {/* Type */}
        <section>
          <h4 className="text-xs font-bold text-text-muted uppercase mb-1.5">Type</h4>
          <span className="text-xs text-text-primary capitalize">{suggestion.constraintType}</span>
        </section>

        {/* Deequ Code */}
        <section>
          <div className="flex items-center justify-between mb-1.5">
            <h4 className="text-xs font-bold text-text-muted uppercase">Deequ Code</h4>
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 text-[10px] text-text-muted hover:text-text-primary transition-colors"
              title="Copy code"
            >
              {copied ? <Check size={10} className="text-green-400" /> : <Copy size={10} />}
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
          <pre className="bg-dark-darkest border border-dark-border rounded p-3 text-xs font-mono text-sky-300 whitespace-pre-wrap break-all leading-relaxed overflow-x-auto">
            {suggestion.deequCode}
          </pre>
        </section>

        {/* Source badge */}
        <div className="flex items-center gap-2 pt-2 border-t border-dark-darkest">
          <Database size={11} className="text-sky-400/60" />
          <span className="text-[10px] text-text-muted">
            Suggested by Deequ's data-driven analysis — based on statistical properties of the dataset, not task code.
          </span>
        </div>
      </div>
    </div>
  );
};

export default DeequSuggestionDetails;
