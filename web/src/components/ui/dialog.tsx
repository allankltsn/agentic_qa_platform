import type { ReactNode } from 'react';
import { Dialog as AriaDialog, Heading, Modal, ModalOverlay } from 'react-aria-components';
import { Icon } from '@/brand';
import { cn } from '@/lib/utils';

export interface DialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  kicker?: string;
  description?: string;
  size?: 'sm' | 'md';
  children: ReactNode;
}

export function Dialog({ isOpen, onOpenChange, title, kicker, description, size = 'md', children }: DialogProps) {
  return (
    <ModalOverlay isOpen={isOpen} onOpenChange={onOpenChange} isDismissable className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-nav/60 p-4">
      <Modal className={cn('w-full rounded-lg bg-surface shadow-dialog outline-none', size === 'sm' ? 'max-w-md' : 'max-w-2xl')}>
        <AriaDialog className="flex max-h-[90dvh] flex-col outline-none">
          {({ close }) => (
            <>
              <div className="flex items-start justify-between gap-4 border-b border-line px-6 py-5">
                <div>
                  {kicker ? <div className="text-kicker uppercase tracking-[0.14em] text-accent-text">{kicker}</div> : null}
                  <Heading slot="title" className="text-heading-md">{title}</Heading>
                  {description ? <p className="mt-1 text-body text-muted">{description}</p> : null}
                </div>
                <button type="button" aria-label="Fechar" onClick={close} className="grid h-9 w-9 place-items-center rounded-sm text-muted outline-none hover:bg-surface-2 hover:text-ink focus-visible:ring-2 focus-visible:ring-accent-text">
                  <Icon name="close" size={18} />
                </button>
              </div>
              <div className="overflow-y-auto">{children}</div>
            </>
          )}
        </AriaDialog>
      </Modal>
    </ModalOverlay>
  );
}

export const DialogBody = ({ children }: { children: ReactNode }) => <div className="flex flex-col gap-4 px-6 py-5">{children}</div>;
export const DialogFooter = ({ children }: { children: ReactNode }) => <div className="flex justify-end gap-2 border-t border-line px-6 py-4">{children}</div>;
