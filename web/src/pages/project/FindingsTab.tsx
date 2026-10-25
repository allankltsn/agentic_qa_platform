import { Box, H3, Item, List, P, Span, Strong } from '@/components/ui/primitives';
import { useState } from 'react';
import { Icon } from '@/brand';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';
import { EmptyState } from '@/components/ui/empty-state';
import { SelectField, TextField } from '@/components/ui/fields';
import { useToast } from '@/components/ui/toast';
import { AGENTS, CATEGORIES, FINDING_STATUSES, SEVERITIES } from '@/domain/catalog';
import { severityTone } from '@/domain/tones';
import type { Finding, FindingStatus, Project } from '@/domain/types';
import { useDeleteFinding } from '@/hooks/queries';

export interface FindingsTabProps {
  project: Project;
  onAdd: () => void;
  onEdit: (finding: Finding) => void;
}

export function FindingsTab({ project, onAdd, onEdit }: FindingsTabProps) {
  const { notify } = useToast();
  const remove = useDeleteFinding(project.id);
  const [filter, setFilter] = useState<'all' | FindingStatus>('all');
  const [search, setSearch] = useState('');
  const [toDelete, setToDelete] = useState<Finding | null>(null);

  const needle = search.trim().toLocaleLowerCase('pt-BR');
  const list = project.findings
    .filter((f) => (filter === 'all' || f.status === filter) && (!needle || `${f.title} ${f.description} ${CATEGORIES[f.category].label}`.toLocaleLowerCase('pt-BR').includes(needle)))
    .sort((a, b) => SEVERITIES[b.severity].rank - SEVERITIES[a.severity].rank);

  return (
    <Box className="flex flex-col gap-4">
      <Box className="flex flex-wrap items-end justify-between gap-3">
        <Box>
          <H3 className="text-heading-sm">Achados registrados</H3>
          <P className="text-body text-muted">Priorize por severidade e acompanhe a correção.</P>
        </Box>
        <Box className="flex flex-wrap items-end gap-2">
          <TextField label="Buscar achados" value={search} onChange={setSearch} placeholder="Buscar achados..." className="w-52" />
          <SelectField hideLabel label="Filtrar achados" className="w-44" value={filter} onChange={(v) => setFilter(v as 'all' | FindingStatus)}
            options={[{ value: 'all', label: 'Todos os status' }, ...Object.entries(FINDING_STATUSES).map(([value, label]) => ({ value, label }))]} />
          <Button leftIcon="plus" onClick={onAdd}>Registrar achado</Button>
        </Box>
      </Box>

      {list.length ? (
        <List className="flex flex-col gap-3">
          {list.map((f) => (
            <Item key={f.id} className="relative flex gap-4 overflow-hidden rounded-md border border-line bg-surface p-4 pl-5 shadow-card">
              <Span aria-hidden="true" className={`absolute inset-y-0 left-0 w-1.5 ${f.severity === 'critical' || f.severity === 'high' ? 'bg-danger' : f.severity === 'medium' ? 'bg-warning' : 'bg-info'}`} />
              <Box className="min-w-0 flex-1">
                <Box className="text-body-medium">{f.title}</Box>
                <Box className="mt-2 flex flex-wrap gap-2">
                  <Badge tone={severityTone[f.severity]}>{SEVERITIES[f.severity].label}</Badge>
                  <Badge>{CATEGORIES[f.category].label}</Badge>
                  <Badge>{FINDING_STATUSES[f.status]}</Badge>
                  {f.source === 'agent' ? <Badge tone="primary"><Icon name="sparkle" size={12} />{AGENTS[f.category].name}</Badge> : null}
                </Box>
                <P className="mt-2 text-body text-muted">{f.description}</P>
                {f.steps ? <P className="mt-1 text-body text-muted"><Strong className="text-ink">Reprodução:</Strong> {f.steps}</P> : null}
                {f.evidence ? <P className="mt-1 text-body text-muted"><Strong className="text-ink">Evidência:</Strong> {f.evidence}</P> : null}
              </Box>
              <Box className="flex shrink-0 flex-col items-end gap-1 sm:flex-row sm:items-start">
                <Button variant="ghost" size="sm" leftIcon="edit" aria-label={`Editar ${f.title}`} onClick={() => onEdit(f)}>Editar</Button>
                <Button variant="ghost-danger" size="sm" aria-label={`Excluir ${f.title}`} onClick={() => setToDelete(f)}><Icon name="trash" size={16} /></Button>
              </Box>
            </Item>
          ))}
        </List>
      ) : (
        <EmptyState icon="flag" title="Nenhum achado encontrado" description={project.findings.length ? 'Ajuste a busca ou o filtro.' : 'Registre o primeiro problema ou aceite uma sugestão dos agentes.'}
          action={<Button variant="soft" onClick={onAdd}>Registrar achado</Button>} />
      )}

      <ConfirmDialog
        isOpen={Boolean(toDelete)}
        onOpenChange={(open) => { if (!open) setToDelete(null); }}
        title="Excluir achado?"
        description={toDelete ? `“${toDelete.title}” será removido desta avaliação.` : ''}
        confirmLabel="Excluir"
        onConfirm={() => { if (toDelete) { remove.mutate(toDelete.id); notify('Achado excluído.'); setToDelete(null); } }}
      />
    </Box>
  );
}
