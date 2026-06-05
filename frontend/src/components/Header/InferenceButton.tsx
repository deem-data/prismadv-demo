import { useState, useEffect } from 'react';
import { Sparkles } from 'lucide-react';
import * as Tooltip from '@radix-ui/react-tooltip';
import { useAppStore } from '@/store';
import apiClient from '@/api';
import { CacheConfirmDialog } from '@/components/Dialogs/CacheConfirmDialog';
import { ColumnSelectionDialog } from '@/components/Dialogs/ColumnSelectionDialog';
import { PasswordDialog, isDemoAuthorized } from '@/components/Dialogs/PasswordDialog';

export function InferenceButton() {
  const {
    taskFile,
    dataset,
    isGenerating,
    isDetecting,
    generateConstraints,
    startDetection,
    stopDetection,
    showCacheDialog,
    useCachedResult,
    dismissCacheDialog,
    llmSettings,
    preferences,
    addToast,
    setAPIKey,
    setUseOwnKey,
  } = useAppStore();

  const [accessedColumns, setAccessedColumns] = useState<string[]>([]);
  const [showColumnDialog, setShowColumnDialog] = useState(false);
  const [isRegenerate, setIsRegenerate] = useState(false);
  const [showDetectionCacheDialog, setShowDetectionCacheDialog] = useState(false);
  const [pendingDetectionResult, setPendingDetectionResult] = useState<{ allColumns: string[]; accessedColumns: string[] } | null>(null);
  const [showPasswordDialog, setShowPasswordDialog] = useState(false);
  const [pendingRegenerate, setPendingRegenerate] = useState(false);

  // Reset local detection state when the loaded script/dataset changes
  useEffect(() => {
    setAccessedColumns([]);
    setShowColumnDialog(false);
    setShowDetectionCacheDialog(false);
    setPendingDetectionResult(null);
  }, [taskFile?.id, dataset?.id]);

  const isBusy = isDetecting || isGenerating;
  const canGenerate = taskFile && dataset && !isBusy;

  const runDetection = async (forRegenerate: boolean, forceRedetect = false) => {
    if (!taskFile || !dataset) return;
    setIsRegenerate(forRegenerate);

    const controller = new AbortController();
    startDetection(controller);

    try {
      const options: Record<string, unknown> = { model: llmSettings.model };
      if (llmSettings.useOwnKey && llmSettings.apiKey) {
        options.apiKey = llmSettings.apiKey;
      }

      const result = await apiClient.detectColumns(
        { taskFileId: taskFile.id, datasetId: dataset.id, options, forceRedetect },
        controller.signal,
      );

      stopDetection();

      if (result.cached) {
        setPendingDetectionResult({ allColumns: result.allColumns, accessedColumns: result.accessedColumns });
        setShowDetectionCacheDialog(true);
        return;
      }

      setAccessedColumns(result.accessedColumns);
      useAppStore.setState({ detectedAccessedColumns: result.accessedColumns });

      const cols = result.accessedColumns.length > 0
        ? result.accessedColumns
        : result.allColumns;

      if (preferences.autoSelectDetectedColumns) {
        try {
          await generateConstraints(forRegenerate, cols);
        } catch (error) {
          console.error('Constraint generation failed:', error);
        }
        return;
      }

      setShowColumnDialog(true);
    } catch (err: any) {
      stopDetection();
      if (err?.cancelled || controller.signal.aborted) return;
      addToast({ type: 'error', message: `Column detection failed: ${err instanceof Error ? err.message : 'Unknown error'}` });
    }
  };

  const acceptCachedDetection = () => {
    if (!pendingDetectionResult) return;
    const cols = pendingDetectionResult.accessedColumns.length > 0
      ? pendingDetectionResult.accessedColumns
      : pendingDetectionResult.allColumns;
    setAccessedColumns(pendingDetectionResult.accessedColumns);
    useAppStore.setState({ detectedAccessedColumns: pendingDetectionResult.accessedColumns });
    setShowDetectionCacheDialog(false);
    setPendingDetectionResult(null);
    if (preferences.autoSelectDetectedColumns) {
      generateConstraints(isRegenerate, cols).catch(console.error);
    } else {
      setShowColumnDialog(true);
    }
  };

  const handleInfer = async (selectedColumns: string[]) => {
    setShowColumnDialog(false);
    try {
      await generateConstraints(isRegenerate, selectedColumns);
    } catch (error) {
      console.error('Constraint generation failed:', error);
    }
  };

  return (
    <>
      {isBusy ? (
        <button
          disabled
          className="flex items-center gap-2 px-3 py-1.5 rounded text-sm font-medium bg-dark-border text-text-muted cursor-not-allowed"
        >
          <Sparkles size={16} className="animate-sparkle" />
          <span>{isDetecting ? 'Detecting...' : 'Generating...'}</span>
        </button>
      ) : canGenerate ? (
        <button
          onClick={() => {
            if (llmSettings.useOwnKey && !llmSettings.apiKey) {
              addToast({ type: 'error', message: 'Please provide an API key in LLM Settings, or switch to the provided API.' });
              return;
            }
            if (isDemoAuthorized(llmSettings.useOwnKey && !!llmSettings.apiKey)) {
              runDetection(false);
            } else {
              setPendingRegenerate(false);
              setShowPasswordDialog(true);
            }
          }}
          className="flex items-center gap-2 px-3 py-1.5 rounded text-sm font-medium transition-all bg-accent-blue text-white hover:bg-accent-blue/90"
        >
          <Sparkles size={16} />
          <span>Inference</span>
        </button>
      ) : (
        <Tooltip.Provider delayDuration={300}>
          <Tooltip.Root>
            <Tooltip.Trigger asChild>
              <span className="inline-flex">
                <button disabled className="flex items-center gap-2 px-3 py-1.5 rounded text-sm font-medium bg-dark-border text-text-muted cursor-not-allowed">
                  <Sparkles size={16} />
                  <span>Inference</span>
                </button>
              </span>
            </Tooltip.Trigger>
            <Tooltip.Portal>
              <Tooltip.Content
                className="bg-dark-medium border border-dark-border rounded px-3 py-1.5 text-xs text-text-secondary shadow-lg z-50"
                sideOffset={5}
              >
                {!taskFile ? 'Upload a task file first' : 'Upload a dataset first'}
                <Tooltip.Arrow className="fill-dark-medium" />
              </Tooltip.Content>
            </Tooltip.Portal>
          </Tooltip.Root>
        </Tooltip.Provider>
      )}

      <PasswordDialog
        open={showPasswordDialog}
        onSuccess={() => {
          setShowPasswordDialog(false);
          runDetection(pendingRegenerate);
        }}
        onUseOwnKey={(key) => {
          setAPIKey(key);
          setUseOwnKey(true);
          setShowPasswordDialog(false);
          runDetection(pendingRegenerate);
        }}
        onClose={() => setShowPasswordDialog(false)}
      />

      <CacheConfirmDialog
        open={showDetectionCacheDialog}
        title="Cached Column Detection Found"
        description="Column detection results for this file and dataset are already cached from this session. Use the cached results or re-run detection?"
        useCacheLabel="Use Cached"
        regenerateLabel="Re-detect"
        onUseCache={acceptCachedDetection}
        onRegenerate={() => {
          setShowDetectionCacheDialog(false);
          setPendingDetectionResult(null);
          runDetection(isRegenerate, true);
        }}
        onClose={() => {
          setShowDetectionCacheDialog(false);
          setPendingDetectionResult(null);
          stopDetection();
        }}
      />

      <ColumnSelectionDialog
        open={showColumnDialog}
        columns={dataset?.columns ?? []}
        accessedColumns={accessedColumns}
        onInfer={handleInfer}
        onClose={() => setShowColumnDialog(false)}
      />

      <CacheConfirmDialog
        open={showCacheDialog}
        onUseCache={useCachedResult}
        onRegenerate={() => {
          dismissCacheDialog();
          if (llmSettings.useOwnKey && !llmSettings.apiKey) {
            addToast({ type: 'error', message: 'Please provide an API key in LLM Settings, or switch to the provided API.' });
            return;
          }
          if (isDemoAuthorized(llmSettings.useOwnKey && !!llmSettings.apiKey)) {
            runDetection(true);
          } else {
            setPendingRegenerate(true);
            setShowPasswordDialog(true);
          }
        }}
        onClose={dismissCacheDialog}
      />
    </>
  );
}
