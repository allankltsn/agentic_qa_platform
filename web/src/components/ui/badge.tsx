import { cva, type VariantProps } from 'class-variance-authority';
import type { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

const badgeVariants = cva('inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-caption font-semibold', {
  variants: {
    tone: {
      neutral: 'bg-surface-2 text-muted',
      primary: 'bg-primary-soft text-accent-text',
      success: 'bg-success-bg text-success-text',
      warning: 'bg-warning-bg text-warning-text',
      danger: 'bg-danger-bg text-danger-text',
      info: 'bg-info-bg text-info-text',
    },
  },
  defaultVariants: { tone: 'neutral' },
});

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export const Badge = ({ tone, className, ...rest }: BadgeProps) => <span {...rest} className={cn(badgeVariants({ tone }), className)} />;
