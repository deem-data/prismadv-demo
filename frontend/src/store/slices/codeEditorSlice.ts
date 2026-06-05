import { StateCreator } from 'zustand';
import type { AppState, CodeAnnotation } from '@/types';

export type AssumptionDisplayMode = 'all' | 'selected' | 'none';

export interface CodeEditorSlice {
  code: string;
  codeEditable: boolean;
  constraintsSynced: boolean | null;
  highlightedLines: number[];
  annotations: Map<number, CodeAnnotation>;
  rawAnnotations: CodeAnnotation[];
  assumptionDisplayMode: AssumptionDisplayMode;
  setAssumptionDisplayMode: (mode: AssumptionDisplayMode) => void;
  setCodeEditable: (editable: boolean) => void;
  setCode: (code: string) => void;
  setConstraintsSynced: (synced: boolean | null) => void;
  highlightCodeLine: (lineNumber: number) => void;
  scrollToLine: (lineNumber: number) => void;
}

export const createCodeEditorSlice: StateCreator<
  AppState,
  [],
  [],
  CodeEditorSlice
> = (_set, get) => ({
  code: '',
  codeEditable: false,
  constraintsSynced: null,
  highlightedLines: [],
  annotations: new Map(),
  rawAnnotations: [],
  assumptionDisplayMode: 'selected',

  setAssumptionDisplayMode: (mode: AssumptionDisplayMode) => {
    _set({ assumptionDisplayMode: mode });
  },

  setCodeEditable: (editable: boolean) => {
    _set({ codeEditable: editable });
  },

  setCode: (code: string) => {
    const hasConstraints = get().constraints.length > 0;
    const codeChanged = code !== get().code;
    _set({
      code,
      ...(hasConstraints && codeChanged ? { constraintsSynced: false } : {}),
    });
  },

  setConstraintsSynced: (synced: boolean | null) => {
    _set({ constraintsSynced: synced });
  },

  scrollToLine: (lineNumber: number) => {
    // Just signal the editor to scroll — don't change selected constraint
    _set({ highlightedLines: [lineNumber] });
  },

  highlightCodeLine: (lineNumber: number) => {
    const annotation = get().annotations.get(lineNumber);

    if (annotation) {
      const constraintId = annotation.constraintIds[0];
      if (constraintId) {
        const currentMode = get().assumptionDisplayMode;

        // Ensure mode is suitable for showing decorations
        // Switch to 'selected' if currently 'none', otherwise keep current mode
        if (currentMode === 'none') {
          // Update both mode and selection together to ensure proper decoration update
          _set({
            assumptionDisplayMode: 'selected',
            selectedConstraintId: constraintId
          });
        } else {
          // Just select the constraint in current mode
          get().selectConstraint(constraintId);
        }
      }
    }
  },
});
