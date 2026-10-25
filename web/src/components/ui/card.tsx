import type { HTMLAttributes, ReactNode } from 'react';
import { cn } from '@/lib/utils';

export const Card = ({ className, ...rest }: HTMLAttributes<HTMLDivElement>) => (
  <div {...rest} className={cn('rounded-md border border-line bg-surface shadow-card', className)} />
);

export function CardHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-line px-5 py-4">
      <div>
        <h3 className="text-heading-sm">{title}</h3>
        {subtitle ? <p className="text-caption text-muted">{subtitle}</p> : null}
      </div>
      {action}
    </div>
  );
}

export const Kicker = ({ children }: { children: ReactNode }) => <div className="text-kicker uppercase tracking-[0.14em] text-accent-text">{children}</div>;
