import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import * as Dialog from '@radix-ui/react-dialog';
import { Upload, Settings, Palette, Monitor, Sun, Moon, Check, FlaskConical, RotateCcw, Zap } from 'lucide-react';

import { useAppStore } from '@/store';
import { useState } from 'react';
import { LLMSettingsDialog } from '@/components/Dialogs/LLMSettingsDialog';
import { EIDBenchDialog } from '@/components/Dialogs/EIDBenchDialog';
import { UploadDialog } from '@/components/Dialogs/UploadDialog';
import { PreferencesDialog } from '@/components/Dialogs/PreferencesDialog';

export function MenuBar() {
  const { reset, ui, setThemePreference, loadQuickExample } = useAppStore();
  const [showLLMSettings, setShowLLMSettings] = useState(false);
  const [showEIDBench, setShowEIDBench] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [showNewSessionConfirm, setShowNewSessionConfirm] = useState(false);
  const [showPreferences, setShowPreferences] = useState(false);

  return (
    <div className="flex items-center gap-1">
      {/* File Menu */}
      <DropdownMenu.Root>
        <DropdownMenu.Trigger asChild>
          <button className="px-3 py-1.5 text-sm text-text-secondary hover:bg-dark-border rounded transition-colors">
            File
          </button>
        </DropdownMenu.Trigger>

        <DropdownMenu.Portal>
          <DropdownMenu.Content
            className="min-w-[200px] bg-dark-light border border-dark-border rounded-md shadow-lg p-1 z-50"
            sideOffset={5}
          >
            <DropdownMenu.Item
              className="flex items-center gap-2 px-3 py-2 text-sm text-amber-400 hover:bg-amber-900/20 hover:text-amber-300 rounded cursor-pointer outline-none"
              onSelect={() => loadQuickExample()}
            >
              <Zap size={16} />
              <span>Quick Example</span>
              <span className="ml-auto text-[10px] opacity-60">HR Analytics</span>
            </DropdownMenu.Item>

            <DropdownMenu.Separator className="h-px bg-dark-border my-1" />

            <DropdownMenu.Item
              className="flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-dark-border hover:text-text-primary rounded cursor-pointer outline-none"
              onSelect={() => setTimeout(() => setShowEIDBench(true), 100)}
            >
              <FlaskConical size={16} />
              <span>Load from Benchmark</span>
            </DropdownMenu.Item>

            <DropdownMenu.Item
              className="flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-dark-border hover:text-text-primary rounded cursor-pointer outline-none"
              onSelect={() => setTimeout(() => setShowUpload(true), 100)}
            >
              <Upload size={16} />
              <span>Upload your own</span>
            </DropdownMenu.Item>

            <DropdownMenu.Separator className="h-px bg-dark-border my-1" />

            <DropdownMenu.Item
              className="flex items-center gap-2 px-3 py-2 text-sm text-red-400 hover:bg-red-900/30 hover:text-red-300 rounded cursor-pointer outline-none"
              onSelect={() => setTimeout(() => setShowNewSessionConfirm(true), 100)}
            >
              <RotateCcw size={16} />
              <span>New session</span>
            </DropdownMenu.Item>

          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>

      {/* Settings Menu */}
      <DropdownMenu.Root>
        <DropdownMenu.Trigger asChild>
          <button className="px-3 py-1.5 text-sm text-text-secondary hover:bg-dark-border rounded transition-colors">
            Settings
          </button>
        </DropdownMenu.Trigger>

        <DropdownMenu.Portal>
          <DropdownMenu.Content
            className="min-w-[200px] bg-dark-light border border-dark-border rounded-md shadow-lg p-1 z-50"
            sideOffset={5}
          >
            <DropdownMenu.Item
              className="flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-dark-border hover:text-text-primary rounded cursor-pointer outline-none"
              onSelect={() => setTimeout(() => setShowPreferences(true), 100)}
            >
              <Settings size={16} />
              <span>Preferences</span>
            </DropdownMenu.Item>

            <DropdownMenu.Sub>
              <DropdownMenu.SubTrigger className="flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-dark-border hover:text-text-primary rounded cursor-pointer outline-none">
                <Palette size={16} />
                <span>Theme</span>
                <span className="ml-auto text-xs opacity-70">
                  {ui.themePreference === 'system'
                    ? 'System'
                    : ui.themePreference.charAt(0).toUpperCase() + ui.themePreference.slice(1)}
                </span>
              </DropdownMenu.SubTrigger>

              <DropdownMenu.Portal>
                <DropdownMenu.SubContent
                  className="min-w-[180px] bg-dark-light border border-dark-border rounded-md shadow-lg p-1 z-50"
                  sideOffset={6}
                  alignOffset={-5}
                >
                  <DropdownMenu.Item
                    className="flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-dark-border hover:text-text-primary rounded cursor-pointer outline-none"
                    onSelect={() => setThemePreference('system')}
                  >
                    <Monitor size={16} />
                    <span>System</span>
                    {ui.themePreference === 'system' && (
                      <Check size={14} className="ml-auto opacity-80" />
                    )}
                  </DropdownMenu.Item>

                  <DropdownMenu.Item
                    className="flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-dark-border hover:text-text-primary rounded cursor-pointer outline-none"
                    onSelect={() => setThemePreference('light')}
                  >
                    <Sun size={16} />
                    <span>Light</span>
                    {ui.themePreference === 'light' && (
                      <Check size={14} className="ml-auto opacity-80" />
                    )}
                  </DropdownMenu.Item>

                  <DropdownMenu.Item
                    className="flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-dark-border hover:text-text-primary rounded cursor-pointer outline-none"
                    onSelect={() => setThemePreference('dark')}
                  >
                    <Moon size={16} />
                    <span>Dark</span>
                    {ui.themePreference === 'dark' && (
                      <Check size={14} className="ml-auto opacity-80" />
                    )}
                  </DropdownMenu.Item>
                </DropdownMenu.SubContent>
              </DropdownMenu.Portal>
            </DropdownMenu.Sub>

          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>

      {/* LLM Menu */}
      <button
        onClick={() => setShowLLMSettings(true)}
        className="px-3 py-1.5 text-sm text-text-secondary hover:bg-dark-border rounded transition-colors"
      >
        LLM
      </button>

      {/* LLM Settings Dialog */}
      <PreferencesDialog open={showPreferences} onClose={() => setShowPreferences(false)} />
      <LLMSettingsDialog open={showLLMSettings} onClose={() => setShowLLMSettings(false)} />
      <EIDBenchDialog open={showEIDBench} onClose={() => setShowEIDBench(false)} />
      <UploadDialog open={showUpload} onClose={() => setShowUpload(false)} />

      {/* New Session Confirmation */}
      <Dialog.Root open={showNewSessionConfirm} onOpenChange={setShowNewSessionConfirm}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50" />
          <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-dark-light border border-dark-border rounded-lg shadow-xl p-6 w-[360px] z-50">
            <Dialog.Title className="text-base font-semibold text-text-primary mb-2">
              Start a new session?
            </Dialog.Title>
            <Dialog.Description className="text-sm text-text-secondary mb-6">
              This will clear all uploaded files, constraints, and results. This action cannot be undone.
            </Dialog.Description>
            <div className="flex gap-3">
              <button
                onClick={() => setShowNewSessionConfirm(false)}
                className="flex-1 px-4 py-2 rounded-md border border-dark-border bg-dark-base text-text-secondary hover:text-text-primary hover:border-text-secondary transition-colors text-sm font-medium"
              >
                Cancel
              </button>
              <button
                onClick={() => { setShowNewSessionConfirm(false); reset(); }}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-red-700 hover:bg-red-600 text-white text-sm font-medium transition-colors"
              >
                <RotateCcw size={14} />
                New session
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
