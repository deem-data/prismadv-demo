import React from 'react';
import { X, CheckCircle2, XCircle, Loader2, FlaskConical } from 'lucide-react';
import type { ErrorBenchmarkResult } from '@/types';

interface PerformanceBenchmarkPanelProps {
  result: ErrorBenchmarkResult | null;
  isRunning: boolean;
  progress: number;
  step: string;
  onClose: () => void;
}

const PerformanceBenchmarkPanel: React.FC<PerformanceBenchmarkPanelProps> = ({
  result,
  isRunning,
  progress,
  step,
  onClose,
}) => {
  if (isRunning) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex items-center justify-between px-3 py-2 border-b border-dark-darkest bg-dark-medium">
          <div className="flex items-center gap-2">
            <FlaskConical size={14} className="text-accent-textual" />
            <span className="text-xs font-semibold text-text-primary uppercase tracking-wider">Error Benchmark</span>
          </div>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary transition-colors">
            <X size={14} />
          </button>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center gap-3 p-4">
          <Loader2 size={24} className="text-accent-textual animate-spin" />
          <div className="w-full max-w-48">
            <div className="h-1.5 bg-dark-darkest rounded-full overflow-hidden">
              <div
                className="h-full bg-accent-textual rounded-full transition-all duration-300"
                style={{ width: `${Math.round(progress * 100)}%` }}
              />
            </div>
          </div>
          <span className="text-xs text-text-muted text-center">{step || 'Starting...'}</span>
          <span className="text-[10px] text-text-muted">{Math.round(progress * 100)}%</span>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex items-center justify-between px-3 py-2 border-b border-dark-darkest bg-dark-medium">
          <div className="flex items-center gap-2">
            <FlaskConical size={14} className="text-accent-textual" />
            <span className="text-xs font-semibold text-text-primary uppercase tracking-wider">Error Benchmark</span>
          </div>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary transition-colors">
            <X size={14} />
          </button>
        </div>
        <div className="flex-1 flex items-center justify-center p-4">
          <span className="text-xs text-text-muted">{step || 'No results'}</span>
        </div>
      </div>
    );
  }

  const errorBatches = result.batches.filter((b) => b.batchId !== 'clean');
  const harmfulBatches = errorBatches.filter((b) => b.harmful);
  const safeBatches = errorBatches.filter((b) => !b.harmful);

  // F1 = 2 * precision * recall / (precision + recall)
  // Recall = detection rate (TP / (TP + FN))
  // Precision = TP / (TP + FP)
  // Balanced F1: accounts for class imbalance between harmful (positive) and safe (negative) batches
  // Uses TP, FP, TN, FN counts directly from the batch results
  // Balanced F1: harmonic mean of TPR (recall) and TNR (1 - false alarm rate)
  // Penalises both missed harmful errors and false alarms on safe data
  const computeF1 = (detectionRate: number, falseAlarmRate: number, _nHarmful: number, nSafe: number) => {
    const tpr = detectionRate;
    const tnr = nSafe > 0 ? 1 - falseAlarmRate : 1;
    return tpr + tnr > 0 ? (2 * tpr * tnr) / (tpr + tnr) : 0;
  };

  const prismadvF1 = computeF1(result.prismadvDetectionRate, result.prismadvFalseAlarmRate, harmfulBatches.length, safeBatches.length);
  const deequF1 = computeF1(result.deequDetectionRate, result.deequFalseAlarmRate, harmfulBatches.length, safeBatches.length);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-dark-darkest bg-dark-medium flex-shrink-0">
        <div className="flex items-center gap-2">
          <FlaskConical size={14} className="text-accent-textual" />
          <span className="text-xs font-semibold text-text-primary uppercase tracking-wider">Error Benchmark</span>
          <span className="text-[10px] text-text-muted">({result.datasetName})</span>
        </div>
        <button onClick={onClose} className="text-text-muted hover:text-text-primary transition-colors">
          <X size={14} />
        </button>
      </div>

      {/* Summary — F1 Score */}
      <div className="px-3 py-2.5 border-b border-dark-darkest bg-dark-medium/50 flex-shrink-0">
        <div className="flex items-center justify-center gap-6">
          <div className="text-[9px] text-text-muted uppercase tracking-wider font-medium">F1 Score</div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-[10px] text-amber-400 font-medium">PrismaDV</span>
            <span className="text-lg font-bold text-amber-400">{(prismadvF1 * 100).toFixed(0)}%</span>
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-[10px] text-sky-400 font-medium">Deequ</span>
            <span className="text-lg font-bold text-sky-400">{(deequF1 * 100).toFixed(0)}%</span>
          </div>
        </div>
      </div>

      {/* Per-batch table */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {/* Table header */}
        <div className="sticky top-0 flex items-center px-3 py-1.5 bg-dark-darkest/80 text-[9px] uppercase tracking-wider text-text-muted font-medium border-b border-dark-border">
          <div className="w-8 flex-shrink-0">#</div>
          <div className="flex-1 min-w-0">Error Type</div>
          <div className="w-12 text-center flex-shrink-0">Label</div>
          <div className="w-14 text-center flex-shrink-0">PrismaDV</div>
          <div className="w-14 text-center flex-shrink-0">Deequ</div>
        </div>

        {/* Error batch rows */}
        {errorBatches.map((batch) => {
          // For harmful batches: detecting (violations > 0) is good
          // For safe batches: detecting is a false alarm (bad)
          const prismadvFired = batch.prismadvViolations > 0;
          const deequFired = batch.deequViolations > 0;
          const prismadvGood = batch.harmful ? prismadvFired : !prismadvFired;
          const deequGood = batch.harmful ? deequFired : !deequFired;

          return (
            <div key={batch.batchId} className={`flex items-center px-3 py-1.5 border-b border-dark-border/50 hover:bg-dark-light/30 transition-colors ${!batch.harmful ? 'opacity-60' : ''}`}>
              <div className="w-8 flex-shrink-0 text-[10px] text-text-muted">{batch.batchId}</div>
              <div className="flex-1 min-w-0 text-xs text-text-secondary truncate" title={batch.errorDescription}>
                {batch.errorDescription}
              </div>
              <div className="w-12 flex items-center justify-center flex-shrink-0">
                <span className={`text-[9px] px-1 py-0.5 rounded font-medium ${batch.harmful ? 'bg-red-500/10 text-red-400' : 'bg-emerald-500/10 text-emerald-400'}`}>
                  {batch.harmful ? 'Harm' : 'Safe'}
                </span>
              </div>
              <div className="w-14 flex items-center justify-center gap-1 flex-shrink-0">
                {prismadvGood ? (
                  <CheckCircle2 size={10} className="text-emerald-400" />
                ) : (
                  <XCircle size={10} className="text-red-400" />
                )}
                <span className={`text-[10px] font-medium ${prismadvFired ? 'text-amber-400' : 'text-text-muted'}`}>
                  {batch.prismadvViolations}
                </span>
              </div>
              <div className="w-14 flex items-center justify-center gap-1 flex-shrink-0">
                {deequGood ? (
                  <CheckCircle2 size={10} className="text-emerald-400" />
                ) : (
                  <XCircle size={10} className="text-red-400" />
                )}
                <span className={`text-[10px] font-medium ${deequFired ? 'text-sky-400' : 'text-text-muted'}`}>
                  {batch.deequViolations}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default PerformanceBenchmarkPanel;
