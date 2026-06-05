import React from 'react';
import { useAppStore } from '@/store';
import { Loader2, Maximize2, X } from 'lucide-react';

const GenerationProgressBar: React.FC = () => {
  const {
    isGenerating,
    isDetecting,
    generationProgress,
    currentStep,
    isOverlayMinimized,
    restoreOverlay,
    cancelGeneration,
    cancelDetection,
  } = useAppStore();

  if (!isOverlayMinimized || (!isGenerating && !isDetecting)) return null;

  const pct = Math.round(generationProgress * 100);

  return (
    <div className="w-full bg-dark-medium border-t border-dark-border flex items-center gap-3 px-4 h-12 flex-shrink-0">
      <Loader2 className="w-4 h-4 text-accent-textual animate-spin flex-shrink-0" />

      <span className="text-sm font-medium text-text-primary flex-shrink-0">
        {isDetecting ? 'Detecting Columns' : 'Generating Constraints'}
      </span>

      {/* Progress bar */}
      <div className="w-24 bg-dark-darkest rounded-full h-1.5 overflow-hidden flex-shrink-0">
        {isDetecting ? (
          <div className="bg-accent-textual h-full rounded-full animate-pulse w-full" />
        ) : (
          <div
            className="bg-accent-textual h-full rounded-full transition-all duration-300 ease-out"
            style={{ width: `${pct}%` }}
          />
        )}
      </div>

      <span className="text-xs text-text-muted flex-shrink-0">
        {isDetecting ? 'Detecting...' : `${pct}%`}
      </span>

      {!isDetecting && currentStep && (
        <span className="text-xs text-text-muted flex-1 min-w-0 truncate">
          {currentStep}
        </span>
      )}

      <button
        onClick={restoreOverlay}
        className="flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium text-text-muted hover:text-text-primary hover:bg-dark-border transition-colors flex-shrink-0"
        title="Restore overlay"
      >
        <Maximize2 size={12} />
        Restore
      </button>

      <button
        onClick={isDetecting ? cancelDetection : cancelGeneration}
        className="flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium border border-red-600/70 text-red-400 hover:bg-red-900/40 hover:border-red-500 hover:text-red-300 transition-colors flex-shrink-0"
        title="Cancel"
      >
        <X size={12} />
        Cancel
      </button>
    </div>
  );
};

export default GenerationProgressBar;
