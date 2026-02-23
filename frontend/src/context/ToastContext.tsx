/**
 * ToastContext — global notification toast system.
 *
 * Usage:
 *   const { success, error } = useToast();
 *   success('Record saved');
 *   error('Something went wrong');
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

/* ── Types ───────────────────────────────────────────────────────── */

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  duration?: number;
}

interface ToastContextValue {
  toasts: ToastMessage[];
  toast: (opts: Omit<ToastMessage, 'id'>) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  warning: (message: string) => void;
  info: (message: string) => void;
  dismiss: (id: string) => void;
  dismissAll: () => void;
}

/* ── Context ─────────────────────────────────────────────────────── */

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

let toastCounter = 0;

/* ── Provider ────────────────────────────────────────────────────── */

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const dismissAll = useCallback(() => {
    setToasts([]);
  }, []);

  const addToast = useCallback((opts: Omit<ToastMessage, 'id'>) => {
    const id = `toast-${++toastCounter}`;
    setToasts((prev) => [...prev, { ...opts, id }]);
  }, []);

  const toast = useCallback(
    (opts: Omit<ToastMessage, 'id'>) => addToast(opts),
    [addToast],
  );

  const success = useCallback(
    (message: string) => addToast({ type: 'success', message }),
    [addToast],
  );
  const error = useCallback(
    (message: string) => addToast({ type: 'error', message }),
    [addToast],
  );
  const warning = useCallback(
    (message: string) => addToast({ type: 'warning', message }),
    [addToast],
  );
  const info = useCallback(
    (message: string) => addToast({ type: 'info', message }),
    [addToast],
  );

  const value = useMemo<ToastContextValue>(
    () => ({ toasts, toast, success, error, warning, info, dismiss, dismissAll }),
    [toasts, toast, success, error, warning, info, dismiss, dismissAll],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

/* ── Hook ─────────────────────────────────────────────────────────── */

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within a <ToastProvider>');
  return ctx;
}

/* ── Toast container ─────────────────────────────────────────────── */

function ToastContainer({
  toasts,
  onDismiss,
}: {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}) {
  if (toasts.length === 0) return null;

  return (
    <div className="toast-container" aria-live="polite">
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

/* ── Single toast item ───────────────────────────────────────────── */

function ToastItem({
  toast: t,
  onDismiss,
}: {
  toast: ToastMessage;
  onDismiss: (id: string) => void;
}) {
  useEffect(() => {
    const duration = t.duration ?? 4000;
    if (duration <= 0) return;
    const timer = setTimeout(() => onDismiss(t.id), duration);
    return () => clearTimeout(timer);
  }, [t.id, t.duration, onDismiss]);

  return (
    <div className={`toast toast--${t.type}`} role="alert">
      <span className="toast__message">{t.message}</span>
      <button
        className="toast__close"
        onClick={() => onDismiss(t.id)}
        aria-label="Dismiss"
      >
        ×
      </button>
    </div>
  );
}
