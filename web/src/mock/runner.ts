import { AGENTS, CATEGORIES } from '@/domain/catalog';
import { activeItems, uid } from '@/domain/selectors';
import type { CategoryId, FindingProposal, Project, Run, RunStep, Severity } from '@/domain/types';
import { db } from './db';

/** Intervalo entre passos simulados. Os testes reduzem para 0. */
export const runnerConfig = { stepDelayMs: 750 };

const timers = new Map<string, ReturnType<typeof setTimeout>>();

function hash(text: string): number {
  let h = 0;
  for (let i = 0; i < text.length; i += 1) h = (h * 31 + text.charCodeAt(i)) >>> 0;
  return h;
}

/** Resultado determinístico e simulado: cerca de 1 em 4 verificações falha. */
export const simulatedFailure = (title: string): boolean => hash(title) % 4 === 0;

const SEVERITY_BY_CATEGORY: Record<CategoryId, Severity[]> = {
  usability: ['low', 'medium', 'medium'],
  functionality: ['medium', 'high', 'medium'],
  vulnerabilities: ['high', 'critical', 'high'],
  security: ['high', 'medium', 'critical'],
};

function buildProposal(title: string, category: CategoryId, itemId: string): FindingProposal {
  const severity = SEVERITY_BY_CATEGORY[category][hash(title) % 3];
  return {
    id: uid(),
    itemId,
    title: `${CATEGORIES[category].label}: ${title}`,
    severity,
    description: `Simulação: o agente de ${CATEGORIES[category].label.toLowerCase()} não conseguiu confirmar que "${title.toLowerCase()}". Dado fictício para validar a tela.`,
    steps: 'Passos registrados pelo agente na execução (simulados).',
    evidence: 'Registro da execução simulada; nenhum sistema real foi testado.',
    state: 'pending',
  };
}

export function buildSteps(project: Project, agent: CategoryId): RunStep[] {
  return activeItems(project)
    .filter((item) => item.category === agent && item.status !== 'skipped')
    .flatMap((item) => [
      { id: uid(), kind: 'act' as const, text: `Exercitar: ${item.title}`, itemId: item.id, status: 'pending' as const },
      { id: uid(), kind: 'assert' as const, text: `Verificar: ${item.title}`, itemId: item.id, status: 'pending' as const },
    ]);
}

function findRun(projectId: string, runId: string): { project: Project; run: Run } | null {
  const project = db.get(projectId);
  const run = project?.runs.find((r) => r.id === runId);
  return project && run ? { project, run } : null;
}

function advance(projectId: string, runId: string) {
  timers.delete(runId);
  const found = findRun(projectId, runId);
  if (!found || found.run.status !== 'running') return;

  db.mutate(() => {
    const { project, run } = found;
    const current = run.steps.find((s) => s.status === 'running');
    if (current) {
      const item = project.items.find((i) => i.id === current.itemId);
      if (current.kind === 'assert' && item) {
        const failed = simulatedFailure(item.title);
        current.status = failed ? 'failed' : 'passed';
        current.note = failed ? 'Comportamento diferente do esperado.' : 'Confirmado conforme o esperado.';
        item.status = failed ? 'failed' : 'passed';
        item.verifiedBy = run.agent;
        if (failed) run.proposals.push(buildProposal(item.title, run.agent, item.id));
      } else {
        current.status = 'passed';
        current.note = 'Ação executada.';
      }
      project.updatedAt = new Date().toISOString();
    }
    const next = run.steps.find((s) => s.status === 'pending');
    if (next) {
      next.status = 'running';
    } else {
      run.status = 'completed';
      run.finishedAt = new Date().toISOString();
    }
  });

  const after = findRun(projectId, runId);
  if (after?.run.status === 'running') timers.set(runId, setTimeout(() => advance(projectId, runId), runnerConfig.stepDelayMs));
}

export function startRun(projectId: string, agent: CategoryId): Run {
  const project = db.get(projectId);
  if (!project) throw new Error('Projeto não encontrado.');
  if (!project.categories.includes(agent)) throw new Error(`${AGENTS[agent].name} não está ativo neste projeto.`);
  if (project.runs.some((r) => r.agent === agent && r.status === 'running')) throw new Error('Este agente já está em execução.');
  const steps = buildSteps(project, agent);
  if (!steps.length) throw new Error('Não há verificações para este agente executar.');
  steps[0].status = 'running';
  const run: Run = { id: uid(), agent, status: 'running', startedAt: new Date().toISOString(), steps, proposals: [] };
  db.mutate(() => { project.runs.unshift(run); });
  timers.set(run.id, setTimeout(() => advance(projectId, run.id), runnerConfig.stepDelayMs));
  return run;
}

export function cancelRun(projectId: string, runId: string) {
  const timer = timers.get(runId);
  if (timer) clearTimeout(timer);
  timers.delete(runId);
  const found = findRun(projectId, runId);
  if (!found || found.run.status !== 'running') return;
  db.mutate(() => {
    found.run.status = 'cancelled';
    found.run.finishedAt = new Date().toISOString();
    found.run.steps.forEach((s) => { if (s.status === 'running') s.status = 'pending'; });
  });
}
