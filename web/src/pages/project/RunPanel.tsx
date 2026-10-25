import { Box, Code, Item, List, OList, P, Span } from '@/components/ui/primitives';
import { Icon } from '@/brand';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardHeader } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Spinner } from '@/components/ui/spinner';
import { AGENTS, SEVERITIES } from '@/domain/catalog';
import { formatTime, runProgress } from '@/domain/selectors';
import { RUN_STATUSES, runStatusTone, severityTone, STEP_STATUSES, stepStatusTone } from '@/domain/tones';
import type { Run } from '@/domain/types';
import { useCancelRun, useResolveProposal } from '@/hooks/queries';

export function RunPanel({ projectId, run }: { projectId: string; run: Run }) {
  const cancel = useCancelRun(projectId);
  const resolve = useResolveProposal(projectId);
  const agent = AGENTS[run.agent];
  const p = runProgress(run);

  return (
    <Box className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
      <Card>
        <CardHeader
          title={`Execução · ${agent.name}`}
          subtitle={`Iniciada às ${formatTime(run.startedAt)}${run.finishedAt ? ` · terminou às ${formatTime(run.finishedAt)}` : ''}`}
          action={
            <Box className="flex items-center gap-2">
              <Badge tone={runStatusTone[run.status]}>{RUN_STATUSES[run.status]}</Badge>
              {run.status === 'running' ? <Button variant="outline" size="sm" leftIcon="stop" onClick={() => cancel.mutate(run.id)}>Interromper</Button> : null}
            </Box>
          }
        />
        <Box className="flex items-center gap-3 border-b border-line px-5 py-3">
          <Progress value={p.percent} label={`Progresso da execução de ${agent.name}`} tone={run.status === 'completed' ? 'success' : 'primary'} />
          <Span className="w-24 shrink-0 text-right text-caption text-muted">{p.finished} de {p.total} passos</Span>
        </Box>
        <OList className="flex flex-col divide-y divide-line" aria-label="Passos da execução">
          {run.steps.map((s) => (
            <Item key={s.id} className="flex items-start gap-3 px-5 py-3">
              <Span className="mt-0.5 grid h-5 w-5 place-items-center">
                {s.status === 'running' ? <Spinner size={16} /> : s.status === 'passed' ? <Span className="text-success-text"><Icon name="check" size={16} /></Span> : s.status === 'failed' ? <Span className="text-danger-text"><Icon name="warning" size={16} /></Span> : <Span className="text-faint"><Icon name="clock" size={16} /></Span>}
              </Span>
              <Box className="min-w-0 flex-1">
                <Box className="text-body"><Code className="rounded-sm bg-surface-2 px-1.5 py-0.5 text-caption">agent.{s.kind}</Code> {s.text}</Box>
                {s.note ? <Box className="text-caption text-muted">{s.note}</Box> : null}
              </Box>
              <Badge tone={stepStatusTone[s.status]}>{STEP_STATUSES[s.status]}</Badge>
            </Item>
          ))}
        </OList>
      </Card>

      <Card className="self-start">
        <CardHeader title="Achados sugeridos" subtitle="Você decide o que entra na avaliação." />
        {run.proposals.length ? (
          <List className="flex flex-col divide-y divide-line">
            {run.proposals.map((pr) => (
              <Item key={pr.id} className="flex flex-col gap-2 px-5 py-4">
                <Box className="flex flex-wrap items-center gap-2">
                  <Badge tone={severityTone[pr.severity]}>{SEVERITIES[pr.severity].label}</Badge>
                  {pr.state === 'accepted' ? <Badge tone="success">Aceito</Badge> : pr.state === 'dismissed' ? <Badge>Descartado</Badge> : null}
                </Box>
                <Box className="text-body-medium">{pr.title}</Box>
                <P className="text-caption text-muted">{pr.description}</P>
                {pr.state === 'pending' ? (
                  <Box className="flex gap-2">
                    <Button size="sm" leftIcon="check" aria-label={`Aceitar sugestão: ${pr.title}`} onClick={() => resolve.mutate(run.id, pr.id, 'accepted')}>Aceitar</Button>
                    <Button size="sm" variant="ghost" aria-label={`Descartar sugestão: ${pr.title}`} onClick={() => resolve.mutate(run.id, pr.id, 'dismissed')}>Descartar</Button>
                  </Box>
                ) : null}
              </Item>
            ))}
          </List>
        ) : (
          <P className="px-5 py-6 text-body text-muted">{run.status === 'running' ? 'O agente ainda está testando. Problemas encontrados aparecem aqui.' : 'Nenhum problema encontrado nesta execução.'}</P>
        )}
      </Card>
    </Box>
  );
}
