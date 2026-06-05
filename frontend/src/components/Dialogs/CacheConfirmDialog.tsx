import * as Dialog from '@radix-ui/react-dialog';
import { Database, RefreshCw } from 'lucide-react';

interface CacheConfirmDialogProps {
  open: boolean;
  title?: string;
  description?: string;
  useCacheLabel?: string;
  regenerateLabel?: string;
  onUseCache: () => void;
  onRegenerate: () => void;
  onClose: () => void;
}

export function CacheConfirmDialog({
  open,
  title = 'Cached Results Found',
  description = 'We found cached constraints for this dataset and code combination. Would you like to use the cached results or regenerate new constraints?',
  useCacheLabel = 'Use Cache',
  regenerateLabel = 'Regenerate',
  onUseCache,
  onRegenerate,
  onClose,
}: CacheConfirmDialogProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-dark-light border border-dark-border rounded-lg shadow-xl p-6 w-[400px] z-50">
          <Dialog.Title className="text-lg font-semibold text-text-primary mb-2">
            {title}
          </Dialog.Title>

          <Dialog.Description className="text-sm text-text-secondary mb-6">
            {description}
          </Dialog.Description>

          <div className="flex gap-3">
            <button
              onClick={onUseCache}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-md bg-accent-textual text-white font-medium hover:bg-accent-textual/90 transition-colors"
            >
              <Database size={16} />
              {useCacheLabel}
            </button>
            <button
              onClick={onRegenerate}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-md border border-dark-border bg-dark-base text-text-secondary hover:text-text-primary hover:border-text-secondary transition-colors"
            >
              <RefreshCw size={16} />
              {regenerateLabel}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
