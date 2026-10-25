import { Form } from '@/components/ui/primitives';
import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { Button } from '@/components/ui/button';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';
import { CheckboxCards, FormRow, RadioCards, TextAreaField, TextField } from '@/components/ui/fields';
import { useToast } from '@/components/ui/toast';
import { CATEGORIES, CATEGORY_IDS, TYPES, TYPE_IDS } from '@/domain/catalog';
import { projectSchema, type ProjectInput } from '@/domain/schemas';
import type { Project } from '@/domain/types';
import { useCreateProject, useUpdateProject } from '@/hooks/queries';

const empty: ProjectInput = { name: '', type: 'api', categories: [...CATEGORY_IDS], description: '', stack: '', reference: '' };

const fromProject = (p: Project): ProjectInput => ({ name: p.name, type: p.type, categories: p.categories, description: p.description, stack: p.stack, reference: p.reference });

export interface ProjectDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  /** Quando informado, edita o projeto; senão cria um novo. */
  project?: Project;
  onSaved?: (project: Project) => void;
}

export function ProjectDialog({ isOpen, onOpenChange, project, onSaved }: ProjectDialogProps) {
  const { notify } = useToast();
  const create = useCreateProject();
  const update = useUpdateProject(project?.id ?? '');
  const { control, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<ProjectInput>({
    resolver: zodResolver(projectSchema),
    defaultValues: project ? fromProject(project) : empty,
  });

  useEffect(() => { if (isOpen) reset(project ? fromProject(project) : empty); }, [isOpen, project, reset]);

  const submit = handleSubmit(async (values) => {
    try {
      const saved = project ? await update.mutateAsync(values) : await create.mutateAsync(values);
      notify(project ? 'Avaliação atualizada.' : 'Avaliação criada.');
      onOpenChange(false);
      onSaved?.(saved);
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Não foi possível salvar.', 'error');
    }
  });

  return (
    <Dialog isOpen={isOpen} onOpenChange={onOpenChange} kicker="CONFIGURAÇÃO" title={project ? 'Editar contexto' : 'Nova avaliação'} description="Defina o contexto para montar o checklist e a equipe de agentes.">
      <Form onSubmit={submit} noValidate>
        <DialogBody>
          <Controller control={control} name="name" render={({ field }) => (
            <TextField {...field} autoFocus label="Nome do projeto" placeholder="Ex.: API de autenticação" maxLength={80} error={errors.name?.message} />
          )} />
          <Controller control={control} name="type" render={({ field }) => (
            <RadioCards label="Tipo de projeto" value={field.value} onChange={field.onChange} options={TYPE_IDS.map((id) => ({ value: id, label: TYPES[id].label, description: TYPES[id].description, icon: TYPES[id].icon }))} />
          )} />
          <Controller control={control} name="categories" render={({ field }) => (
            <CheckboxCards label="Categorias de teste (cada uma ativa um agente especialista)" value={field.value} onChange={field.onChange} error={errors.categories?.message}
              options={CATEGORY_IDS.map((id) => ({ value: id, label: CATEGORIES[id].label, description: CATEGORIES[id].description, icon: CATEGORIES[id].icon }))} />
          )} />
          <Controller control={control} name="description" render={({ field }) => (
            <TextAreaField {...field} label="Descrição e escopo" placeholder="O que será avaliado? Quais fluxos estão no escopo?" maxLength={600} error={errors.description?.message} />
          )} />
          <FormRow>
            <Controller control={control} name="stack" render={({ field }) => (
              <TextField {...field} label="Stack ou ferramentas" placeholder="Ex.: NestJS, PostgreSQL" maxLength={120} error={errors.stack?.message} />
            )} />
            <Controller control={control} name="reference" render={({ field }) => (
              <TextField {...field} label="URL ou referência" placeholder="https://... ou link do repositório" maxLength={300} error={errors.reference?.message} />
            )} />
          </FormRow>
        </DialogBody>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button type="submit" loading={isSubmitting}>Salvar avaliação</Button>
        </DialogFooter>
      </Form>
    </Dialog>
  );
}
