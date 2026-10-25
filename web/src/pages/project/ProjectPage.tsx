import { Box, H1, H2, P, Section, Span, Strong } from '@/components/ui/primitives';
import { useState } from 'react';
import { Navigate, useNavigate, useParams, useSearchParams } from 'react-router';
import { Icon } from '@/brand';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, Kicker } from '@/components/ui/card';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';
import { Progress } from '@/components/ui/progress';
import { Spinner } from '@/components/ui/spinner';
import { Tabs } from '@/components/ui/tabs';
import { useToast } from '@/components/ui/toast';
import { SEVERITIES, TYPES } from '@/domain/catalog';
import { formatDate, openFindings, pendingProposals, progress, topPriority } from '@/domain/selectors';
import { severityTone } from '@/domain/tones';
import type { Finding } from '@/domain/types';
import { useDeleteProject, useProject } from '@/hooks/queries';
import { AgentsTab } from './AgentsTab';
import { ChecklistTab } from './ChecklistTab';
import { FindingDialog } from './FindingDialog';
import { FindingsTab } from './FindingsTab';
import { ItemDialog } from './ItemDialog';
import { OverviewTab } from './OverviewTab';
import { ProjectDialog } from './ProjectDialog';

const TAB_IDS = ['overview', 'checklist', 'findings', 'agents'] as const;

export function ProjectPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { notify } = useToast();
  const [params, setParams] = useSearchParams();
  const { data: project, isLoading, isError } = useProject(projectId);
  const remove = useDeleteProject();

  const [editing, setEditing] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [itemOpen, setItemOpen] = useState(false);
  const [findingDialog, setFindingDialog] = useState<{ open: boolean; finding?: Finding; itemId?: string }>({ open: false });

  if (isLoading) return <Box className="grid place-items-center py-24"><Spinner size={28} label="Carregando avaliação" /></Box>;
  if (isError || !project) return <Navigate to="/app" replace />;

  const tabParam = params.get('tab');
  const tab = (TAB_IDS as readonly string[]).includes(tabParam ?? '') ? (tabParam as string) : 'overview';
  const prog = progress(project);
  const open = openFindings(project);
  const top = topPriority(project);
  const proposals = pendingProposals(project);

  return (
    <Box className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-6 sm:px-8">
      <Section aria-labelledby="project-title" className="flex flex-wrap items-start justify-between gap-4">
        <Box className="min-w-0 max-w-3xl">
          <Box className="flex items-center gap-3 text-caption text-muted">
            <Badge tone="primary"><Icon name={TYPES[project.type].icon} size={12} />{TYPES[project.type].label}</Badge>
            <Span>Atualizado em {formatDate(project.updatedAt)}</Span>
          </Box>
          <H1 id="project-title" className="mt-2 text-display">{project.name}</H1>
          {project.description ? <P className="mt-2 text-body text-muted">{project.description}</P> : null}
          {project.stack ? <Box className="mt-3"><Badge>{project.stack}</Badge></Box> : null}
        </Box>
        <Box className="flex gap-2">
          <Button variant="soft" leftIcon="edit" onClick={() => setEditing(true)}>Editar contexto</Button>
          <Button variant="ghost-danger" onClick={() => setConfirmDelete(true)}>Excluir</Button>
        </Box>
      </Section>

      <Section aria-label="Indicadores da avaliação" className="grid gap-4 md:grid-cols-3">
        <Card className="p-5">
          <Box className="text-kicker uppercase tracking-[0.12em] text-muted">Progresso do checklist</Box>
          <Box className="mt-2 flex items-baseline gap-2"><Strong className="text-heading-lg">{prog.percent}%</Strong><Span className="text-caption text-muted">{prog.done} de {prog.total} verificados</Span></Box>
          <Progress className="mt-3" value={prog.percent} label="Progresso do checklist" />
        </Card>
        <Card className="p-5">
          <Box className="text-kicker uppercase tracking-[0.12em] text-muted">Achados em aberto</Box>
          <Box className="mt-2 flex items-baseline gap-2"><Strong className="text-heading-lg">{open.length}</Strong><Span className="text-caption text-muted">{open.length ? 'Aguardando correção' : 'Aguardando triagem'}</Span></Box>
          {proposals ? <Box className="mt-3"><Badge tone="warning">{proposals} sugest{proposals > 1 ? 'ões' : 'ão'} de agentes para revisar</Badge></Box> : null}
        </Card>
        <Card className="p-5">
          <Box className="text-kicker uppercase tracking-[0.12em] text-muted">Risco prioritário</Box>
          <Box className="mt-2 flex items-baseline gap-2">
            <Strong className="text-heading-lg">{top ? SEVERITIES[top].label : '—'}</Strong>
            <Span className="text-caption text-muted">{top ? 'Maior severidade em aberto' : 'Sem achados críticos'}</Span>
          </Box>
          {top ? <Box className="mt-3"><Badge tone={severityTone[top]}>{open.filter((f) => f.severity === top).length} em {SEVERITIES[top].label.toLowerCase()}</Badge></Box> : null}
        </Card>
      </Section>

      <Section aria-label="Área de trabalho" className="rounded-md border border-line bg-surface p-5 shadow-card">
        <Box className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <Box>
            <Kicker>SUA AVALIAÇÃO</Kicker>
            <H2 className="text-heading-md">Plano de validação</H2>
            <P className="text-body text-muted">Organize o que precisa ser testado e acompanhe os resultados.</P>
          </Box>
          <Button variant="outline" leftIcon="plus" onClick={() => setFindingDialog({ open: true })}>Registrar achado</Button>
        </Box>
        <Tabs
          label="Visualizações"
          activeId={tab}
          onChange={(id) => setParams({ tab: id }, { replace: true })}
          items={[
            { id: 'overview', label: 'Visão geral', content: <OverviewTab project={project} /> },
            { id: 'checklist', label: 'Checklist', count: prog.total, content: <ChecklistTab project={project} onAddItem={() => setItemOpen(true)} onAddFinding={(itemId) => setFindingDialog({ open: true, itemId })} /> },
            { id: 'findings', label: 'Achados', count: project.findings.length, content: <FindingsTab project={project} onAdd={() => setFindingDialog({ open: true })} onEdit={(finding) => setFindingDialog({ open: true, finding })} /> },
            { id: 'agents', label: 'Agentes', count: proposals || undefined, content: <AgentsTab project={project} /> },
          ]}
        />
      </Section>

      <ProjectDialog isOpen={editing} onOpenChange={setEditing} project={project} />
      <ItemDialog isOpen={itemOpen} onOpenChange={setItemOpen} project={project} />
      <FindingDialog isOpen={findingDialog.open} onOpenChange={(o) => setFindingDialog((s) => ({ ...s, open: o }))} project={project} finding={findingDialog.finding} itemId={findingDialog.itemId} />
      <ConfirmDialog
        isOpen={confirmDelete}
        onOpenChange={setConfirmDelete}
        title="Excluir avaliação?"
        description={`“${project.name}” e todos os seus achados e execuções serão removidos deste navegador.`}
        confirmLabel="Excluir avaliação"
        loading={remove.isPending}
        onConfirm={async () => {
          await remove.mutateAsync(project.id);
          notify('Avaliação excluída.');
          navigate('/app', { replace: true });
        }}
      />
    </Box>
  );
}
