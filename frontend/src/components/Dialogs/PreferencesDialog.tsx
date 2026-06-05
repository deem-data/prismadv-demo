import * as Dialog from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { useAppStore } from '@/store';

interface PreferencesDialogProps {
  open: boolean;
  onClose: () => void;
}

function SectionHeader({ title }: { title: string }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">{title}</span>
      <div className="flex-1 h-px bg-dark-border" />
    </div>
  );
}

function Row({ label, description, children }: { label: string; description?: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 mb-5">
      <div className="flex-1 min-w-0">
        <div className="text-sm text-text-primary">{label}</div>
        {description && <div className="text-xs text-text-muted mt-0.5">{description}</div>}
      </div>
      <div className="flex-shrink-0">{children}</div>
    </div>
  );
}

function Stepper({
  value,
  min,
  max,
  step = 1,
  onChange,
}: {
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex items-center gap-1">
      <button
        onClick={() => onChange(Math.max(min, value - step))}
        disabled={value <= min}
        className="w-7 h-7 flex items-center justify-center rounded bg-dark-base border border-dark-border text-text-secondary hover:text-text-primary hover:border-text-secondary disabled:opacity-40 disabled:cursor-not-allowed transition-colors text-base leading-none"
      >
        −
      </button>
      <span className="w-10 text-center text-sm font-mono text-text-primary">{value}</span>
      <button
        onClick={() => onChange(Math.min(max, value + step))}
        disabled={value >= max}
        className="w-7 h-7 flex items-center justify-center rounded bg-dark-base border border-dark-border text-text-secondary hover:text-text-primary hover:border-text-secondary disabled:opacity-40 disabled:cursor-not-allowed transition-colors text-base leading-none"
      >
        +
      </button>
    </div>
  );
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${
        checked ? 'bg-accent-blue' : 'bg-dark-border'
      }`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform ${
          checked ? 'translate-x-4' : 'translate-x-1'
        }`}
      />
    </button>
  );
}

export function PreferencesDialog({ open, onClose }: PreferencesDialogProps) {
  const { preferences, setPreferences } = useAppStore();

  return (
    <Dialog.Root open={open} onOpenChange={onClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-dark-light border border-dark-border rounded-lg shadow-xl p-6 w-[480px] max-h-[80vh] overflow-y-auto z-50">

          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <Dialog.Title className="text-base font-semibold text-text-primary">
              Preferences
            </Dialog.Title>
            <Dialog.Close asChild>
              <button className="text-text-muted hover:text-text-secondary transition-colors">
                <X size={16} />
              </button>
            </Dialog.Close>
          </div>

          {/* Generation */}
          <SectionHeader title="Generation" />

          <Row
            label="Max parallel LLM calls"
            description="Higher values are faster but may hit rate limits."
          >
            <Stepper
              value={preferences.maxParallelCalls}
              min={1}
              max={20}
              onChange={(v) => setPreferences({ maxParallelCalls: v })}
            />
          </Row>

          {/* Column Detection */}
          <SectionHeader title="Column Detection" />

          <Row
            label="Auto-select detected columns"
            description="Skip the selection dialog and use the model's detected columns directly."
          >
            <Toggle
              checked={preferences.autoSelectDetectedColumns}
              onChange={(v) => setPreferences({ autoSelectDetectedColumns: v })}
            />
          </Row>

          {/* Editor */}
          <SectionHeader title="Editor" />

          <Row label="Font size">
            <Stepper
              value={preferences.editorFontSize}
              min={10}
              max={24}
              onChange={(v) => setPreferences({ editorFontSize: v })}
            />
          </Row>

          <Row
            label="Word wrap"
            description="Wrap long lines instead of scrolling horizontally."
          >
            <Toggle
              checked={preferences.editorWordWrap}
              onChange={(v) => setPreferences({ editorWordWrap: v })}
            />
          </Row>

          {/* Footer */}
          <div className="mt-6 flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm bg-accent-blue hover:bg-accent-blue/90 text-white rounded-md transition-colors"
            >
              Done
            </button>
          </div>

        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
