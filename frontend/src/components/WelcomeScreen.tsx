import { useState } from 'react';
import { Sparkles, Upload, FlaskConical, ArrowRight } from 'lucide-react';
import { useAppStore } from '@/store';
import { EIDBenchDialog } from '@/components/Dialogs/EIDBenchDialog';
import { UploadDialog } from '@/components/Dialogs/UploadDialog';

export function WelcomeScreen() {
  const { loadQuickExample } = useAppStore();
  const [showBenchmark, setShowBenchmark] = useState(false);
  const [showUpload, setShowUpload] = useState(false);

  return (
    <>
      <div className="flex items-center justify-center h-full w-full px-8">
        <div className="max-w-[640px] w-full space-y-8">
          {/* Action cards */}
          <div className="grid grid-cols-1 gap-3">
            {/* Quick Example */}
            <button
              onClick={() => loadQuickExample()}
              className="group flex items-center gap-4 p-4 bg-dark-light border border-dark-border rounded-lg hover:border-accent-blue/50 hover:bg-dark-light/80 transition-all text-left"
            >
              <div className="w-10 h-10 rounded-lg bg-violet-500/10 flex items-center justify-center flex-shrink-0">
                <Sparkles size={20} className="text-violet-400" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-text-primary">Quick Example</div>
                <div className="text-xs text-text-muted mt-0.5">
                  Load a pre-computed example with HR analytics data and 58 constraints
                </div>
              </div>
              <ArrowRight size={16} className="text-text-muted group-hover:text-accent-blue transition-colors flex-shrink-0" />
            </button>

            {/* Load from Benchmark */}
            <button
              onClick={() => setShowBenchmark(true)}
              className="group flex items-center gap-4 p-4 bg-dark-light border border-dark-border rounded-lg hover:border-accent-blue/50 hover:bg-dark-light/80 transition-all text-left"
            >
              <div className="w-10 h-10 rounded-lg bg-sky-500/10 flex items-center justify-center flex-shrink-0">
                <FlaskConical size={20} className="text-sky-400" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-text-primary">Load from Benchmark</div>
                <div className="text-xs text-text-muted mt-0.5">
                  Choose from benchmark datasets with multiple analysis scripts
                </div>
              </div>
              <ArrowRight size={16} className="text-text-muted group-hover:text-accent-blue transition-colors flex-shrink-0" />
            </button>

            {/* Upload your own */}
            <button
              onClick={() => setShowUpload(true)}
              className="group flex items-center gap-4 p-4 bg-dark-light border border-dark-border rounded-lg hover:border-accent-blue/50 hover:bg-dark-light/80 transition-all text-left"
            >
              <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center flex-shrink-0">
                <Upload size={20} className="text-green-400" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-text-primary">Upload Your Own</div>
                <div className="text-xs text-text-muted mt-0.5">
                  Upload a Python task script and CSV dataset to generate constraints
                </div>
              </div>
              <ArrowRight size={16} className="text-text-muted group-hover:text-accent-blue transition-colors flex-shrink-0" />
            </button>
          </div>
        </div>
      </div>

      <EIDBenchDialog open={showBenchmark} onClose={() => setShowBenchmark(false)} />
      <UploadDialog open={showUpload} onClose={() => setShowUpload(false)} />
    </>
  );
}
