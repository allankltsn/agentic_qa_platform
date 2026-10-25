import { Box, H3, Header, Item, List, P, Section, Span } from '@/components/ui/primitives';
import { useState } from 'react';
import { Icon } from '@/brand';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { SelectField } from '@/components/ui/fields';
import { AGENTS, CATEGORIES, ITEM_STATUSES } from '@/domain/catalog';
import { activeItems } from '@/domain/selectors';
import type { ItemStatus, Project } from '@/domain/types';
import { useSetItemStatus } from '@/hooks/queries';

export interface ChecklistTabProps {
  project: Project;
  onAddItem: () => void;
  onAddFinding: (itemId: string) => void;
}

export function ChecklistTab({ project, onAddItem, onAddFinding }: ChecklistTabProps) {
  const [filter, setFilter] = useState<'all' | ItemStatus>('all');
  const setStatus = useSetItemStatus(project.id);
  const items = activeItems(project).filter((i) => filter === 'all' || i.status === filter);

  return (
    <Box className="flex flex-col gap-4">
      <Box className="flex flex-wrap items-end justify-between gap-3">
        <Box>
          <H3 className="text-heading-sm">Verificações</H3>
          <P className="text-body text-muted">Registre o resultado de cada teste ou deixe o agente especialista verificar.</P>
        </Box>
        <Box className="flex items-end gap-2">
          <SelectField hideLabel label="Filtrar verificações" size="sm" className="w-44" value={filter} onChange={(v) => setFilter(v as 'all' | ItemStatus)}
            options={[{ value: 'all', label: 'Todos os status' }, ...Object.entries(ITEM_STATUSES).map(([value, label]) => ({ value, label }))]} />
          <Button variant="outline" size="sm" leftIcon="plus" onClick={onAddItem}>Verificação</Button>
        </Box>
      </Box>

      {project.categories.map((c) => {
        const rows = items.filter((i) => i.category === c);
        if (!rows.length) return null;
        return (
          <Section key={c} className="overflow-hidden rounded-md border border-line bg-surface shadow-card" aria-label={CATEGORIES[c].label}>
            <Header className="flex items-center gap-2 border-b border-line bg-surface-2/60 px-4 py-3 text-label">
              <Span className="text-accent-text"><Icon name={CATEGORIES[c].icon} size={16} /></Span>
              {CATEGORIES[c].label}
              <Span className="text-caption font-normal text-muted">{rows.length} verificações</Span>
            </Header>
            <List className="divide-y divide-line">
              {rows.map((i) => (
                <Item key={i.id} className="grid grid-cols-1 items-center gap-3 px-4 py-3 md:grid-cols-[1fr_auto_auto]">
                  <Box>
                    <Box className="text-body-medium">{i.title}</Box>
                    <Box className="mt-0.5 flex flex-wrap gap-2 text-caption text-muted">
                      {i.custom ? <Span>Adicionado por você</Span> : null}
                      {i.verifiedBy ? <Badge tone="primary"><Icon name="sparkle" size={12} />{AGENTS[i.verifiedBy].name}</Badge> : null}
                    </Box>
                  </Box>
                  <SelectField hideLabel label={`Status: ${i.title}`} size="sm" className="w-40" value={i.status} onChange={(v) => setStatus.mutate(i.id, v as ItemStatus)}
                    options={Object.entries(ITEM_STATUSES).map(([value, label]) => ({ value, label }))} />
                  <Button variant="soft" size="sm" leftIcon="plus" onClick={() => onAddFinding(i.id)}>Achado</Button>
                </Item>
              ))}
            </List>
          </Section>
        );
      })}

      {!items.length ? (
        <EmptyState icon="list" title="Nenhuma verificação neste filtro" description="Mude o filtro ou adicione um teste ao checklist." action={<Button variant="soft" onClick={onAddItem}>Adicionar verificação</Button>} />
      ) : null}
    </Box>
  );
}
