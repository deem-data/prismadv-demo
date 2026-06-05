import React from 'react';
import { useAppStore } from '@/store';
import { Loader2, Minus, X } from 'lucide-react';

const LoadingOverlay: React.FC = () => {
  const {
    isGenerating,
    isDetecting,
    generationProgress,
    currentStep,
    isOverlayMinimized,
    cancelGeneration,
    cancelDetection,
    minimizeOverlay,
  } = useAppStore();

  const visible = isGenerating || isDetecting;
  if (!visible || isOverlayMinimized) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-dark-darkest/80 backdrop-blur-sm">
      <div className="bg-dark-medium border border-dark-border rounded-lg p-8 w-96 shadow-2xl relative">
        {/* Minimize button */}
        <button
          onClick={minimizeOverlay}
          className="absolute top-3 right-3 p-1 rounded text-text-muted hover:text-text-primary hover:bg-dark-border transition-colors"
          title="Minimize"
        >
          <Minus size={14} />
        </button>

        <div className="flex flex-col items-center text-center">
          <Loader2 className="w-10 h-10 text-accent-textual animate-spin mb-4" />

          <h2 className="text-lg font-bold text-text-primary mb-1">
            {isDetecting ? 'Detecting Columns' : 'Generating Constraints'}
          </h2>
          <p className="text-sm text-text-muted mb-6">
            {isDetecting
              ? 'Analyzing code to identify accessed columns...'
              : (currentStep || 'Analyzing code and data...')}
          </p>

          {/* Progress Bar */}
          <div className="w-full bg-dark-darkest rounded-full h-2 mb-2 overflow-hidden">
            {isDetecting ? (
              <div className="bg-accent-textual h-full rounded-full animate-pulse w-full" />
            ) : (
              <div
                className="bg-accent-textual h-full transition-all duration-300 ease-out"
                style={{ width: `${Math.round(generationProgress * 100)}%` }}
              />
            )}
          </div>

          <div className="text-[10px] text-text-muted uppercase tracking-widest font-bold mb-6">
            {isDetecting ? 'Detecting...' : `${Math.round(generationProgress * 100)}% Complete`}
          </div>

          <button
            onClick={isDetecting ? cancelDetection : cancelGeneration}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded text-sm font-medium border border-red-600/70 text-red-400 hover:bg-red-900/40 hover:border-red-500 hover:text-red-300 transition-colors"
          >
            <X size={14} />
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};

export default LoadingOverlay;
