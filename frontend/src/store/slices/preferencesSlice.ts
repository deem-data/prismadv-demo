import { StateCreator } from 'zustand';
import type { AppState } from '@/types';

export interface Preferences {
  // Generation
  maxParallelCalls: number;
  // Column detection
  autoSelectDetectedColumns: boolean;
  // Editor
  editorFontSize: number;
  editorWordWrap: boolean;
}

export interface PreferencesSlice {
  preferences: Preferences;
  setPreferences: (patch: Partial<Preferences>) => void;
}

export const DEFAULT_PREFERENCES: Preferences = {
  maxParallelCalls: 10,
  autoSelectDetectedColumns: false,
  editorFontSize: 14,
  editorWordWrap: false,
};

export const createPreferencesSlice: StateCreator<AppState, [], [], PreferencesSlice> = (set, get) => ({
  preferences: { ...DEFAULT_PREFERENCES },

  setPreferences: (patch) => {
    set({ preferences: { ...get().preferences, ...patch } });
  },
});
