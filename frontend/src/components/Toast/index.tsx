import { useAppStore } from '@/store';
import { X, CheckCircle2, AlertCircle, Info, AlertTriangle } from 'lucide-react';

export function ToastContainer() {
  const { toasts, removeToast } = useAppStore();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className="pointer-events-auto bg-dark-light border border-dark-border rounded-lg shadow-lg p-4 min-w-[300px] max-w-[400px] animate-in slide-in-from-top-2 duration-300"
        >
          <div className="flex items-start gap-3">
            {/* Icon */}
            <div className="flex-shrink-0 mt-0.5">
              {toast.type === 'success' && (
                <CheckCircle2 size={20} className="text-accent-green" />
              )}
              {toast.type === 'error' && (
                <AlertCircle size={20} className="text-red-500" />
              )}
              {toast.type === 'warning' && (
                <AlertTriangle size={20} className="text-accent-orange" />
              )}
              {toast.type === 'info' && (
                <Info size={20} className="text-accent-blue" />
              )}
            </div>

            {/* Message */}
            <div className="flex-1 text-sm text-text-primary">
              {toast.message}
            </div>

            {/* Close Button */}
            <button
              onClick={() => removeToast(toast.id)}
              className="flex-shrink-0 text-text-muted hover:text-text-primary transition-colors"
            >
              <X size={16} />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

export default ToastContainer;
