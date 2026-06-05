import { useEffect, useRef, useState } from 'react';
import ReactDOM from 'react-dom';
import * as Dialog from '@radix-ui/react-dialog';
import * as Tabs from '@radix-ui/react-tabs';
import { X, ChevronDown, ChevronRight, Wand2, Sparkles, Loader2, Check, Database, Settings2, Shuffle, Pencil, RotateCcw } from 'lucide-react';
import { useAppStore } from '@/store';
import { DEFAULT_MODELS } from '@/store/slices/llmSlice';
import apiClient from '@/api';
import type { OptimizationConfig, PromptInstructions } from '@/types';
import { InstructionDiffView } from './InstructionDiffView';

/** Reusable styled dropdown matching the LLM Settings design. */
function CustomSelect<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label?: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const selected = options.find((o) => o.value === value);

  return (
    <div ref={ref}>
      {label && (
        <label className="block text-[10px] text-text-muted uppercase tracking-wider mb-1.5">{label}</label>
      )}
      <div className="relative">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="w-full flex items-center justify-between px-3 py-1.5 bg-dark-darkest border border-dark-border rounded-md text-xs text-text-primary hover:border-text-muted focus:outline-none focus:border-violet-500/50 transition-colors"
        >
          <span>{selected?.label ?? value}</span>
          <ChevronDown size={12} className={`text-text-muted transition-transform ${open ? 'rotate-180' : ''}`} />
        </button>
        {open && (
          <ul className="absolute z-50 mt-1 w-full bg-dark-light border border-dark-border rounded-md shadow-lg py-1 max-h-48 overflow-y-auto">
            {options.map((opt) => (
              <li key={opt.value}>
                <button
                  type="button"
                  onClick={() => { onChange(opt.value); setOpen(false); }}
                  className={`w-full flex items-center gap-2 px-3 py-1.5 text-xs text-left transition-colors ${
                    opt.value === value
                      ? 'bg-violet-500/15 text-violet-400'
                      : 'text-text-primary hover:bg-dark-border/50'
                  }`}
                >
                  <span className={`w-3 flex-shrink-0 ${opt.value === value ? '' : 'opacity-0'}`}>
                    <Check size={11} />
                  </span>
                  <span>{opt.label}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

const CACHED_SECTIONS: { key: keyof PromptInstructions; label: string }[] = [
  { key: 'columnAccess', label: 'Data Flow Detection' },
  { key: 'assumptionExtraction', label: 'Assumption Extraction' },
  { key: 'constraintGeneration', label: 'Constraint Generation' },
];

const LIVE_SECTIONS: { key: keyof PromptInstructions; label: string }[] = [
  { key: 'columnAccess', label: 'Data Flow Detection' },
  { key: 'assumptionExtraction', label: 'Assumption Extraction' },
  { key: 'constraintGeneration', label: 'Constraint Generation' },
];

function ScoreRow({ before, after }: { before: number; after: number }) {
  const improved = after > before;
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-text-muted">F1 Score:</span>
      <span className="font-mono text-text-secondary">{before.toFixed(2)}</span>
      <span className="text-text-muted">&rarr;</span>
      <span className={`font-mono font-semibold ${improved ? 'text-green-400' : 'text-text-muted'}`}>
        {after.toFixed(2)}
      </span>
      {improved && <span className="text-green-400">&uarr; improved</span>}
      {!improved && before === after && <span className="text-text-muted">no change</span>}
      {!improved && after < before && <span className="text-red-400">&darr; decreased</span>}
    </div>
  );
}

function SplitAssigner({
  label,
  color,
  items,
  available,
  assigned,
  onChange,
}: {
  label: string;
  color: 'amber' | 'sky' | 'violet';
  items: string[];
  available: string[];
  assigned: string[];
  onChange: (items: string[]) => void;
}) {
  const [showAdd, setShowAdd] = useState(false);
  const unassigned = available.filter((s) => !assigned.includes(s));

  const colorClass = {
    amber: 'bg-amber-500/10 text-amber-400',
    sky: 'bg-sky-500/10 text-sky-400',
    violet: 'bg-violet-500/10 text-violet-400',
  }[color];

  return (
    <div>
      <div className="flex items-center gap-1.5 mb-1">
        <span className="text-text-muted text-[10px]">{label}</span>
        <span className="text-text-muted text-[10px]">({items.length})</span>
        {unassigned.length > 0 && (
          <button
            onClick={() => setShowAdd(!showAdd)}
            className="text-[10px] text-violet-400 hover:text-violet-300 ml-auto"
          >
            {showAdd ? 'done' : '+ add'}
          </button>
        )}
      </div>
      <div className="flex flex-wrap gap-1">
        {items.map((s) => (
          <span key={s} className={`font-mono text-[10px] px-1.5 py-0.5 rounded inline-flex items-center gap-1 ${colorClass}`}>
            {s}
            <button
              onClick={() => onChange(items.filter((x) => x !== s))}
              className="opacity-50 hover:opacity-100"
            >
              <X size={8} />
            </button>
          </span>
        ))}
        {items.length === 0 && <span className="text-[10px] text-text-muted italic">none</span>}
      </div>
      {showAdd && unassigned.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1 pt-1 border-t border-dark-border/50">
          {unassigned.map((s) => (
            <button
              key={s}
              onClick={() => { onChange([...items, s]); }}
              className="font-mono text-[10px] px-1.5 py-0.5 bg-dark-darkest text-text-muted rounded hover:bg-dark-border hover:text-text-secondary transition-colors"
            >
              + {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function ErrorConfigPill({ configId, runId }: { configId: string; runId: string }) {
  const [showPopover, setShowPopover] = useState(false);
  const [yamlContent, setYamlContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [pos, setPos] = useState<{ top: number; left: number }>({ top: 0, left: 0 });
  const btnRef = useRef<HTMLButtonElement>(null);
  const popRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!showPopover) return;
    const handler = (e: MouseEvent) => {
      if (popRef.current && !popRef.current.contains(e.target as Node) &&
          btnRef.current && !btnRef.current.contains(e.target as Node)) {
        setShowPopover(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showPopover]);

  const handleClick = async () => {
    if (showPopover) { setShowPopover(false); return; }
    if (btnRef.current) {
      const rect = btnRef.current.getBoundingClientRect();
      setPos({ top: rect.bottom + 4, left: Math.min(rect.left, window.innerWidth - 340) });
    }
    setShowPopover(true);
    if (yamlContent !== null) return;
    setLoading(true);
    try {
      const res = await apiClient.getErrorConfig(runId, configId);
      setYamlContent(res.content);
    } catch {
      setYamlContent('(failed to load)');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button
        ref={btnRef}
        onClick={handleClick}
        className={`font-mono text-[10px] px-1.5 py-0.5 rounded transition-colors cursor-pointer ${
          showPopover
            ? 'bg-violet-500/20 text-violet-400'
            : 'bg-dark-darkest text-text-muted hover:bg-dark-border hover:text-text-secondary'
        }`}
      >
        {configId}
      </button>
      {showPopover && ReactDOM.createPortal(
        <div
          ref={popRef}
          className="fixed z-[100] w-[320px] bg-dark-light border border-dark-border rounded-md shadow-xl overflow-hidden"
          style={{ top: pos.top, left: pos.left }}
        >
          <div className="px-3 py-1.5 bg-dark-darkest text-[10px] text-text-muted font-medium border-b border-dark-border flex items-center justify-between">
            <span>Error Config #{configId}</span>
            <button onClick={() => setShowPopover(false)} className="text-text-muted hover:text-text-primary">
              <X size={10} />
            </button>
          </div>
          <div className="p-2 max-h-[200px] overflow-y-auto">
            {loading ? (
              <div className="flex items-center gap-1.5 text-[10px] text-text-muted py-2">
                <Loader2 className="w-3 h-3 animate-spin" /> Loading...
              </div>
            ) : (
              <pre className="font-mono text-[10px] text-text-secondary whitespace-pre-wrap">{yamlContent}</pre>
            )}
          </div>
        </div>,
        document.body,
      )}
    </>
  );
}

function ConfigView({ config, runId }: { config: OptimizationConfig; runId: string }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border border-dark-border rounded-md overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium text-text-secondary hover:text-text-primary bg-dark-darkest hover:bg-dark-border transition-colors"
      >
        <span className="flex items-center gap-1.5">
          <Settings2 className="w-3.5 h-3.5" />
          Run Configuration
        </span>
        {open
          ? <ChevronDown className="w-3.5 h-3.5 flex-shrink-0" />
          : <ChevronRight className="w-3.5 h-3.5 flex-shrink-0" />}
      </button>
      {open && (
        <div className="px-3 py-2.5 bg-dark-light space-y-2 text-xs">
          {/* Config */}
          <div className="grid grid-cols-[140px_1fr] gap-y-1.5 gap-x-3">
            <span className="text-text-muted">Proposer LLM</span>
            <span className="font-mono text-text-secondary">{config.proposerLlm ?? 'gpt-5'}</span>
            <span className="text-text-muted">Rounds</span>
            <span className="font-mono text-text-secondary">{config.maxRounds}</span>
          </div>

          {/* Script splits */}
          <div className="border-t border-dark-border pt-2 space-y-1.5">
            <div>
              <span className="text-text-muted">Train scripts</span>
              <span className="text-text-muted ml-1">({config.trainScripts.length})</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {config.trainScripts.map((s) => (
                  <span key={s} className="font-mono text-[10px] px-1.5 py-0.5 bg-amber-500/10 text-amber-400 rounded">
                    {s}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <span className="text-text-muted">Eval scripts</span>
              <span className="text-text-muted ml-1">({config.evalScripts.length})</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {config.evalScripts.map((s) => (
                  <span key={s} className="font-mono text-[10px] px-1.5 py-0.5 bg-sky-500/10 text-sky-400 rounded">
                    {s}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <span className="text-text-muted">Test scripts</span>
              <span className="text-text-muted ml-1">({config.testScripts.length})</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {config.testScripts.map((s) => (
                  <span key={s} className="font-mono text-[10px] px-1.5 py-0.5 bg-violet-500/10 text-violet-400 rounded">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Error configs */}
          <div className="border-t border-dark-border pt-2 space-y-1.5">
            <div>
              <span className="text-text-muted">Train/eval error configs</span>
              <span className="text-text-muted ml-1">({config.trainErrorConfigs.length})</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {config.trainErrorConfigs.map((c) => (
                  <ErrorConfigPill key={c} configId={c} runId={runId} />
                ))}
              </div>
            </div>
            <div>
              <span className="text-text-muted">Test error configs</span>
              <span className="text-text-muted ml-1">({config.testErrorConfigs.length})</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {config.testErrorConfigs.map((c) => (
                  <ErrorConfigPill key={c} configId={c} runId={runId} />
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface PromptsPanelProps {
  open: boolean;
  onClose: () => void;
}

export function PromptsPanel({ open, onClose }: PromptsPanelProps) {
  const {
    currentPrompts,
    optimizedPrompts,
    evalF1Before,
    evalF1After,
    isOptimizing,
    optimizationJobId,
    optimizationProgress,
    optimizationStep,
    optimizationLog,
    fetchCurrentPrompts,
    startOptimization,
    applyOptimizedPrompts,
    resetOptimizedPrompts,
    snapshotConstraints,
    generateConstraints,
    // Cached runs
    cachedRuns,
    selectedCachedRunId,
    cachedRunDetail,
    isLoadingCachedRuns,
    fetchCachedRuns,
    selectCachedRun,
    applyCachedRun,
    addToast,
    // LLM settings
    llmSettings,
  } = useAppStore();

  const providerModels = DEFAULT_MODELS[llmSettings.provider];

  const [activeTab, setActiveTab] = useState<string>('live');
  const [selectedModule, setSelectedModule] = useState<keyof PromptInstructions>('constraintGeneration');
  const [liveConfigOpen, setLiveConfigOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editDraft, setEditDraft] = useState('');

  // Live optimization config
  const [liveDataset, setLiveDataset] = useState('sleep_health');
  const [liveRounds, setLiveRounds] = useState(3);
  const [liveBudget, setLiveBudget] = useState(3);
  const [liveNTrain, setLiveNTrain] = useState(3);
  const [liveModel, setLiveModel] = useState('');
  const [liveProposerModel, setLiveProposerModel] = useState('');

  // Dataset split config
  const [availableScripts, setAvailableScripts] = useState<string[]>([]);
  const [availableErrors, setAvailableErrors] = useState<string[]>([]);
  const [trainScripts, setTrainScripts] = useState<string[]>([]);
  const [evalScripts, setEvalScripts] = useState<string[]>([]);
  const [testScripts, setTestScripts] = useState<string[]>([]);
  const [trainErrors, setTrainErrors] = useState<string[]>([]);
  const [testErrors, setTestErrors] = useState<string[]>([]);

  // Load available scripts/errors when dataset changes
  useEffect(() => {
    if (!liveDataset) return;
    apiClient.getDatasetInfo(liveDataset).then((info) => {
      setAvailableScripts(info.scripts);
      setAvailableErrors(info.errorConfigs);
      // Default split: 40% train, 30% eval, 30% test for scripts
      const s = info.scripts;
      const t1 = Math.ceil(s.length * 0.4);
      const t2 = Math.ceil(s.length * 0.7);
      setTrainScripts(s.slice(0, t1));
      setEvalScripts(s.slice(t1, t2));
      setTestScripts(s.slice(t2));
      // Default split: 50/50 for errors
      const e = info.errorConfigs;
      const mid = Math.ceil(e.length * 0.5);
      setTrainErrors(e.slice(0, mid));
      setTestErrors(e.slice(mid));
    }).catch(() => {});
  }, [liveDataset]);

  useEffect(() => {
    if (open) {
      fetchCurrentPrompts();
      fetchCachedRuns();
    }
  }, [open]);

  const handleApplyAndRegenerate = async () => {
    snapshotConstraints();
    await applyOptimizedPrompts();
    onClose();
    generateConstraints(true);
  };

  const handleApplyCachedAndRegenerate = async () => {
    snapshotConstraints();
    await applyCachedRun();
    onClose();
    generateConstraints(true);
  };

  const improved = evalF1Before !== null && evalF1After !== null && evalF1After > evalF1Before;

  return (
    <Dialog.Root open={open} onOpenChange={(v) => !v && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-dark-light border border-dark-border rounded-lg shadow-xl w-[960px] h-[85vh] flex flex-col z-50">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-dark-border flex-shrink-0">
            <div className="flex items-center gap-2">
              <Wand2 className="w-4 h-4 text-violet-400" />
              <Dialog.Title className="text-sm font-semibold text-text-primary">
                Prompt Optimization
              </Dialog.Title>
            </div>
            <button
              onClick={onClose}
              className="text-text-muted hover:text-text-primary transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <Tabs.Root value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0">
            {/* Tabs */}
            <Tabs.List className="flex border-b border-dark-border px-4 flex-shrink-0">
              <Tabs.Trigger
                value="live"
                className="px-3 py-2 text-xs font-medium text-text-muted hover:text-text-primary border-b-2 border-transparent data-[state=active]:text-violet-400 data-[state=active]:border-violet-400 transition-colors"
              >
                <span className="flex items-center gap-1.5">
                  <Wand2 className="w-3.5 h-3.5" />
                  Current Prompts
                </span>
              </Tabs.Trigger>
              <Tabs.Trigger
                value="cached"
                className="px-3 py-2 text-xs font-medium text-text-muted hover:text-text-primary border-b-2 border-transparent data-[state=active]:text-violet-400 data-[state=active]:border-violet-400 transition-colors"
              >
                <span className="flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5" />
                  Cached Runs
                  {cachedRuns && (
                    <span className="text-[10px] text-text-muted bg-dark-darkest px-1.5 py-0.5 rounded-full">
                      {cachedRuns.length}
                    </span>
                  )}
                </span>
              </Tabs.Trigger>
            </Tabs.List>

            {/* Cached Runs Tab */}
            <Tabs.Content value="cached" className="flex-1 flex flex-col min-h-0 overflow-hidden data-[state=inactive]:hidden">
              <div className="flex-1 overflow-y-auto min-h-0 px-4 py-3 space-y-3">
                {/* Run selector */}
                {cachedRuns && cachedRuns.length > 0 && (
                  <CustomSelect
                    label="Select optimization run"
                    value={selectedCachedRunId ?? ''}
                    options={cachedRuns.map((run) => ({
                      value: run.runId,
                      label: `${run.trainDataset} [${run.initialScore.toFixed(1)} → ${run.finalScore.toFixed(1)}]${run.improved ? ' ✓' : ''}`,
                    }))}
                    onChange={(v) => selectCachedRun(v || null)}
                  />
                )}

                {isLoadingCachedRuns && !cachedRunDetail && (
                  <div className="flex items-center justify-center py-8 gap-2 text-xs text-text-muted">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Loading...
                  </div>
                )}

                {/* Diff view */}
                {cachedRunDetail && (
                  <div className="space-y-3">
                    {/* Run metadata */}
                    <div className="flex items-center gap-3 text-xs text-text-muted">
                      <span>
                        <span className="text-text-secondary">{cachedRunDetail.trainDataset}</span>
                        {' '}dataset
                      </span>
                      <span className="text-dark-border">|</span>
                      <ScoreRow
                        before={cachedRunDetail.initialScore}
                        after={cachedRunDetail.finalScore}
                      />
                    </div>

                    {/* Config */}
                    <ConfigView config={cachedRunDetail.config} runId={cachedRunDetail.runId} />

                    {/* Module selector */}
                    <CustomSelect
                      label="Module"
                      value={selectedModule}
                      options={CACHED_SECTIONS.map(({ key, label }) => ({ value: key, label }))}
                      onChange={(v) => setSelectedModule(v as keyof PromptInstructions)}
                    />

                    {/* Instruction diff for selected module */}
                    <InstructionDiffView
                      key={selectedModule}
                      before={cachedRunDetail.baselineInstructions[selectedModule]}
                      after={cachedRunDetail.optimizedInstructions[selectedModule]}
                    />
                  </div>
                )}

                {!cachedRunDetail && !isLoadingCachedRuns && cachedRuns && cachedRuns.length === 0 && (
                  <p className="text-sm text-text-muted text-center py-8">
                    No cached optimization runs found in benchmarks/optimization_runs/
                  </p>
                )}
              </div>

              {/* Cached runs footer */}
              {cachedRunDetail && (
                <div className="px-4 py-3 border-t border-dark-border flex-shrink-0">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleApplyCachedAndRegenerate}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-green-700 hover:bg-green-600 text-white rounded transition-colors"
                    >
                      <Check className="w-3.5 h-3.5" />
                      Apply &amp; Regenerate
                    </button>
                  </div>
                </div>
              )}
            </Tabs.Content>

            {/* Live Optimization Tab */}
            <Tabs.Content value="live" className="flex-1 flex flex-col min-h-0 overflow-hidden data-[state=inactive]:hidden">
              <div className="flex-1 overflow-y-auto min-h-0 px-4 py-3 space-y-3">
                {/* Run Configuration */}
                <div className="border border-dark-border rounded-md overflow-hidden">
                  <button
                    onClick={() => setLiveConfigOpen((v) => !v)}
                    className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium text-text-secondary hover:text-text-primary bg-dark-darkest hover:bg-dark-border transition-colors"
                  >
                    <span className="flex items-center gap-1.5">
                      <Settings2 className="w-3.5 h-3.5" />
                      Run Configuration
                    </span>
                    {liveConfigOpen
                      ? <ChevronDown className="w-3.5 h-3.5 flex-shrink-0" />
                      : <ChevronRight className="w-3.5 h-3.5 flex-shrink-0" />}
                  </button>
                  {liveConfigOpen && <div className="px-3 py-2.5 bg-dark-light space-y-2.5 text-xs">
                    {/* Row 1: Dataset + Model */}
                    <div className="grid grid-cols-2 gap-3">
                      <CustomSelect
                        label="Dataset"
                        value={liveDataset}
                        options={[
                          { value: 'hr_analytics', label: 'hr_analytics' },
                          { value: 'students', label: 'students' },
                          { value: 'sleep_health', label: 'sleep_health' },
                          { value: 'IPL_win_prediction', label: 'IPL_win_prediction' },
                          { value: 'imdb', label: 'imdb' },
                        ]}
                        onChange={setLiveDataset}
                      />
                      <CustomSelect
                        label="Execution LLM"
                        value={liveModel || providerModels[0]}
                        options={providerModels.map((m) => ({ value: m, label: m }))}
                        onChange={setLiveModel}
                      />
                    </div>

                    {/* Row 1b: Proposer LLM */}
                    <CustomSelect
                      label="Proposer LLM (stronger model for instruction reflection)"
                      value={liveProposerModel || providerModels[providerModels.length - 1]}
                      options={providerModels.map((m) => ({ value: m, label: m }))}
                      onChange={setLiveProposerModel}
                    />

                    {/* Row 2: Rounds, Budget, Mini-batch */}
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <label className="text-text-muted block mb-1">Rounds</label>
                        <input
                          type="number" min={1} max={5}
                          value={liveRounds}
                          onChange={(e) => setLiveRounds(Number(e.target.value))}
                          className="w-full bg-dark-darkest text-text-secondary border border-dark-border rounded px-2 py-1 focus:outline-none focus:border-violet-500/50"
                        />
                      </div>
                      <div>
                        <label className="text-text-muted block mb-1">Budget</label>
                        <input
                          type="number" min={1} max={20}
                          value={liveBudget}
                          onChange={(e) => setLiveBudget(Number(e.target.value))}
                          className="w-full bg-dark-darkest text-text-secondary border border-dark-border rounded px-2 py-1 focus:outline-none focus:border-violet-500/50"
                        />
                      </div>
                      <div>
                        <label className="text-text-muted block mb-1">Mini-batch</label>
                        <input
                          type="number" min={1} max={10}
                          value={liveNTrain}
                          onChange={(e) => setLiveNTrain(Number(e.target.value))}
                          className="w-full bg-dark-darkest text-text-secondary border border-dark-border rounded px-2 py-1 focus:outline-none focus:border-violet-500/50"
                        />
                      </div>
                    </div>

                    {/* Script split */}
                    {availableScripts.length > 0 && (
                      <div className="border-t border-dark-border pt-2 space-y-1.5">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-text-muted font-medium">Script Split</span>
                          <button
                            onClick={() => {
                              const shuffled = [...availableScripts].sort(() => Math.random() - 0.5);
                              const t1 = Math.ceil(shuffled.length * 0.4);
                              const t2 = Math.ceil(shuffled.length * 0.7);
                              setTrainScripts(shuffled.slice(0, t1));
                              setEvalScripts(shuffled.slice(t1, t2));
                              setTestScripts(shuffled.slice(t2));
                            }}
                            className="flex items-center gap-1 text-[10px] text-text-muted hover:text-violet-400 transition-colors"
                          >
                            <Shuffle size={10} /> Shuffle
                          </button>
                        </div>
                        <SplitAssigner
                          label="Train"
                          color="amber"
                          items={trainScripts}
                          available={availableScripts}
                          assigned={[...trainScripts, ...evalScripts, ...testScripts]}
                          onChange={setTrainScripts}
                        />
                        <SplitAssigner
                          label="Eval"
                          color="sky"
                          items={evalScripts}
                          available={availableScripts}
                          assigned={[...trainScripts, ...evalScripts, ...testScripts]}
                          onChange={setEvalScripts}
                        />
                        <SplitAssigner
                          label="Test"
                          color="violet"
                          items={testScripts}
                          available={availableScripts}
                          assigned={[...trainScripts, ...evalScripts, ...testScripts]}
                          onChange={setTestScripts}
                        />
                      </div>
                    )}

                    {/* Error config split */}
                    {availableErrors.length > 0 && (
                      <div className="border-t border-dark-border pt-2 space-y-1.5">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-text-muted font-medium">Error Config Split</span>
                          <button
                            onClick={() => {
                              const shuffled = [...availableErrors].sort(() => Math.random() - 0.5);
                              const mid = Math.ceil(shuffled.length * 0.5);
                              setTrainErrors(shuffled.slice(0, mid));
                              setTestErrors(shuffled.slice(mid));
                            }}
                            className="flex items-center gap-1 text-[10px] text-text-muted hover:text-violet-400 transition-colors"
                          >
                            <Shuffle size={10} /> Shuffle
                          </button>
                        </div>
                        <SplitAssigner
                          label="Train/Eval"
                          color="amber"
                          items={trainErrors}
                          available={availableErrors}
                          assigned={[...trainErrors, ...testErrors]}
                          onChange={setTrainErrors}
                        />
                        <SplitAssigner
                          label="Test"
                          color="violet"
                          items={testErrors}
                          available={availableErrors}
                          assigned={[...trainErrors, ...testErrors]}
                          onChange={setTestErrors}
                        />
                      </div>
                    )}
                  </div>}
                </div>

                {/* Module selector + prompt view */}
                <CustomSelect
                  label="Module"
                  value={selectedModule}
                  options={LIVE_SECTIONS.map(({ key, label }) => ({ value: key, label }))}
                  onChange={(v) => { setSelectedModule(v as keyof PromptInstructions); setIsEditing(false); }}
                />

                {currentPrompts ? (
                  <div key={selectedModule} className="space-y-2">
                    {/* Show diff view when optimization has completed */}
                    {optimizationJobId && !isOptimizing && optimizedPrompts?.[selectedModule] && optimizedPrompts[selectedModule] !== currentPrompts[selectedModule] ? (
                      <>
                        <InstructionDiffView
                          key={`live-${selectedModule}`}
                          before={currentPrompts[selectedModule]}
                          after={optimizedPrompts[selectedModule]}
                        />
                        <div className="flex items-center gap-2">
                          <button
                            onClick={handleApplyAndRegenerate}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-green-700 hover:bg-green-600 text-white rounded transition-colors"
                          >
                            <Check className="w-3.5 h-3.5" />
                            Apply &amp; Regenerate
                          </button>
                          <button
                            onClick={() => {
                              resetOptimizedPrompts();
                              useAppStore.setState({ optimizationJobId: null });
                            }}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-dark-darkest hover:bg-dark-border text-text-secondary border border-dark-border rounded transition-colors"
                          >
                            <RotateCcw className="w-3.5 h-3.5" />
                            Restore Baseline
                          </button>
                        </div>
                      </>
                    ) : (
                      /* Normal view: read-only or editing */
                      <div className="border border-dark-border rounded-md overflow-hidden">
                        <div className="flex items-center justify-between px-3 py-1.5 bg-dark-darkest border-b border-dark-border">
                          <span className="text-[10px] text-text-muted uppercase tracking-wider">Instruction</span>
                          {!isEditing ? (
                            <button
                              onClick={() => { setIsEditing(true); setEditDraft(currentPrompts[selectedModule]); }}
                              className="flex items-center gap-1 text-[10px] text-text-muted hover:text-violet-400 transition-colors"
                            >
                              <Pencil size={10} /> Edit
                            </button>
                          ) : (
                            <div className="flex items-center gap-1.5">
                              <button
                                onClick={() => {
                                  useAppStore.setState({
                                    currentPrompts: { ...currentPrompts, [selectedModule]: editDraft },
                                  });
                                  setIsEditing(false);
                                }}
                                className="text-[10px] text-green-400 hover:text-green-300 transition-colors"
                              >
                                Save
                              </button>
                              <button
                                onClick={() => setIsEditing(false)}
                                className="text-[10px] text-text-muted hover:text-text-primary transition-colors"
                              >
                                Cancel
                              </button>
                            </div>
                          )}
                        </div>
                        {isEditing ? (
                          <textarea
                            value={editDraft}
                            onChange={(e) => setEditDraft(e.target.value)}
                            className="font-mono text-xs text-text-secondary bg-dark-darkest p-3 w-full h-[400px] leading-relaxed resize-none focus:outline-none focus:ring-1 focus:ring-violet-500/30"
                          />
                        ) : (
                          <div className="font-mono text-xs text-text-secondary bg-dark-darkest p-3 h-[400px] overflow-y-auto leading-relaxed whitespace-pre-wrap">
                            {currentPrompts[selectedModule]}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-text-muted text-center py-8">Loading prompts...</p>
                )}
              </div>

              {/* Live optimization footer */}
              <div className="px-4 py-3 border-t border-dark-border flex-shrink-0 space-y-3">
                {/* F1 score row — only show after a live optimization has completed */}
                {optimizationJobId && evalF1Before !== null && evalF1After !== null && (
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-text-muted">F1 Score:</span>
                    <span className="font-mono text-text-secondary">{evalF1Before.toFixed(3)}</span>
                    <span className="text-text-muted">&rarr;</span>
                    <span className={`font-mono font-semibold ${improved ? 'text-green-400' : 'text-red-400'}`}>
                      {evalF1After.toFixed(3)}
                    </span>
                    <span className={improved ? 'text-green-400' : 'text-red-400'}>
                      {improved ? '↑ improved' : '↓ no improvement'}
                    </span>
                  </div>
                )}

                {/* Progress bar + log */}
                {isOptimizing && (
                  <div className="space-y-2">
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-text-muted truncate pr-2">{optimizationStep}</span>
                        <span className="text-text-muted font-mono flex-shrink-0">
                          {Math.round(optimizationProgress * 100)}%
                        </span>
                      </div>
                      <div className="h-1.5 bg-dark-darkest rounded-full overflow-hidden">
                        <div
                          className="h-full bg-violet-500 transition-all duration-500 rounded-full"
                          style={{ width: `${optimizationProgress * 100}%` }}
                        />
                      </div>
                    </div>
                    {optimizationLog.length > 0 && (
                      <div className="bg-dark-darkest border border-dark-border rounded-md p-2 max-h-[160px] overflow-y-auto">
                        {optimizationLog.map((entry, i) => (
                          <div key={i} className={`font-mono text-[10px] leading-relaxed ${
                            entry.includes('ACCEPTED') ? 'text-green-400' :
                            entry.includes('REJECTED') ? 'text-red-400/70' :
                            entry.includes('NEW BEST') ? 'text-green-300 font-semibold' :
                            entry.includes('score') || entry.includes('Score') ? 'text-text-secondary' :
                            'text-text-muted'
                          }`}>
                            {entry}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Action buttons */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      const execModel = liveModel || providerModels[0];
                      const propModel = liveProposerModel || providerModels[providerModels.length - 1];
                      startOptimization({
                        dataset: liveDataset,
                        nRounds: liveRounds,
                        budget: liveBudget,
                        nTrain: liveNTrain,
                        maxUnits: 200,
                        options: {
                          model: `${llmSettings.provider}/${execModel}`,
                          proposerModel: `${llmSettings.provider}/${propModel}`,
                        },
                      });
                    }}
                    disabled={isOptimizing}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-violet-600 hover:bg-violet-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded transition-colors"
                  >
                    {isOptimizing ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        Optimizing...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3.5 h-3.5" />
                        Run Optimization
                      </>
                    )}
                  </button>

                  {isOptimizing && optimizationJobId && (
                    <button
                      onClick={async () => {
                        try {
                          await apiClient.cancelOptimizationJob(optimizationJobId);
                        } catch {}
                        useAppStore.setState({ isOptimizing: false, optimizationProgress: 0, optimizationStep: '' });
                        addToast({ type: 'info', message: 'Optimization stopped' });
                      }}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-red-700 hover:bg-red-600 text-white rounded transition-colors"
                    >
                      <X className="w-3.5 h-3.5" />
                      Stop
                    </button>
                  )}

                </div>
              </div>
            </Tabs.Content>
          </Tabs.Root>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
