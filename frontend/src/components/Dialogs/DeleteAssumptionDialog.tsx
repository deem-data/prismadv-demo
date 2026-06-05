import * as Dialog from '@radix-ui/react-dialog';
import { AlertTriangle } from 'lucide-react';
import type { AssumptionItem, Constraint } from '@/types';

interface DeleteAssumptionDialogProps {
  open: boolean;
  assumption: AssumptionItem;
  linkedConstraints: Constraint[];
  onDeleteAssumptionOnly: () => void;
  onDeleteWithConstraints: () => void;
  onClose: () => void;
}

export function DeleteAssumptionDialog({
  open,
  assumption,
  linkedConstraints,
  onDeleteAssumptionOnly,
  onDeleteWithConstraints,
  onClose,
}: DeleteAssumptionDialogProps) {
  return (
    <Dialog.Root open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-dark-light border border-dark-border rounded-lg shadow-xl p-5 w-[400px] z-50">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 rounded-md bg-red-500/10 text-red-400">
              <AlertTriangle size={18} />
            </div>
            <Dialog.Title className="text-sm font-semibold text-text-primary">
              Delete Assumption
            </Dialog.Title>
          </div>

          <Dialog.Description className="text-xs text-text-secondary mb-4 leading-relaxed">
            <span className="font-medium text-text-primary">"{assumption.text.length > 80 ? assumption.text.slice(0, 80) + '...' : assumption.text}"</span>
          </Dialog.Description>

          {linkedConstraints.length > 0 ? (
            <>
              <p className="text-xs text-text-secondary mb-2">
                This assumption has <span className="text-text-primary font-medium">{linkedConstraints.length}</span> derived constraint{linkedConstraints.length > 1 ? 's' : ''}:
              </p>
              <ul className="mb-4 space-y-1 max-h-32 overflow-y-auto">
                {linkedConstraints.map((c) => (
                  <li key={c.id} className="text-[11px] text-text-muted px-2 py-1 bg-dark-darkest rounded truncate">
                    {c.label}
                  </li>
                ))}
              </ul>
              <div className="flex flex-col gap-2">
                <button
                  onClick={onDeleteWithConstraints}
                  className="w-full px-3 py-2 rounded-md bg-red-500/20 border border-red-500/30 text-red-400 text-xs font-medium hover:bg-red-500/30 transition-colors"
                >
                  Delete assumption + {linkedConstraints.length} constraint{linkedConstraints.length > 1 ? 's' : ''}
                </button>
                <button
                  onClick={onDeleteAssumptionOnly}
                  className="w-full px-3 py-2 rounded-md border border-dark-border text-text-secondary text-xs hover:text-text-primary hover:border-text-secondary transition-colors"
                >
                  Delete assumption only
                </button>
                <button
                  onClick={onClose}
                  className="w-full px-3 py-1.5 text-xs text-text-muted hover:text-text-secondary transition-colors"
                >
                  Cancel
                </button>
              </div>
            </>
          ) : (
            <div className="flex gap-2 mt-4">
              <button
                onClick={onDeleteAssumptionOnly}
                className="flex-1 px-3 py-2 rounded-md bg-red-500/20 border border-red-500/30 text-red-400 text-xs font-medium hover:bg-red-500/30 transition-colors"
              >
                Delete
              </button>
              <button
                onClick={onClose}
                className="flex-1 px-3 py-2 rounded-md border border-dark-border text-text-secondary text-xs hover:text-text-primary transition-colors"
              >
                Cancel
              </button>
            </div>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
