import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { forwardRef, type ButtonHTMLAttributes } from 'react';
import { Icon, type IconName } from '@/brand';
import { cn } from '@/lib/utils';
import { Spinner } from './spinner';

export const buttonVariants = cva(
  [
    'inline-flex items-center justify-center gap-2 rounded-sm text-button transition-colors motion-reduce:transition-none',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-text focus-visible:ring-offset-2 focus-visible:ring-offset-surface',
    'disabled:cursor-not-allowed disabled:opacity-50 aria-disabled:cursor-not-allowed aria-disabled:opacity-50',
  ],
  {
    variants: {
      variant: {
        primary: 'bg-primary text-on-primary hover:bg-primary-hover active:bg-primary-press',
        soft: 'bg-primary-soft text-accent-text hover:bg-primary-line/60',
        outline: 'border border-line-strong bg-surface text-ink hover:bg-surface-2 active:bg-line',
        ghost: 'text-ink hover:bg-surface-2 active:bg-line',
        danger: 'bg-danger text-on-danger hover:opacity-90 active:opacity-80',
        'ghost-danger': 'text-danger-text hover:bg-danger-bg',
        nav: 'text-nav-muted hover:bg-nav-2 hover:text-nav-ink',
      },
      size: {
        sm: 'min-h-9 px-3 text-caption font-semibold',
        md: 'min-h-11 px-4',
        lg: 'min-h-12 px-6',
        icon: 'h-11 w-11',
      },
      fullWidth: { true: 'w-full', false: '' },
    },
    defaultVariants: { variant: 'primary', size: 'md', fullWidth: false },
  },
);

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
  leftIcon?: IconName;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant, size, fullWidth, asChild = false, loading = false, leftIcon, className, children, disabled, type = 'button', ...rest },
  ref,
) {
  const classes = cn(buttonVariants({ variant, size, fullWidth }), className);
  if (asChild) return <Slot {...rest} ref={ref} className={classes}>{children}</Slot>;
  return (
    <button ref={ref} type={type} disabled={disabled || loading} aria-busy={loading || undefined} className={classes} {...rest}>
      {loading ? <Spinner size={16} className="text-current" /> : leftIcon ? <Icon name={leftIcon} size={16} /> : null}
      {children}
    </button>
  );
});
