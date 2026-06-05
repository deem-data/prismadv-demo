import { useState, useRef, useEffect } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { X, Check, ChevronDown } from 'lucide-react';
import { useAppStore } from '@/store';
import { DEFAULT_MODELS } from '@/store/slices/llmSlice';

function ModelSelect({
  value,
  options,
  onChange,
}: {
  value: string;
  options: string[];
  onChange: (v: string) => void;
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

  return (
    <div className="mb-6" ref={ref}>
      <label className="block text-sm font-medium text-text-secondary mb-2">Model</label>
      <div className="relative">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="w-full flex items-center justify-between px-3 py-2 bg-dark-darkest border border-dark-border rounded-md text-sm text-text-primary hover:border-text-muted focus:outline-none focus:border-blue-500 transition-colors"
        >
          <span className="font-mono">{value}</span>
          <ChevronDown size={14} className={`text-text-muted transition-transform ${open ? 'rotate-180' : ''}`} />
        </button>
        {open && (
          <ul className="absolute z-50 mt-1 w-full bg-dark-light border border-dark-border rounded-md shadow-lg py-1 max-h-48 overflow-y-auto">
            {options.map((model) => (
              <li key={model}>
                <button
                  type="button"
                  onClick={() => { onChange(model); setOpen(false); }}
                  className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left transition-colors ${
                    model === value
                      ? 'bg-blue-500/15 text-blue-400'
                      : 'text-text-primary hover:bg-dark-border/50'
                  }`}
                >
                  <span className={`w-4 flex-shrink-0 ${model === value ? '' : 'opacity-0'}`}>
                    <Check size={13} />
                  </span>
                  <span className="font-mono">{model}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

interface LLMSettingsDialogProps {
  open: boolean;
  onClose: () => void;
}

export function LLMSettingsDialog({ open, onClose }: LLMSettingsDialogProps) {
  const { llmSettings, setLLMProvider, setLLMModel, setUseOwnKey, setAPIKey } = useAppStore();

  const handleProviderChange = (provider: 'openai' | 'anthropic' | 'gemini') => {
    setLLMProvider(provider);
  };

  return (
    <Dialog.Root open={open} onOpenChange={onClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-dark-light border border-dark-border rounded-lg shadow-xl p-6 w-[500px] max-h-[80vh] overflow-y-auto z-50">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <Dialog.Title className="text-xl font-semibold text-text-primary">
              LLM Settings
            </Dialog.Title>
            <Dialog.Close asChild>
              <button
                className="text-text-secondary hover:text-text-primary transition-colors"
                aria-label="Close"
              >
                <X size={20} />
              </button>
            </Dialog.Close>
          </div>

          {/* Provider Selection */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-text-secondary mb-3">
              Provider
            </label>
            <div className="grid grid-cols-3 gap-3">
              {(['openai', 'anthropic', 'gemini'] as const).map((provider) => (
                <button
                  key={provider}
                  onClick={() => handleProviderChange(provider)}
                  className={`px-4 py-3 rounded-md border transition-colors ${
                    llmSettings.provider === provider
                      ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                      : 'border-dark-border bg-dark-base text-text-secondary hover:border-text-secondary'
                  }`}
                >
                  <div className="flex items-center justify-center gap-2">
                    {llmSettings.provider === provider && <Check size={16} />}
                    <span className="capitalize">{provider}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Model Selection */}
          <ModelSelect
            value={llmSettings.model}
            options={DEFAULT_MODELS[llmSettings.provider]}
            onChange={setLLMModel}
          />

          {/* API Key Section */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-text-secondary mb-3">
              API Key
            </label>

            {/* Use key from .env file */}
            <div className="mb-4">
              <label className="flex items-center gap-2 p-3 border border-dark-border rounded-md cursor-pointer hover:bg-dark-border/50 transition-colors">
                <input
                  type="radio"
                  name="keyOption"
                  checked={!llmSettings.useOwnKey}
                  onChange={() => setUseOwnKey(false)}
                  className="w-4 h-4"
                />
                <div>
                  <div className="text-sm text-text-primary">Use API key from .env file</div>
                  <div className="text-xs text-text-secondary">Configure your key in the backend .env file</div>
                </div>
              </label>
            </div>

            <label className="flex items-start gap-2 p-3 border border-dark-border rounded-md cursor-pointer hover:bg-dark-border/50 transition-colors">
              <input
                type="radio"
                name="keyOption"
                checked={llmSettings.useOwnKey}
                onChange={() => setUseOwnKey(true)}
                className="w-4 h-4 mt-0.5"
              />
              <div className="flex-1">
                <div className="text-sm text-text-primary mb-2">Use my own API key</div>
                {llmSettings.useOwnKey && (
                  <input
                    type="password"
                    value={llmSettings.apiKey}
                    onChange={(e) => setAPIKey(e.target.value)}
                    placeholder={`Enter your ${llmSettings.provider} API key`}
                    className="w-full px-3 py-2 bg-dark-base border border-dark-border rounded-md text-text-primary text-sm focus:outline-none focus:border-blue-500"
                  />
                )}
              </div>
            </label>
          </div>

          {/* Info */}
          <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-md">
            <div className="text-xs text-blue-400">
              {!llmSettings.useOwnKey ? (
                <>Using API key from the backend .env file.</>
              ) : (
                <>
                  Get your API key from:{' '}
                  {llmSettings.provider === 'openai' && (
                    <a
                      href="https://platform.openai.com/api-keys"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline hover:text-blue-300"
                    >
                      OpenAI Platform
                    </a>
                  )}
                  {llmSettings.provider === 'anthropic' && (
                    <a
                      href="https://console.anthropic.com/settings/keys"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline hover:text-blue-300"
                    >
                      Anthropic Console
                    </a>
                  )}
                  {llmSettings.provider === 'gemini' && (
                    <a
                      href="https://aistudio.google.com/app/apikey"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline hover:text-blue-300"
                    >
                      Google AI Studio
                    </a>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="mt-6 flex justify-end gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-text-secondary hover:text-text-primary transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded-md transition-colors"
            >
              Save Settings
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
