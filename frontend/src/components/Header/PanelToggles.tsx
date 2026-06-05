import { Database, ListChecks, GitBranch } from 'lucide-react';
import type { PanelType } from '@/types';

interface PanelTogglesProps {
  visibility: {
    data: boolean;
    constraints: boolean;
    flow: boolean;
  };
  onToggle: (panel: PanelType) => void;
}

export function PanelToggles({ visibility, onToggle }: PanelTogglesProps) {
  return (
    <div className="flex items-center gap-1">
      {/* Data Panel Toggle */}
      <button
        onClick={() => onToggle('data')}
        className={`
          flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded transition-colors
          ${
            visibility.data
              ? 'bg-accent-blue/20 text-accent-blue'
              : 'text-text-secondary hover:bg-dark-border'
          }
        `}
        title="Toggle Data Panel"
      >
        <Database size={14} />
        <span>Data</span>
      </button>

      {/* Flow Panel Toggle */}
      <button
        onClick={() => onToggle('flow')}
        className={`
          flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded transition-colors
          ${
            visibility.flow
              ? 'bg-accent-blue/20 text-accent-blue'
              : 'text-text-secondary hover:bg-dark-border'
          }
        `}
        title="Toggle Data-Code Assumption Graph"
      >
        <GitBranch size={14} />
        <span>Graph</span>
      </button>

      {/* Constraints Panel Toggle */}
      <button
        onClick={() => onToggle('constraints')}
        className={`
          flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded transition-colors
          ${
            visibility.constraints
              ? 'bg-accent-blue/20 text-accent-blue'
              : 'text-text-secondary hover:bg-dark-border'
          }
        `}
        title="Toggle Constraints Panel"
      >
        <ListChecks size={14} />
        <span>Constraints</span>
      </button>
    </div>
  );
}
