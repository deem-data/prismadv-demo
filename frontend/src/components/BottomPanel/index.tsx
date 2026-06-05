import React from 'react';
import FlowGraph from './FlowGraph';
import { useAppStore } from '@/store';
import { X } from 'lucide-react';

const BottomPanel: React.FC = () => {
  const { flowGraph, togglePanel } = useAppStore();

  // We handle maximization via resizing panels in AppLayout, 
  // but we can provide a collapse button here.

  return (
    <div className="flex flex-col h-full bg-dark-medium border-t border-dark-darkest overflow-hidden min-w-0">
      {/* Header */}
      <div className="flex items-center justify-between p-2 px-3 bg-dark-medium border-b border-dark-darkest z-10">
        <h3 className="text-xs font-bold uppercase tracking-wider text-text-secondary">Data-Code Assumption Graph</h3>
        <div className="flex items-center space-x-2">
          <button 
            onClick={() => togglePanel('flow')}
            className="text-text-muted hover:text-text-primary transition-colors"
            title="Close Panel"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 relative min-w-0">
        <FlowGraph data={flowGraph} />
      </div>
    </div>
  );
};

export default BottomPanel;
