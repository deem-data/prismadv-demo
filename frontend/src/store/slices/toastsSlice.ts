import { StateCreator } from 'zustand';
import type { AppState, Toast } from '@/types';

let toastId = 0;

export interface ToastsSlice {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
}

export const createToastsSlice: StateCreator<
  AppState,
  [],
  [],
  ToastsSlice
> = (set, get) => ({
  toasts: [],

  addToast: (toast: Omit<Toast, 'id'>) => {
    const id = `toast-${toastId++}`;
    const newToast: Toast = {
      id,
      ...toast,
      duration: toast.duration || 5000,
    };

    set((state) => ({
      toasts: [...state.toasts, newToast],
    }));

    // Auto-remove toast after duration
    const duration = newToast.duration;
    if (duration && duration > 0) {
      setTimeout(() => {
        get().removeToast(id);
      }, duration);
    }
  },

  removeToast: (id: string) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }));
  },
});
