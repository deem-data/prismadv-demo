import { Settings } from 'lucide-react';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { useAppStore } from '@/store';
import type { AssumptionDisplayMode } from '@/store/slices/codeEditorSlice';

export function EditorSettings() {
  const assumptionDisplayMode = useAppStore((state) => state.assumptionDisplayMode);
  const setAssumptionDisplayMode = useAppStore((state) => state.setAssumptionDisplayMode);

  const modes: { value: AssumptionDisplayMode; label: string; description: string }[] = [
    {
      value: 'all',
      label: 'Show All',
      description: 'Display all assumptions in code'
    },
    {
      value: 'selected',
      label: 'Show Selected',
      description: 'Only show selected assumption'
    },
    {
      value: 'none',
      label: 'Hide All',
      description: 'Hide all assumption markers'
    },
  ];

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button
          className="flex items-center gap-1.5 px-2 py-1 text-xs text-text-secondary hover:text-text-primary hover:bg-dark-medium rounded transition-colors"
          title="Editor Settings"
        >
          <Settings className="w-4 h-4" />
          <span>View</span>
        </button>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          className="min-w-[220px] bg-dark-medium border border-dark-border rounded shadow-lg py-1 z-50"
          sideOffset={5}
          align="end"
        >
          <div className="px-2 py-1.5 text-xs font-semibold text-text-muted">
            Assumption Display
          </div>

          <DropdownMenu.RadioGroup
            value={assumptionDisplayMode}
            onValueChange={(value) => setAssumptionDisplayMode(value as AssumptionDisplayMode)}
          >
            {modes.map((mode) => (
              <DropdownMenu.RadioItem
                key={mode.value}
                value={mode.value}
                className="relative flex items-start gap-2 px-3 py-2 text-sm text-text-secondary hover:text-text-primary hover:bg-dark-light cursor-pointer outline-none"
              >
                <div className="flex items-center justify-center w-4 h-4 mt-0.5">
                  <DropdownMenu.ItemIndicator>
                    <div className="w-2 h-2 bg-accent-blue rounded-full" />
                  </DropdownMenu.ItemIndicator>
                </div>
                <div className="flex-1">
                  <div className="font-medium">{mode.label}</div>
                  <div className="text-xs text-text-muted">{mode.description}</div>
                </div>
              </DropdownMenu.RadioItem>
            ))}
          </DropdownMenu.RadioGroup>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
