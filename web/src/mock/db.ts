import { CATEGORY_IDS, CHECKS } from '@/domain/catalog';
import { uid } from '@/domain/selectors';
import type { CategoryId, ChecklistItem, Project, ProjectType } from '@/domain/types';

const KEY = 'prismaqa.web.v1';
export const BACKUP_FORMAT = 'prismaqa-v1';

export function templateItems(type: ProjectType, categories: CategoryId[]): ChecklistItem[] {
  return categories.flatMap((category) =>
    CHECKS[type][category].map((title, i) => ({ id: `${type}:${category}:${i}`, category, title, status: 'pending' as const, custom: false })),
  );
}

export function buildProject(input: { name: string; type: ProjectType; categories: CategoryId[]; description?: string; stack?: string; reference?: string }): Project {
  const now = new Date().toISOString();
  return {
    id: uid(),
    name: input.name.trim(),
    type: input.type,
    categories: input.categories,
    description: (input.description ?? '').trim(),
    stack: (input.stack ?? '').trim(),
    reference: (input.reference ?? '').trim(),
    createdAt: now,
    updatedAt: now,
    items: templateItems(input.type, input.categories),
    findings: [],
    runs: [],
  };
}

function seed(): Project[] {
  const p = buildProject({
    name: 'API de autenticação · exemplo',
    type: 'api',
    categories: CATEGORY_IDS,
    description: 'Exemplo para explorar o fluxo de revisão. Crie sua própria avaliação para começar.',
    stack: 'NestJS · PostgreSQL',
  });
  p.items[0].status = 'passed';
  p.items[3].status = 'passed';
  p.items[7].status = 'failed';
  p.findings.push({
    id: uid(),
    title: 'Mensagens de erro expõem detalhes internos',
    category: 'vulnerabilities',
    severity: 'high',
    status: 'open',
    itemId: p.items[7].id,
    description: 'Exemplo fictício: uma resposta de erro expõe detalhes de implementação. Validar o tratamento de exceções e retornar mensagens seguras.',
    steps: 'Enviar uma entrada inválida ao endpoint de exemplo.',
    evidence: 'Registro ilustrativo, sem teste executado.',
    createdAt: new Date().toISOString(),
    source: 'manual',
  });
  return [p];
}

function isProject(value: unknown): value is Project {
  const p = value as Project;
  return Boolean(p) && typeof p.id === 'string' && typeof p.name === 'string' && p.type in CHECKS
    && Array.isArray(p.categories) && Array.isArray(p.items) && Array.isArray(p.findings);
}

/** Aceita backups do protótipo anterior (sem `runs`/`source`) e normaliza. */
export function normalizeBackup(raw: unknown): Project[] {
  const data = raw as { format?: string; projects?: unknown };
  if (!data || data.format !== BACKUP_FORMAT || !Array.isArray(data.projects)) throw new Error('Arquivo de backup inválido.');
  const projects = data.projects.filter(isProject).map((p) => ({
    ...p,
    runs: Array.isArray(p.runs) ? p.runs : [],
    findings: p.findings.map((f) => ({ ...f, source: f.source ?? 'manual' })),
  }));
  if (!projects.length && data.projects.length) throw new Error('Nenhum projeto válido no backup.');
  return projects;
}

type Listener = () => void;
const listeners = new Set<Listener>();
let cache: Project[] | null = null;

function persist(projects: Project[]) {
  try { localStorage.setItem(KEY, JSON.stringify({ format: BACKUP_FORMAT, projects })); } catch { /* armazenamento cheio ou bloqueado: segue em memória */ }
}

function read(): Project[] {
  if (cache) return cache;
  try {
    const raw = localStorage.getItem(KEY);
    cache = raw ? normalizeBackup(JSON.parse(raw)) : seed();
  } catch {
    cache = seed();
  }
  // Execuções que estavam rodando quando a página fechou não continuam: marcamos como interrompidas.
  for (const project of cache) {
    for (const run of project.runs) {
      if (run.status === 'running') {
        run.status = 'cancelled';
        run.finishedAt = new Date().toISOString();
        run.steps.forEach((s) => { if (s.status === 'running') s.status = 'pending'; });
      }
    }
  }
  persist(cache);
  return cache;
}

export const db = {
  all: (): Project[] => read(),
  get: (id: string): Project | undefined => read().find((p) => p.id === id),
  /** Aplica uma mudança, persiste e avisa os ouvintes (a UI revalida as consultas). */
  mutate(fn: (projects: Project[]) => void) {
    const projects = read();
    fn(projects);
    persist(projects);
    listeners.forEach((l) => l());
  },
  replaceAll(projects: Project[]) {
    cache = projects;
    persist(projects);
    listeners.forEach((l) => l());
  },
  subscribe(listener: Listener) {
    listeners.add(listener);
    return () => { listeners.delete(listener); };
  },
  /** Somente testes. */
  reset() { cache = null; },
};
