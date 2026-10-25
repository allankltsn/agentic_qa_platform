import { CATEGORY_IDS, SEVERITIES } from './catalog';
import type { CategoryId, Finding, Project, Run, Severity } from './types';

export const uid = (): string => globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`;

export function activeItems(project: Project) {
  return project.items.filter((item) => project.categories.includes(item.category) && (item.custom || item.id.startsWith(`${project.type}:`)));
}

export function progress(project: Project) {
  const items = activeItems(project);
  const done = items.filter((item) => item.status !== 'pending').length;
  return { done, total: items.length, percent: items.length ? Math.round((done / items.length) * 100) : 0 };
}

export function categoryProgress(project: Project, category: CategoryId) {
  const items = activeItems(project).filter((item) => item.category === category);
  const done = items.filter((item) => item.status !== 'pending').length;
  return { done, total: items.length, percent: items.length ? Math.round((done / items.length) * 100) : 0 };
}

export const openFindings = (project: Project): Finding[] => project.findings.filter((f) => f.status !== 'resolved');

export function topPriority(project: Project): Severity | null {
  return openFindings(project).reduce<Severity | null>((top, f) => (!top || SEVERITIES[f.severity].rank > SEVERITIES[top].rank ? f.severity : top), null);
}

export const pendingProposals = (project: Project) => project.runs.reduce((n, run) => n + run.proposals.filter((p) => p.state === 'pending').length, 0);

export const latestRun = (project: Project, agent: CategoryId): Run | undefined =>
  project.runs.filter((run) => run.agent === agent).sort((a, b) => b.startedAt.localeCompare(a.startedAt))[0];

export const runProgress = (run: Run) => {
  const finished = run.steps.filter((s) => s.status === 'passed' || s.status === 'failed').length;
  return { finished, total: run.steps.length, percent: run.steps.length ? Math.round((finished / run.steps.length) * 100) : 0 };
};

export const agentsForProject = (project: Project): CategoryId[] => CATEGORY_IDS.filter((c) => project.categories.includes(c));

export function validLink(value: string): string | null {
  try {
    const url = new URL(value);
    return ['http:', 'https:'].includes(url.protocol) ? url.href : null;
  } catch {
    return null;
  }
}

export function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.valueOf()) ? 'Data indisponível' : new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' }).format(d);
}

export function formatTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.valueOf()) ? '—' : new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(d);
}
