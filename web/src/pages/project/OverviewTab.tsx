import { Box, Dd, Dl, Dt, Em, ExtLink, Item, List, Span, Strong } from '@/components/ui/primitives';
import { Icon } from '@/brand';
import { Card, CardHeader } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { CATEGORIES, TYPES } from '@/domain/catalog';
import { categoryProgress, formatDate, validLink } from '@/domain/selectors';
import type { Project } from '@/domain/types';

export function OverviewTab({ project }: { project: Project }) {
  const link = validLink(project.reference);
  return (
    <Box className="flex flex-col gap-5">
      <Box className="grid gap-5 lg:grid-cols-[1.6fr_1fr]">
        <Card>
          <CardHeader title="Cobertura da avaliação" subtitle={`${project.categories.length} categorias ativas`} />
          <List className="flex flex-col divide-y divide-line">
            {project.categories.map((c) => {
              const p = categoryProgress(project, c);
              return (
                <Item key={c} className="grid grid-cols-[auto_1fr_auto] items-center gap-4 px-5 py-4 sm:grid-cols-[auto_1fr_160px_auto]">
                  <Span className="grid h-9 w-9 place-items-center rounded-sm bg-primary-soft text-accent-text"><Icon name={CATEGORIES[c].icon} size={18} /></Span>
                  <Box>
                    <Box className="text-label">{CATEGORIES[c].label}</Box>
                    <Box className="text-caption text-muted">{p.done} de {p.total} verificados</Box>
                  </Box>
                  <Progress className="hidden sm:block" value={p.percent} label={`Progresso de ${CATEGORIES[c].label}`} />
                  <Span className="w-10 text-right text-label">{p.percent}%</Span>
                </Item>
              );
            })}
          </List>
        </Card>
        <Card>
          <CardHeader title="Contexto do projeto" subtitle={TYPES[project.type].label} />
          <Dl className="flex flex-col gap-4 px-5 py-4">
            <Box><Dt className="text-kicker uppercase tracking-[0.12em] text-muted">Stack / ferramentas</Dt><Dd className="mt-1 text-body">{project.stack || 'Ainda não informado'}</Dd></Box>
            <Box>
              <Dt className="text-kicker uppercase tracking-[0.12em] text-muted">Referência</Dt>
              <Dd className="mt-1 text-body">
                {link ? <ExtLink href={link} className="inline-flex items-center gap-1 text-accent-text underline-offset-2 hover:underline">{project.reference}<Icon name="external" size={14} /></ExtLink> : project.reference || 'Ainda não informado'}
              </Dd>
            </Box>
            <Box><Dt className="text-kicker uppercase tracking-[0.12em] text-muted">Última atualização</Dt><Dd className="mt-1 text-body">{formatDate(project.updatedAt)}</Dd></Box>
          </Dl>
        </Card>
      </Box>
      <Box className="rounded-md border border-primary-line bg-primary-soft px-5 py-4 text-body">
        <Strong>Próximo passo:</Strong> abra a aba <Em>Agentes</Em>, execute os especialistas e revise as sugestões de achados. Você também pode marcar o checklist manualmente.
        <Span className="text-muted"> Nesta fase as execuções são simuladas; nenhum sistema real é testado.</Span>
      </Box>
    </Box>
  );
}
