import { Box, H3, Item, List, P, Section, Span } from '@/components/ui/primitives';
import { useState } from 'react';
import { Icon } from '@/brand';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { useToast } from '@/components/ui/toast';
import { AGENTS } from '@/domain/catalog';
import { agentsForProject, formatTime, latestRun, runProgress } from '@/domain/selectors';
import { RUN_STATUSES, runStatusTone } from '@/domain/tones';
import type { CategoryId, Project } from '@/domain/types';
import { useStartRun } from '@/hooks/queries';
import { RunPanel } from './RunPanel';

export function AgentsTab({ project }: { project: Project }) {
  const { notify } = useToast();
  const start = useStartRun(project.id);
  const [selected, setSelected] = useState<string | null>(null);
  const run = project.runs.find((r) => r.id === selected) ?? project.runs[0];

  const launch = (agent: CategoryId) => {
    start.mutate(agent);
    setSelected(null);
    notify(`${AGENTS[agent].name} começou a testar (simulação).`);
  };

  return (
    <Box className="flex flex-col gap-6">
      <Box>
        <H3 className="text-heading-sm">Equipe de especialistas</H3>
        <P className="text-body text-muted">Cada categoria ativa tem um agente. Ele executa as verificações, registra o que fez e sugere achados para você aprovar.</P>
      </Box>

      <List className="grid gap-4 md:grid-cols-2">
        {agentsForProject(project).map((id) => {
          const a = AGENTS[id];
          const last = latestRun(project, id);
          const running = last?.status === 'running';
          const p = last ? runProgress(last) : null;
          const pending = last ? last.proposals.filter((x) => x.state === 'pending').length : 0;
          return (
            <Item key={id}>
              <Card className="flex h-full flex-col gap-3 p-5">
                <Box className="flex items-start gap-3">
                  <Span className="grid h-10 w-10 shrink-0 place-items-center rounded-sm bg-primary-soft text-accent-text"><Icon name="agent" size={20} /></Span>
                  <Box className="min-w-0 flex-1">
                    <Box className="text-heading-sm">{a.name}</Box>
                    <Box className="text-caption text-muted">{a.role}</Box>
                  </Box>
                  {last ? <Badge tone={runStatusTone[last.status]}>{RUN_STATUSES[last.status]}</Badge> : <Badge>Nunca executou</Badge>}
                </Box>
                <P className="text-body text-muted">{a.approach}</P>
                <Box className="flex flex-wrap gap-1.5">{a.tools.map((t) => <Badge key={t}>{t}</Badge>)}</Box>
                {p && last ? (
                  <Box className="flex items-center gap-3">
                    <Progress value={p.percent} label={`Progresso de ${a.name}`} tone={last.status === 'completed' ? 'success' : 'primary'} />
                    <Span className="shrink-0 text-caption text-muted">{p.percent}%</Span>
                  </Box>
                ) : null}
                <Box className="mt-auto flex flex-wrap items-center gap-2 pt-1">
                  <Button size="sm" leftIcon="play" disabled={running} onClick={() => launch(id)} aria-label={`Executar ${a.name}`}>{last ? 'Executar de novo' : 'Executar'}</Button>
                  {last ? <Button size="sm" variant="ghost" onClick={() => setSelected(last.id)}>Ver execução</Button> : null}
                  {pending ? <Badge tone="warning">{pending} sugest{pending > 1 ? 'ões' : 'ão'} para revisar</Badge> : null}
                </Box>
              </Card>
            </Item>
          );
        })}
      </List>

      {run ? (
        <Section aria-label="Detalhe da execução" className="flex flex-col gap-4">
          {project.runs.length > 1 ? (
            <Box className="flex flex-wrap items-center gap-2">
              <Span className="text-label">Histórico</Span>
              {project.runs.slice(0, 6).map((r) => (
                <Button key={r.id} size="sm" variant={r.id === run.id ? 'soft' : 'outline'} onClick={() => setSelected(r.id)}>
                  {AGENTS[r.agent].name.split(' · ')[0]} · {formatTime(r.startedAt)}
                </Button>
              ))}
            </Box>
          ) : null}
          <RunPanel projectId={project.id} run={run} />
        </Section>
      ) : null}
    </Box>
  );
}
