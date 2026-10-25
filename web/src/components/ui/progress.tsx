import { ProgressBar } from 'react-aria-components';
import { cn } from '@/lib/utils';

export interface ProgressProps {
  value: number;
  label: string;
  className?: string;
  tone?: 'primary' | 'success';
}

export function Progress({ value, label, className, tone = 'primary' }: ProgressProps) {
  return (
    <ProgressBar value={value} aria-label={label} className={cn('h-2 w-full overflow-hidden rounded-full bg-surface-2', className)}>
      {({ percentage }) => (
        <div className={cn('h-full rounded-full transition-[width] duration-300 motion-reduce:transition-none', tone === 'success' ? 'bg-success' : 'bg-primary')} style={{ width: `${percentage}%` }} />
      )}
    </ProgressBar>
  );
}
