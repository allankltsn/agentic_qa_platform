import { Form } from '@/components/ui/primitives';
import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { Button } from '@/components/ui/button';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';
import { FormRow, SelectField, TextAreaField, TextField } from '@/components/ui/fields';
import { useToast } from '@/components/ui/toast';
import { CATEGORIES, FINDING_STATUSES, SEVERITIES } from '@/domain/catalog';
import { findingSchema, type FindingInput } from '@/domain/schemas';
import { activeItems } from '@/domain/selectors';
import type { Finding, Project } from '@/domain/types';
import { useSaveFinding } from '@/hooks/queries';

const NO_ITEM = 'none';

export interface FindingDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  project: Project;
  finding?: Finding;
  /** Pré-seleciona a verificação ao registrar a partir do checklist. */
  itemId?: string;
}

function defaults(project: Project, finding?: Finding, itemId?: string): FindingInput {
  const item = project.items.find((i) => i.id === (finding?.itemId ?? itemId));
  return finding
    ? { title: finding.title, category: finding.category, severity: finding.severity, status: finding.status, itemId: finding.itemId || NO_ITEM, description: finding.description, steps: finding.steps, evidence: finding.evidence }
    : { title: '', category: item?.category ?? project.categories[0], severity: 'medium', status: 'open', itemId: item?.id ?? NO_ITEM, description: '', steps: '', evidence: '' };
}

export function FindingDialog({ isOpen, onOpenChange, project, finding, itemId }: FindingDialogProps) {
  const { notify } = useToast();
  const save = useSaveFinding(project.id);
  const { control, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FindingInput>({
    resolver: zodResolver(findingSchema),
    defaultValues: defaults(project, finding, itemId),
  });
  useEffect(() => { if (isOpen) reset(defaults(project, finding, itemId)); }, [isOpen, project, finding, itemId, reset]);

  const submit = handleSubmit(async (values) => {
    try {
      await save.mutateAsync({ ...values, itemId: values.itemId === NO_ITEM ? '' : values.itemId }, finding?.id);
      notify(finding ? 'Achado atualizado.' : 'Achado registrado.');
      onOpenChange(false);
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Não foi possível salvar.', 'error');
    }
  });

  return (
    <Dialog isOpen={isOpen} onOpenChange={onOpenChange} kicker="EVIDÊNCIA & AÇÃO" title={finding ? 'Editar achado' : 'Registrar achado'} description="Descreva o problema para facilitar a correção e a retestagem.">
      <Form onSubmit={submit} noValidate>
        <DialogBody>
          <Controller control={control} name="title" render={({ field }) => (
            <TextField {...field} autoFocus label="Título do achado" placeholder="Ex.: Token de acesso não expira" maxLength={120} error={errors.title?.message} />
          )} />
          <FormRow>
            <Controller control={control} name="category" render={({ field }) => (
              <SelectField label="Categoria" value={field.value} onChange={field.onChange} options={project.categories.map((c) => ({ value: c, label: CATEGORIES[c].label }))} />
            )} />
            <Controller control={control} name="severity" render={({ field }) => (
              <SelectField label="Severidade" value={field.value} onChange={field.onChange} options={Object.entries(SEVERITIES).map(([value, s]) => ({ value, label: s.label }))} />
            )} />
          </FormRow>
          <FormRow>
            <Controller control={control} name="status" render={({ field }) => (
              <SelectField label="Status" value={field.value} onChange={field.onChange} options={Object.entries(FINDING_STATUSES).map(([value, label]) => ({ value, label }))} />
            )} />
            <Controller control={control} name="itemId" render={({ field }) => (
              <SelectField label="Referência do teste" value={field.value || NO_ITEM} onChange={field.onChange}
                options={[{ value: NO_ITEM, label: 'Sem vínculo' }, ...activeItems(project).map((i) => ({ value: i.id, label: i.title }))]} />
            )} />
          </FormRow>
          <Controller control={control} name="description" render={({ field }) => (
            <TextAreaField {...field} label="Descrição e impacto" placeholder="O que aconteceu? Qual o impacto?" maxLength={2000} error={errors.description?.message} />
          )} />
          <FormRow>
            <Controller control={control} name="steps" render={({ field }) => (
              <TextAreaField {...field} label="Como reproduzir" placeholder="Passos, rota, ambiente..." maxLength={1500} error={errors.steps?.message} />
            )} />
            <Controller control={control} name="evidence" render={({ field }) => (
              <TextAreaField {...field} label="Evidência ou link" placeholder="Resultado observado, log, captura ou link..." maxLength={1500} error={errors.evidence?.message} />
            )} />
          </FormRow>
        </DialogBody>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button type="submit" loading={isSubmitting}>Salvar achado</Button>
        </DialogFooter>
      </Form>
    </Dialog>
  );
}
