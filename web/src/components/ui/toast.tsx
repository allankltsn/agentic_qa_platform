import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface ToastContextValue { notify: (message: string, tone?: 'info' | 'error') => void }
const ToastContext = createContext<ToastContextValue>({ notify: () => undefined });

export const useToast = () => useContext(ToastContext);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<{ message: string; tone: 'info' | 'error' } | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout>>();
  const notify = useCallback((message: string, tone: 'info' | 'error' = 'info') => {
    clearTimeout(timer.current);
    setToast({ message, tone });
    timer.current = setTimeout(() => setToast(null), 3500);
  }, []);
  useEffect(() => () => clearTimeout(timer.current), []);
  const value = useMemo(() => ({ notify }), [notify]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div role="status" aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-6 z-[60] flex justify-center px-4">
        {toast ? (
          <div className={cn('pointer-events-auto rounded-md px-4 py-3 text-body shadow-dialog', toast.tone === 'error' ? 'bg-danger text-on-danger' : 'bg-nav text-nav-ink')}>
            {toast.message}
          </div>
        ) : null}
      </div>
    </ToastContext.Provider>
  );
}
