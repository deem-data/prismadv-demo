import { useState, useMemo, useEffect } from 'react';
import ReactDiffViewer, { DiffMethod } from 'react-diff-viewer-continued';
import { useAppStore } from '@/store';

interface InstructionDiffViewProps {
  label: string;
  before: string;
  after: string;
}

type ViewMode = 'diff' | 'optimized' | 'baseline';

function countChanges(before: string, after: string): { added: number; removed: number } {
  const oldLines = before.split('\n');
  const newLines = after.split('\n');
  const oldSet = new Map<string, number>();
  for (const l of oldLines) oldSet.set(l, (oldSet.get(l) ?? 0) + 1);
  const newSet = new Map<string, number>();
  for (const l of newLines) newSet.set(l, (newSet.get(l) ?? 0) + 1);

  let removed = 0;
  for (const [line, count] of oldSet) {
    removed += Math.max(0, count - (newSet.get(line) ?? 0));
  }
  let added = 0;
  for (const [line, count] of newSet) {
    added += Math.max(0, count - (oldSet.get(line) ?? 0));
  }
  return { added, removed };
}

function useResolvedTheme(): 'dark' | 'light' {
  const themePreference = useAppStore((state) => state.ui.themePreference);
  const [resolved, setResolved] = useState<'dark' | 'light'>(() => {
    if (themePreference === 'dark' || themePreference === 'light') return themePreference;
    if (typeof window === 'undefined') return 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  useEffect(() => {
    if (themePreference === 'dark' || themePreference === 'light') {
      setResolved(themePreference);
      return;
    }
    const mql = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => setResolved(mql.matches ? 'dark' : 'light');
    handler();
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, [themePreference]);

  return resolved;
}

const darkStyles = {
  variables: {
    dark: {
      diffViewerBackground: '#1e1e1e',
      diffViewerColor: '#d4d4d4',
      addedBackground: '#2ea04320',
      addedColor: '#d4d4d4',
      removedBackground: '#f8514920',
      removedColor: '#d4d4d4',
      wordAddedBackground: '#2ea04350',
      wordRemovedBackground: '#f8514950',
      addedGutterBackground: '#2ea04330',
      removedGutterBackground: '#f8514930',
      gutterBackground: '#1e1e1e',
      gutterBackgroundDark: '#1a1a1a',
      highlightBackground: '#ffffff10',
      highlightGutterBackground: '#ffffff10',
      codeFoldGutterBackground: '#2d2d2d',
      codeFoldBackground: '#2d2d2d',
      emptyLineBackground: '#252525',
      gutterColor: '#555555',
      addedGutterColor: '#7ee787',
      removedGutterColor: '#ffa198',
      codeFoldContentColor: '#888888',
      diffViewerTitleBackground: '#2d2d2d',
      diffViewerTitleColor: '#cccccc',
      diffViewerTitleBorderColor: '#3e3e3e',
    },
  },
  line: {
    padding: '2px 8px',
    fontSize: '12px',
    fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
    wordBreak: 'break-word' as const,
  },
  gutter: {
    padding: '2px 8px',
    fontSize: '11px',
    minWidth: '35px',
  },
  contentText: {
    fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
    fontSize: '12px',
    lineHeight: '1.5',
  },
  diffContainer: {
    tableLayout: 'fixed' as const,
    width: '100%',
    overflowX: 'hidden' as const,
  },
};

const lightStyles = {
  variables: {
    light: {
      diffViewerBackground: '#ffffff',
      diffViewerColor: '#24292f',
      addedBackground: '#dafbe1',
      addedColor: '#24292f',
      removedBackground: '#ffebe9',
      removedColor: '#24292f',
      wordAddedBackground: '#abf2bc',
      wordRemovedBackground: '#ff818266',
      addedGutterBackground: '#ccffd8',
      removedGutterBackground: '#ffd7d5',
      gutterBackground: '#f6f8fa',
      gutterBackgroundDark: '#f0f1f3',
      highlightBackground: '#fffbdd',
      highlightGutterBackground: '#fff5b1',
      codeFoldGutterBackground: '#f6f8fa',
      codeFoldBackground: '#f6f8fa',
      emptyLineBackground: '#fafbfc',
      gutterColor: '#8b949e',
      addedGutterColor: '#1a7f37',
      removedGutterColor: '#cf222e',
      codeFoldContentColor: '#656d76',
      diffViewerTitleBackground: '#f6f8fa',
      diffViewerTitleColor: '#24292f',
      diffViewerTitleBorderColor: '#d0d7de',
    },
  },
  line: {
    padding: '2px 8px',
    fontSize: '12px',
    fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
    wordBreak: 'break-word' as const,
  },
  gutter: {
    padding: '2px 8px',
    fontSize: '11px',
    minWidth: '35px',
  },
  contentText: {
    fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
    fontSize: '12px',
    lineHeight: '1.5',
  },
  diffContainer: {
    tableLayout: 'fixed' as const,
    width: '100%',
    overflowX: 'hidden' as const,
  },
};

function ViewToggle({ mode, onChange }: { mode: ViewMode; onChange: (m: ViewMode) => void }) {
  const options: { value: ViewMode; label: string }[] = [
    { value: 'diff', label: 'Diff' },
    { value: 'optimized', label: 'Optimized' },
    { value: 'baseline', label: 'Baseline' },
  ];
  return (
    <div className="flex bg-dark-darkest rounded overflow-hidden border border-dark-border">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={(e) => { e.stopPropagation(); onChange(opt.value); }}
          className={`px-2 py-0.5 text-[10px] transition-colors ${
            mode === opt.value
              ? 'bg-violet-500/20 text-violet-400 font-medium'
              : 'text-text-muted hover:text-text-secondary'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

function PlainTextView({ text }: { text: string }) {
  return (
    <div className="bg-dark-darkest overflow-x-auto max-h-[400px] overflow-y-auto">
      <div className="font-mono text-[12px] leading-[1.5] p-3 text-text-secondary whitespace-pre-wrap break-words">
        {text}
      </div>
    </div>
  );
}

export function InstructionDiffView({ before, after }: Omit<InstructionDiffViewProps, 'label'>) {
  const [viewMode, setViewMode] = useState<ViewMode>('diff');
  const resolvedTheme = useResolvedTheme();

  const { added: addedCount, removed: removedCount } = useMemo(
    () => countChanges(before, after),
    [before, after],
  );
  const hasChanges = addedCount > 0 || removedCount > 0;

  return (
    <div className="border border-dark-border rounded-md overflow-hidden">
      {/* Toolbar: change stats + view toggle */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-dark-darkest border-b border-dark-border">
        <div className="flex items-center gap-2">
          {hasChanges ? (
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-dark-border">
              <span className="text-green-400">+{addedCount}</span>
              <span className="text-text-muted mx-1">/</span>
              <span className="text-red-400">-{removedCount}</span>
            </span>
          ) : (
            <span className="text-[10px] text-text-muted">unchanged</span>
          )}
        </div>
        <ViewToggle mode={viewMode} onChange={setViewMode} />
      </div>

          {viewMode === 'diff' && (
            <div className="max-h-[400px] overflow-y-auto overflow-x-hidden">
              <ReactDiffViewer
                oldValue={before}
                newValue={after}
                splitView={false}
                useDarkTheme={resolvedTheme === 'dark'}
                compareMethod={DiffMethod.LINES}
                styles={resolvedTheme === 'dark' ? darkStyles : lightStyles}
                hideLineNumbers={false}
              />
            </div>
          )}

          {viewMode === 'optimized' && <PlainTextView text={after} />}
          {viewMode === 'baseline' && <PlainTextView text={before} />}
    </div>
  );
}
