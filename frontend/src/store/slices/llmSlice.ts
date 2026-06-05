import { StateCreator } from 'zustand';
import type { AppState } from '@/types';

export type LLMProvider = 'openai' | 'anthropic' | 'gemini';

export interface LLMSettings {
  provider: LLMProvider;
  model: string;
  useOwnKey: boolean;
  apiKey: string;
}

export interface LLMSlice {
  llmSettings: LLMSettings;
  setLLMProvider: (provider: LLMProvider) => void;
  setLLMModel: (model: string) => void;
  setUseOwnKey: (useOwnKey: boolean) => void;
  setAPIKey: (apiKey: string) => void;
}

// Default models for each provider
export const DEFAULT_MODELS: Record<LLMProvider, string[]> = {
  openai: ['gpt-5.4', 'gpt-5.4-mini', 'gpt-5.4-nano'],
  anthropic: ['claude-sonnet-4-5', 'claude-opus-4-5'],
  gemini: ['gemini-2.5-flash-lite', 'gemini-2.5-flash', 'gemini-2.5-pro'],
};

export const createLLMSlice: StateCreator<AppState, [], [], LLMSlice> = (
  set,
  get
) => ({
  llmSettings: {
    provider: 'gemini',
    model: 'gemini-2.5-flash',
    useOwnKey: false,
    apiKey: '',
  },

  setLLMProvider: (provider: LLMProvider) => {
    // When changing provider, set default model for that provider
    const defaultModel = DEFAULT_MODELS[provider][0];
    set({
      llmSettings: {
        ...get().llmSettings,
        provider,
        model: defaultModel,
      },
    });
  },

  setLLMModel: (model: string) => {
    set({
      llmSettings: {
        ...get().llmSettings,
        model,
      },
    });
  },

  setUseOwnKey: (useOwnKey: boolean) => {
    set({
      llmSettings: {
        ...get().llmSettings,
        useOwnKey,
      },
    });
  },

  setAPIKey: (apiKey: string) => {
    set({
      llmSettings: {
        ...get().llmSettings,
        apiKey,
      },
    });
  },
});
