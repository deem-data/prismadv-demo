import { useState } from 'react';
import { DollarSign } from 'lucide-react';
import * as Tooltip from '@radix-ui/react-tooltip';
import { CostDialog } from '@/components/Dialogs/CostDialog';

interface CostIndicatorProps {
  cost: number;
}

export function CostIndicator({ cost }: CostIndicatorProps) {
  const [open, setOpen] = useState(false);

  const formattedCost = cost.toFixed(4);

  return (
    <>
      <Tooltip.Provider delayDuration={300}>
        <Tooltip.Root>
          <Tooltip.Trigger
            onClick={() => setOpen(true)}
            className="flex items-center gap-1.5 px-2.5 py-1 bg-dark-darkest rounded text-xs text-text-muted hover:text-text-secondary hover:bg-dark-border transition-colors cursor-pointer"
          >
            <DollarSign className="w-3.5 h-3.5" />
            <span className="font-mono">{formattedCost}</span>
          </Tooltip.Trigger>
          <Tooltip.Portal>
            <Tooltip.Content
              className="bg-dark-medium border border-dark-border rounded px-3 py-2 text-xs text-text-secondary shadow-lg z-50"
              sideOffset={5}
            >
              Click to see cost breakdown
              <Tooltip.Arrow className="fill-dark-medium" />
            </Tooltip.Content>
          </Tooltip.Portal>
        </Tooltip.Root>
      </Tooltip.Provider>
      <CostDialog open={open} onClose={() => setOpen(false)} />
    </>
  );
}
