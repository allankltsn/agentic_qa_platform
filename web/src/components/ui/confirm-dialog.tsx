import { Button } from './button';
import { Dialog, DialogBody, DialogFooter } from './dialog';

export interface ConfirmDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel: string;
  onConfirm: () => void;
  loading?: boolean;
}

export function ConfirmDialog({ isOpen, onOpenChange, title, description, confirmLabel, onConfirm, loading }: ConfirmDialogProps) {
  return (
    <Dialog isOpen={isOpen} onOpenChange={onOpenChange} title={title} size="sm">
      <DialogBody><p className="text-body text-muted">{description}</p></DialogBody>
      <DialogFooter>
        <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancelar</Button>
        <Button variant="danger" loading={loading} onClick={onConfirm}>{confirmLabel}</Button>
      </DialogFooter>
    </Dialog>
  );
}
