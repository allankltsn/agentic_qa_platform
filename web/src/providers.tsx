import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState, type ReactNode } from 'react';
import { BrowserRouter } from 'react-router';
import { ToastProvider } from '@/components/ui/toast';
import { db } from '@/mock/db';

export function makeQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 30_000 } } });
}

/** Revalida as consultas sempre que o armazenamento mock muda (ex.: o simulador avançou uma execução). */
export function useRevalidateOnDbChange(client: QueryClient) {
  useEffect(() => db.subscribe(() => { void client.invalidateQueries(); }), [client]);
}

export function Providers({ children, router = true }: { children: ReactNode; router?: boolean }) {
  const [client] = useState(makeQueryClient);
  useRevalidateOnDbChange(client);
  const content = <QueryClientProvider client={client}><ToastProvider>{children}</ToastProvider></QueryClientProvider>;
  return router ? <BrowserRouter>{content}</BrowserRouter> : content;
}
