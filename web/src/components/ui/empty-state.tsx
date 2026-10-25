import type { ReactNode } from 'react';
import { Icon, type IconName } from '@/brand';

export function EmptyState({ icon = 'sparkle', title, description, action }: { icon?: IconName; title: string; description: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-md border border-dashed border-line-strong bg-surface px-6 py-12 text-center">
      <span className="grid h-12 w-12 place-items-center rounded-full bg-primary-soft text-accent-text"><Icon name={icon} size={24} /></span>
      <h3 className="text-heading-sm">{title}</h3>
      <p className="max-w-md text-body text-muted">{description}</p>
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
