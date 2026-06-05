import React, { useEffect, useRef, useState } from 'react';
import Editor, { OnMount } from '@monaco-editor/react';
import { useAppStore } from '@/store';

const CodeEditor: React.FC = () => {
  const {
    code,
    codeEditable,
    setCode,
    taskFile,
    annotations,
    highlightCodeLine,
    highlightedLines,
    constraints,
    assumptions,
    assumptionDisplayMode,
    selectedConstraintId,
    selectedAssumptionId,
    selectedColumn,
  } = useAppStore();
  const themePreference = useAppStore((state) => state.ui.themePreference);
  const { editorFontSize, editorWordWrap } = useAppStore((state) => state.preferences);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const editorRef = useRef<any>(null);
  const monacoRef = useRef<any>(null);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);
  const decorationIdsRef = useRef<string[]>([]);
  const [editorReady, setEditorReady] = useState(false);

  const [resolvedTheme, setResolvedTheme] = useState<'dark' | 'light'>(() => {
    if (themePreference === 'dark' || themePreference === 'light') return themePreference;
    if (typeof window === 'undefined') return 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  useEffect(() => {
    if (themePreference === 'dark' || themePreference === 'light') {
      setResolvedTheme(themePreference);
      return;
    }

    const mql = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = () => {
      setResolvedTheme(mql.matches ? 'dark' : 'light');
    };

    handleChange();

    if (mql.addEventListener) {
      mql.addEventListener('change', handleChange);
      return () => mql.removeEventListener('change', handleChange);
    }

    mql.addListener(handleChange);
    return () => mql.removeListener(handleChange);
  }, [themePreference]);

  const monacoThemeName = resolvedTheme === 'dark' ? 'prismadv-dark' : 'prismadv-light';

  const handleEditorMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;

    // Define custom theme
    monaco.editor.defineTheme('prismadv-dark', {
      base: 'vs-dark',
      inherit: true,
      rules: [],
      colors: {
        'editor.background': '#1e1e1e',
        'editor.lineHighlightBackground': '#00000000', // Transparent to avoid conflicts
        'editorLineNumber.foreground': '#858585',
        'editorLineNumber.activeForeground': '#c6c6c6',
      },
    });

    monaco.editor.defineTheme('prismadv-light', {
      base: 'vs',
      inherit: true,
      rules: [],
      colors: {
        'editor.background': '#ffffff',
        'editor.lineHighlightBackground': '#f3f4f6',
        'editorLineNumber.foreground': '#9ca3af',
        'editorLineNumber.activeForeground': '#374151',
      },
    });

    monaco.editor.setTheme(monacoThemeName);

    if (typeof ResizeObserver !== 'undefined' && containerRef.current) {
      resizeObserverRef.current?.disconnect();
      resizeObserverRef.current = new ResizeObserver(() => {
        editor.layout();
      });
      resizeObserverRef.current.observe(containerRef.current);
    }

    // Monaco editor mouse target types: 2 = GUTTER_LINE_NUMBERS, 3 = GUTTER_GLYPH_MARGIN
    const MOUSE_TARGET_GUTTER_LINE_NUMBERS = 2;
    const MOUSE_TARGET_CONTENT_TEXT = 3;
    editor.onMouseDown((e: any) => {
      if (e.target.type === MOUSE_TARGET_GUTTER_LINE_NUMBERS || e.target.type === MOUSE_TARGET_CONTENT_TEXT) {
        const lineNumber = e.target.position.lineNumber;
        highlightCodeLine(lineNumber);
      }
    });

    setEditorReady(true);
  };

  const updateDecorations = () => {
    if (!editorRef.current || !monacoRef.current || !annotations) {
      return;
    }

    const editor = editorRef.current;
    const monaco = monacoRef.current;

    const decorations: any[] = [];

    // Skip all decorations if mode is 'none'
    if (assumptionDisplayMode === 'none') {
      const newDecorationIds = editor.deltaDecorations(
        decorationIdsRef.current,
        []
      );
      decorationIdsRef.current = newDecorationIds;
      return;
    }

    const decoratedLines = new Set<number>();

    annotations.forEach((annotation, line) => {
      // In 'selected' mode, only show lines linked to the selected constraint
      if (assumptionDisplayMode === 'selected') {
        if (!selectedConstraintId || !annotation.constraintIds.includes(selectedConstraintId)) {
          return;
        }
      }

      // Use the selected constraint for the tooltip in 'selected' mode, otherwise the first
      const constraintId =
        assumptionDisplayMode === 'selected' && selectedConstraintId
          ? selectedConstraintId
          : annotation.constraintIds[0];
      const constraint = constraints.find(c => c.id === constraintId);

      if (!constraint) return;

      decoratedLines.add(line);
      decorations.push({
        range: new monaco.Range(line, 1, line, 1),
        options: {
          isWholeLine: true,
          className: 'line-highlight-assumption',
          linesDecorationsClassName: 'line-decoration-assumption',
          hoverMessage: {
            value: `**Assumption**: ${constraint.assumption.text}`
          },
        },
      });
    });

    // Highlight selected assumption's source lines (only lines not already decorated above)
    if (selectedAssumptionId) {
      const assumption = assumptions.find((a) => a.id === selectedAssumptionId);
      if (assumption) {
        assumption.sourceCodeLines.forEach((line) => {
          if (decoratedLines.has(line)) return;
          decorations.push({
            range: new monaco.Range(line, 1, line, 1),
            options: {
              isWholeLine: true,
              className: 'line-highlight-assumption',
              linesDecorationsClassName: 'line-decoration-assumption',
              hoverMessage: {
                value: `**Assumption**: ${assumption.text}`,
              },
            },
          });
        });
      }
    }

    // Highlight data flow lines for the selected column (blue tint)
    if (selectedColumn && !selectedAssumptionId) {
      const columnLines = new Set<number>();
      for (const a of assumptions) {
        if (a.column === selectedColumn || a.columns.includes(selectedColumn)) {
          for (const line of a.sourceCodeLines) {
            columnLines.add(line);
          }
        }
      }
      columnLines.forEach((line) => {
        decorations.push({
          range: new monaco.Range(line, 1, line, 1),
          options: {
            isWholeLine: true,
            className: 'line-highlight-column',
            linesDecorationsClassName: 'line-decoration-column',
            hoverMessage: {
              value: `**Data flow**: column \`${selectedColumn}\``,
            },
          },
        });
      });
    }

    // Apply decorations - only replace our own tracked decorations
    const newDecorationIds = editor.deltaDecorations(
      decorationIdsRef.current,
      decorations
    );
    decorationIdsRef.current = newDecorationIds;
  };

  useEffect(() => {
    // Update decorations whenever data or mode changes, or when editor becomes ready
    // Guard in updateDecorations() handles case when editor isn't ready yet
    updateDecorations();
  }, [annotations, constraints, assumptions, assumptionDisplayMode, selectedConstraintId, selectedAssumptionId, selectedColumn, editorReady]);

  // Scroll to line when a constraint is selected
  useEffect(() => {
    if (!editorRef.current || !selectedConstraintId || !annotations) return;

    // Find the line number for the selected constraint
    let targetLine: number | null = null;
    annotations.forEach((annotation, lineNumber) => {
      if (annotation.constraintIds.includes(selectedConstraintId)) {
        targetLine = lineNumber;
      }
    });

    if (targetLine !== null) {
      // Always scroll when a constraint is selected (user explicitly selected it)
      // This works in all display modes: 'all', 'selected', 'none'
      editorRef.current.revealLineInCenter(targetLine);
    }
  }, [selectedConstraintId]);

  // Scroll to first source line when an assumption is selected
  useEffect(() => {
    if (!editorRef.current || !selectedAssumptionId) return;
    const assumption = assumptions.find((a) => a.id === selectedAssumptionId);
    if (assumption && assumption.sourceCodeLines.length > 0) {
      editorRef.current.revealLineInCenter(assumption.sourceCodeLines[0]);
    }
  }, [selectedAssumptionId]);

  // Scroll to line when "Go to reference" is clicked (without changing selection)
  useEffect(() => {
    if (!editorRef.current || highlightedLines.length === 0) return;
    editorRef.current.revealLineInCenter(highlightedLines[0]);
  }, [highlightedLines]);

  useEffect(() => {
    const monaco = monacoRef.current;
    if (!monaco) return;
    monaco.editor.setTheme(monacoThemeName);
  }, [monacoThemeName]);

  useEffect(() => {
    return () => {
      resizeObserverRef.current?.disconnect();
    };
  }, []);

  return (
    <div ref={containerRef} className="flex-1 w-full overflow-hidden relative min-w-0">
      <Editor
        height="100%"
        width="100%"
        language={taskFile?.language || 'python'}
        value={code}
        theme={monacoThemeName}
        onChange={(value) => { if (codeEditable) setCode(value ?? ''); }}
        options={{
          readOnly: !codeEditable,
          fontSize: editorFontSize,
          fontFamily: "'Fira Code', 'JetBrains Mono', monospace",
          lineNumbers: 'on',
          roundedSelection: false,
          scrollBeyondLastLine: false,
          wordWrap: editorWordWrap ? 'on' : 'off',
          minimap: { enabled: true },
          automaticLayout: true,
          glyphMargin: true,
          lineDecorationsWidth: 10,
          folding: true,
          fixedOverflowWidgets: true,
        }}
        onMount={handleEditorMount}
      />

      <style dangerouslySetInnerHTML={{ __html: `
        .line-highlight-assumption {
          background: rgba(245, 158, 66, 0.15) !important;
          position: relative;
        }
        .line-decoration-assumption {
          border-left: 3px solid #f59e42 !important;
        }
        .line-highlight-column {
          background: rgba(56, 189, 248, 0.12) !important;
          position: relative;
        }
        .line-decoration-column {
          border-left: 3px solid #38bdf8 !important;
        }
      `}} />
    </div>
  );
};

export default CodeEditor;
