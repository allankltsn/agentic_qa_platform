import { cn } from '@/lib/utils';
import { Icon } from './icons';

export interface LogoProps {
  className?: string;
  tagline?: string;
}

export function Logo({ className, tagline = 'WORKSPACE' }: LogoProps) {
  return (
    <span role="img" aria-label="Prisma QA" className={cn('inline-flex items-center gap-3', className)}>
      <span className="grid h-9 w-9 place-items-center rounded-md bg-accent text-nav"><Icon name="sparkle" size={22} /></span>
      <span className="flex flex-col leading-none">
        <span className="text-heading-sm tracking-tight">prisma<span className="text-accent">qa</span></span>
        <span className="mt-1 text-kicker tracking-[0.18em] text-nav-muted">{tagline}</span>
      </span>
    </span>
  );
}
