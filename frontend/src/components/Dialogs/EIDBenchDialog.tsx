import * as Dialog from '@radix-ui/react-dialog';
import { X, Database, FileCode, Globe, LayoutGrid } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useAppStore } from '@/store';
import apiClient from '@/api';
import type { EIDBenchDataset } from '@/types';

interface EIDBenchDialogProps {
  open: boolean;
  onClose: () => void;
}

export function EIDBenchDialog({ open, onClose }: EIDBenchDialogProps) {
  const { loadEIDBench } = useAppStore();

  const [datasets, setDatasets] = useState<EIDBenchDataset[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<EIDBenchDataset | null>(null);
  const [selectedScript, setSelectedScript] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingList, setLoadingList] = useState(false);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    if (!open) return;
    setSelectedDataset(null);
    setSelectedScript(null);
    setUnavailable(false);
    setLoadingList(true);
    apiClient.getEIDBenchDatasets()
      .then((res) => {
        if (res.datasets.length === 0) setUnavailable(true);
        setDatasets(res.datasets);
      })
      .catch(() => setUnavailable(true))
      .finally(() => setLoadingList(false));
  }, [open]);

  const handleDatasetClick = (ds: EIDBenchDataset) => {
    setSelectedDataset(ds);
    setSelectedScript(null);
  };

  const handleLoad = async () => {
    if (!selectedDataset || !selectedScript) return;
    setLoading(true);
    try {
      await loadEIDBench(selectedDataset.name, selectedScript);
      onClose();
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={onClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-dark-light border border-dark-border rounded-lg shadow-xl z-50 w-[680px] h-[520px] flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-dark-border shrink-0">
            <Dialog.Title className="text-lg font-semibold text-text-primary">
              Load from Benchmark
            </Dialog.Title>
            <Dialog.Close asChild>
              <button className="text-text-secondary hover:text-text-primary transition-colors">
                <X size={18} />
              </button>
            </Dialog.Close>
          </div>

          {/* Body */}
          <div className="flex flex-1 overflow-hidden min-h-0">
            {loadingList ? (
              <div className="flex items-center justify-center w-full py-12 text-text-muted text-sm">
                Loading datasets…
              </div>
            ) : unavailable ? (
              <div className="flex flex-col items-center justify-center w-full py-12 gap-2 text-text-muted text-sm px-8 text-center">
                <Database size={32} className="opacity-30 mb-2" />
                <p>Benchmark datasets are not available.</p>
                <p className="text-xs opacity-70">
                  Set the <code className="bg-dark-border px-1 rounded">EIDBENCH_PATH</code> environment variable to the benchmark root directory and restart the backend.
                </p>
              </div>
            ) : (
              <>
                {/* Left panel: dataset list + description */}
                <div className="w-60 border-r border-dark-border flex flex-col shrink-0 overflow-hidden">
                  {/* Dataset list */}
                  <div className="overflow-y-auto py-2 shrink-0">
                    {datasets.map((ds) => (
                      <button
                        key={ds.name}
                        onClick={() => handleDatasetClick(ds)}
                        className={`w-full text-left px-4 py-2.5 text-sm transition-colors flex items-center gap-2 ${
                          selectedDataset?.name === ds.name
                            ? 'bg-accent-blue/20 text-accent-blue'
                            : 'text-text-secondary hover:bg-dark-border hover:text-text-primary'
                        }`}
                      >
                        <Database size={14} className="shrink-0 opacity-70" />
                        <span className="truncate">{ds.displayName}</span>
                      </button>
                    ))}
                  </div>

                  {/* Dataset description — fixed height, always rendered */}
                  <div className="border-t border-dark-border px-4 py-3 h-36 shrink-0 overflow-hidden">
                    {selectedDataset && (
                      <>
                        <div className="flex flex-col gap-1.5 mb-2">
                          {selectedDataset.domain && (
                            <span className="flex items-center gap-1.5 text-xs text-text-muted">
                              <LayoutGrid size={11} className="opacity-60 shrink-0" />
                              {selectedDataset.domain}
                            </span>
                          )}
                          {selectedDataset.source && (
                            <span className="flex items-center gap-1.5 text-xs text-text-muted">
                              <Globe size={11} className="opacity-60 shrink-0" />
                              {selectedDataset.source}
                            </span>
                          )}
                          <span className="flex items-center gap-1.5 text-xs text-text-muted">
                            <FileCode size={11} className="opacity-60 shrink-0" />
                            {selectedDataset.scripts.length} task script{selectedDataset.scripts.length !== 1 ? 's' : ''}
                          </span>
                        </div>
                        {selectedDataset.description && (
                          <p className="text-xs text-text-secondary leading-relaxed line-clamp-4">
                            {selectedDataset.description}
                          </p>
                        )}
                      </>
                    )}
                  </div>
                </div>

                {/* Right panel: script list */}
                <div className="flex-1 overflow-y-auto py-2">
                  {!selectedDataset ? (
                    <div className="flex items-center justify-center h-full text-text-muted text-sm">
                      Select a dataset
                    </div>
                  ) : (
                    selectedDataset.scripts.map((script) => (
                      <button
                        key={script}
                        onClick={() => setSelectedScript(script)}
                        className={`w-full text-left px-4 py-2.5 text-sm transition-colors flex items-center gap-2 ${
                          selectedScript === script
                            ? 'bg-accent-blue/20 text-accent-blue'
                            : 'text-text-secondary hover:bg-dark-border hover:text-text-primary'
                        }`}
                      >
                        <FileCode size={14} className="shrink-0 opacity-70" />
                        <span className="truncate">{script}</span>
                      </button>
                    ))
                  )}
                </div>
              </>
            )}
          </div>

          {/* Footer */}
          {!unavailable && (
            <div className="flex items-center justify-between px-6 py-3 border-t border-dark-border shrink-0">
              <span className="text-xs text-text-muted">
                {selectedScript
                  ? `${selectedDataset?.displayName} / ${selectedScript}`
                  : 'Choose a dataset and script'}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={onClose}
                  className="px-3 py-1.5 text-sm text-text-secondary hover:text-text-primary transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleLoad}
                  disabled={!selectedDataset || !selectedScript || loading}
                  className={`px-4 py-1.5 rounded text-sm font-medium transition-all ${
                    selectedDataset && selectedScript && !loading
                      ? 'bg-accent-blue text-white hover:bg-accent-blue/90'
                      : 'bg-dark-border text-text-muted cursor-not-allowed'
                  }`}
                >
                  {loading ? 'Loading…' : 'Load'}
                </button>
              </div>
            </div>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
