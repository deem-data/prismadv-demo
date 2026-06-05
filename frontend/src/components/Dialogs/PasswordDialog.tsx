import { useState, useRef, useEffect } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { KeyRound } from 'lucide-react';

const DEMO_PASSWORD = '843940';
const SESSION_KEY = 'prismadv_demo_auth';

const REQUIRE_PASSWORD = import.meta.env.VITE_REQUIRE_PASSWORD === 'true';

export function isDemoAuthorized(useOwnKey: boolean): boolean {
  if (!REQUIRE_PASSWORD) return true;
  if (useOwnKey) return true;
  return sessionStorage.getItem(SESSION_KEY) === '1';
}

interface PasswordDialogProps {
  open: boolean;
  onSuccess: () => void;
  onUseOwnKey: (apiKey: string) => void;
  onClose: () => void;
}

export function PasswordDialog({ open, onSuccess, onUseOwnKey, onClose }: PasswordDialogProps) {
  const [password, setPassword] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [passwordError, setPasswordError] = useState(false);
  const [apiKeyError, setApiKeyError] = useState(false);
  const passwordRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setPassword('');
      setApiKey('');
      setPasswordError(false);
      setApiKeyError(false);
      setTimeout(() => passwordRef.current?.focus(), 50);
    }
  }, [open]);

  const submitPassword = () => {
    if (password === DEMO_PASSWORD) {
      sessionStorage.setItem(SESSION_KEY, '1');
      onSuccess();
    } else {
      setPasswordError(true);
      setPassword('');
      passwordRef.current?.focus();
    }
  };

  const submitApiKey = () => {
    const trimmed = apiKey.trim();
    if (!trimmed) {
      setApiKeyError(true);
      return;
    }
    onUseOwnKey(trimmed);
  };

  return (
    <Dialog.Root open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-dark-light border border-dark-border rounded-lg shadow-xl p-6 w-[400px] z-50">
          <div className="flex items-center gap-3 mb-1">
            <div className="p-2 rounded-md bg-accent-blue/10 text-accent-blue">
              <KeyRound size={18} />
            </div>
            <Dialog.Title className="text-base font-semibold text-text-primary">
              Access Required
            </Dialog.Title>
          </div>

          <Dialog.Description className="text-sm text-text-secondary mb-5">
            Enter the demo password to use the shared API key, or provide your own Anthropic API key.
          </Dialog.Description>

          {/* Demo password section */}
          <div className="mb-4">
            <label className="block text-xs font-medium text-text-secondary mb-1.5">Demo password</label>
            <input
              ref={passwordRef}
              type="password"
              value={password}
              onChange={(e) => { setPassword(e.target.value); setPasswordError(false); }}
              onKeyDown={(e) => { if (e.key === 'Enter') submitPassword(); }}
              placeholder="6-digit code"
              className={`w-full px-3 py-2 rounded-md bg-dark-base border text-sm text-text-primary placeholder:text-text-muted outline-none focus:ring-1 focus:ring-accent-blue transition-colors ${
                passwordError ? 'border-red-500 focus:ring-red-500' : 'border-dark-border'
              }`}
            />
            {passwordError && (
              <p className="text-xs text-red-400 mt-1">Incorrect password. Try again.</p>
            )}
            <button
              onClick={submitPassword}
              disabled={!password}
              className="mt-2 w-full px-4 py-2 rounded-md bg-accent-blue text-white text-sm font-medium hover:bg-accent-blue/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Continue with demo key
            </button>
          </div>

          {/* Divider */}
          <div className="flex items-center gap-3 my-4">
            <div className="flex-1 h-px bg-dark-border" />
            <span className="text-xs text-text-muted">or</span>
            <div className="flex-1 h-px bg-dark-border" />
          </div>

          {/* Own API key section */}
          <div className="mb-5">
            <label className="block text-xs font-medium text-text-secondary mb-1.5">Your Anthropic API key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => { setApiKey(e.target.value); setApiKeyError(false); }}
              onKeyDown={(e) => { if (e.key === 'Enter') submitApiKey(); }}
              placeholder="sk-ant-..."
              className={`w-full px-3 py-2 rounded-md bg-dark-base border text-sm text-text-primary placeholder:text-text-muted outline-none focus:ring-1 focus:ring-accent-blue transition-colors ${
                apiKeyError ? 'border-red-500 focus:ring-red-500' : 'border-dark-border'
              }`}
            />
            {apiKeyError && (
              <p className="text-xs text-red-400 mt-1">Please enter a valid API key.</p>
            )}
            <button
              onClick={submitApiKey}
              disabled={!apiKey.trim()}
              className="mt-2 w-full px-4 py-2 rounded-md border border-dark-border bg-dark-base text-text-primary text-sm font-medium hover:border-accent-blue/60 hover:text-accent-blue disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Continue with my key
            </button>
          </div>

          <button
            onClick={onClose}
            className="w-full px-4 py-1.5 text-xs text-text-muted hover:text-text-secondary transition-colors"
          >
            Cancel
          </button>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
