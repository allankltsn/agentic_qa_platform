import { Form } from '@/components/ui/primitives';
import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { Button } from '@/components/ui/button';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';
import { SelectField, TextField } from '@/components/ui/fields';
import { useToast } from '@/components/ui/toast';
import { CATEGORIES } from '@/domain/catalog';
import { itemSchema, type ItemInput } from '@/domain/schemas';
import type { Project } from '@/domain/types';
import { useAddItem } from '@/hooks/queries';

export function ItemDialog({ isOpen, onOpenChange, project }: { isOpen: boolean; onOpenChange: (open: boolean) => void; project: Project }) {
  const { notify } = useToast();
  const add = useAddItem(project.id);
  const { control, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<ItemInput>({
    resolver: zodResolver(itemSchema),
    defaultValues: { title: '', category: project.categories[0] },
  });
  useEffect(() => { if (isOpen) reset({ title: '', category: project.categories[0] }); }, [isOpen, project.categories, reset]);

  const submit = handleSubmit(async (values) => {
    try {
      await add.mutateAsync(values);
      notify('Verificação adicionada.');
      onOpenChange(false);
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Não foi possível adicionar.', 'error');
    }
  });

  return (
    <Dialog isOpen={isOpen} onOpenChange={onOpenChange} size="sm" kicker="CHECKLIST" title="Adicionar verificação">
      <Form onSubmit={submit} noValidate>
        <DialogBody>
          <Controller control={control} name="title" render={({ field }) => (
            <TextField {...field} autoFocus label="O que precisa ser validado?" placeholder="Ex.: Rotação de refresh token" maxLength={180} error={errors.title?.message} />
          )} />
          <Controller control={control} name="category" render={({ field }) => (
            <SelectField label="Categoria" value={field.value} onChange={field.onChange} options={project.categories.map((c) => ({ value: c, label: CATEGORIES[c].label }))} />
          )} />
        </DialogBody>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button type="submit" loading={isSubmitting}>Adicionar</Button>
        </DialogFooter>
      </Form>
    </Dialog>
  );
}
