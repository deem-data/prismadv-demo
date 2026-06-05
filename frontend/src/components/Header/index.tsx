import { MenuBar } from './MenuBar';
import { InferenceButton } from './InferenceButton';
import { ExportButton } from './ExportButton';
import { LogoSection } from './LogoSection';
import { CostIndicator } from './CostIndicator';
import { PanelToggles } from './PanelToggles';
import { PromptsPanel } from '@/components/Dialogs/PromptsPanel';
import { useAppStore } from '@/store';
import * as Tooltip from '@radix-ui/react-tooltip';
import { Wand2 } from 'lucide-react';

export function Header() {
  const { ui, togglePanel, constraints, totalCost, showPromptsPanel, setShowPromptsPanel } = useAppStore();

  const panelVisibility = {
    data: !ui.leftSidebarCollapsed,
    constraints: !ui.rightSidebarCollapsed,
    flow: !ui.bottomPanelCollapsed,
  };

  return (
    <header className="h-11 bg-dark-light border-b border-dark-border flex items-center justify-between px-4">
      {/* Left Section: Menus */}
      <div className="flex items-center gap-2">
        <MenuBar />
        <InferenceButton />
        <ExportButton constraints={constraints} />
      </div>

      {/* Center Section: Logo */}
      <LogoSection />

      {/* Right Section: Prompts + Cost + Panel Toggles */}
      <div className="flex items-center gap-4">
        <Tooltip.Provider delayDuration={300}>
          <Tooltip.Root>
            <Tooltip.Trigger
              onClick={() => setShowPromptsPanel(true)}
              className="flex items-center gap-1.5 px-2.5 py-1 bg-dark-darkest rounded text-xs text-text-muted hover:text-text-secondary hover:bg-dark-border transition-colors cursor-pointer"
            >
              <Wand2 className="w-3.5 h-3.5" />
              <span>Prompts</span>
            </Tooltip.Trigger>
            <Tooltip.Portal>
              <Tooltip.Content
                className="bg-dark-medium border border-dark-border rounded px-3 py-2 text-xs text-text-secondary shadow-lg z-50"
                sideOffset={5}
              >
                View generation prompts
                <Tooltip.Arrow className="fill-dark-medium" />
              </Tooltip.Content>
            </Tooltip.Portal>
          </Tooltip.Root>
        </Tooltip.Provider>
        <CostIndicator cost={totalCost} />
        <PanelToggles
          visibility={panelVisibility}
          onToggle={togglePanel}
        />
      </div>

      <PromptsPanel open={showPromptsPanel} onClose={() => setShowPromptsPanel(false)} />
    </header>
  );
}

export default Header;
