import { StateCreator } from 'zustand';
import type { AppState, UIState, PanelType, ThemePreference } from '@/types';
import { LAYOUT_DEFAULTS } from '@/types';

const STORAGE_KEY = 'prismadv-ui-state';

const DEFAULT_UI_STATE: UIState = {
  leftSidebarCollapsed: false,
  rightSidebarCollapsed: false,
  bottomPanelCollapsed: false,
  dataTableCollapsed: false,
  columnStatsCollapsed: false,
  dataQualityCollapsed: false,
  constraintListCollapsed: false,
  flowGraphCollapsed: false,
  leftSidebarWidth: LAYOUT_DEFAULTS.LEFT_SIDEBAR_WIDTH,
  rightSidebarWidth: LAYOUT_DEFAULTS.RIGHT_SIDEBAR_WIDTH,
  bottomPanelHeight: LAYOUT_DEFAULTS.BOTTOM_PANEL_HEIGHT,
  themePreference: 'system',
};

// Load UI state from localStorage
const loadUIState = (): UIState => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      return { ...DEFAULT_UI_STATE, ...JSON.parse(saved) } as UIState;
    }
  } catch (error) {
    console.error('Failed to load UI state:', error);
  }

  return DEFAULT_UI_STATE;
};

// Save UI state to localStorage
const saveUIState = (state: UIState) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (error) {
    console.error('Failed to save UI state:', error);
  }
};

export interface UISlice {
  ui: UIState;
  togglePanel: (panel: PanelType) => void;
  setThemePreference: (themePreference: ThemePreference) => void;
}

export const createUISlice: StateCreator<
  AppState,
  [],
  [],
  UISlice
> = (set) => ({
  ui: loadUIState(),

  togglePanel: (panel: PanelType) => {
    set((state) => {
      const newUI = { ...state.ui };

      switch (panel) {
        case 'data':
          newUI.leftSidebarCollapsed = !newUI.leftSidebarCollapsed;
          break;
        case 'constraints':
          newUI.rightSidebarCollapsed = !newUI.rightSidebarCollapsed;
          break;
        case 'flow':
          newUI.bottomPanelCollapsed = !newUI.bottomPanelCollapsed;
          break;
      }

      saveUIState(newUI);
      return { ui: newUI };
    });
  },

  setThemePreference: (themePreference: ThemePreference) => {
    set((state) => {
      const newUI = { ...state.ui, themePreference };
      saveUIState(newUI);
      return { ui: newUI };
    });
  },
});
