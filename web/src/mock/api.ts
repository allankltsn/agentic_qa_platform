import type { FindingInput, ItemInput, ProjectInput } from '@/domain/schemas';
import { uid } from '@/domain/selectors';
import type { CategoryId, Finding, ItemStatus, Project, ProjectType, Severity } from '@/domain/types';
import { BACKUP_FORMAT, buildProject, db, normalizeBackup, templateItems } from './db';
import { cancelRun, startRun } from './runner';

/**
 * API simulada. A forma das funções (assíncronas, recebendo e devolvendo dados serializáveis) é a que a API real vai
 * seguir; só esta pasta é trocada quando o backend existir.
 */
export const mockLatency = { ms: 120 };
const wait = () => new Promise<void>((resolve) => setTimeout(resolve, mockLatency.ms));

function need(id: string): Project {
  const project = db.get(id);
  if (!project) throw new Error('Projeto não encontrado.');
  return project;
}

const clone = <T,>(value: T): T => structuredClone(value);

export const api = {
  async listProjects(): Promise<Project[]> {
    await wait();
    return clone(db.all());
  },

  async getProject(id: string): Promise<Project> {
    await wait();
    return clone(need(id));
  },

  async createProject(input: ProjectInput): Promise<Project> {
    await wait();
    const project = buildProject({ ...input, type: input.type as ProjectType, categories: input.categories as CategoryId[] });
    db.mutate((all) => { all.unshift(project); });
    return clone(project);
  },

  async updateProject(id: string, input: ProjectInput): Promise<Project> {
    await wait();
    const project = need(id);
    db.mutate(() => {
      const type = input.type as ProjectType;
      const categories = input.categories as CategoryId[];
      const typeChanged = project.type !== type;
      Object.assign(project, { name: input.name, description: input.description, stack: input.stack, reference: input.reference, categories, type, updatedAt: new Date().toISOString() });
      // Itens personalizados e já avaliados são preservados; o modelo é recriado quando o tipo muda.
      const known = new Map(project.items.map((i) => [i.id, i]));
      const template = templateItems(type, categories).map((i) => (typeChanged ? i : known.get(i.id) ?? i));
      const custom = project.items.filter((i) => i.custom && categories.includes(i.category));
      project.items = [...template, ...custom];
    });
    return clone(project);
  },

  async deleteProject(id: string): Promise<void> {
    await wait();
    need(id);
    db.mutate((all) => { const i = all.findIndex((p) => p.id === id); all.splice(i, 1); });
  },

  async setItemStatus(projectId: string, itemId: string, status: ItemStatus): Promise<void> {
    await wait();
    const project = need(projectId);
    db.mutate(() => {
      const item = project.items.find((i) => i.id === itemId);
      if (!item) throw new Error('Verificação não encontrada.');
      item.status = status;
      delete item.verifiedBy;
      project.updatedAt = new Date().toISOString();
    });
  },

  async addItem(projectId: string, input: ItemInput): Promise<void> {
    await wait();
    const project = need(projectId);
    db.mutate(() => {
      project.items.push({ id: uid(), category: input.category as CategoryId, title: input.title, status: 'pending', custom: true });
      project.updatedAt = new Date().toISOString();
    });
  },

  async saveFinding(projectId: string, input: FindingInput, findingId?: string): Promise<void> {
    await wait();
    const project = need(projectId);
    db.mutate(() => {
      const data = { ...input, category: input.category as CategoryId, severity: input.severity as Severity, status: input.status as Finding['status'] };
      const existing = findingId ? project.findings.find((f) => f.id === findingId) : undefined;
      if (existing) Object.assign(existing, data);
      else project.findings.unshift({ ...data, id: uid(), createdAt: new Date().toISOString(), source: 'manual' });
      project.updatedAt = new Date().toISOString();
    });
  },

  async deleteFinding(projectId: string, findingId: string): Promise<void> {
    await wait();
    const project = need(projectId);
    db.mutate(() => { project.findings = project.findings.filter((f) => f.id !== findingId); project.updatedAt = new Date().toISOString(); });
  },

  async startRun(projectId: string, agent: CategoryId): Promise<void> {
    await wait();
    startRun(projectId, agent);
  },

  async cancelRun(projectId: string, runId: string): Promise<void> {
    await wait();
    cancelRun(projectId, runId);
  },

  async resolveProposal(projectId: string, runId: string, proposalId: string, decision: 'accepted' | 'dismissed'): Promise<void> {
    await wait();
    const project = need(projectId);
    db.mutate(() => {
      const run = project.runs.find((r) => r.id === runId);
      const proposal = run?.proposals.find((p) => p.id === proposalId);
      if (!run || !proposal || proposal.state !== 'pending') throw new Error('Sugestão não encontrada.');
      proposal.state = decision;
      if (decision === 'accepted') {
        project.findings.unshift({
          id: uid(),
          title: proposal.title,
          category: run.agent,
          severity: proposal.severity,
          status: 'open',
          itemId: proposal.itemId,
          description: proposal.description,
          steps: proposal.steps,
          evidence: proposal.evidence,
          createdAt: new Date().toISOString(),
          source: 'agent',
          runId: run.id,
        });
      }
      project.updatedAt = new Date().toISOString();
    });
  },

  async exportBackup(): Promise<string> {
    await wait();
    return JSON.stringify({ format: BACKUP_FORMAT, projects: db.all() }, null, 2);
  },

  async importBackup(text: string): Promise<number> {
    await wait();
    let parsed: unknown;
    try { parsed = JSON.parse(text); } catch { throw new Error('O arquivo não é um JSON válido.'); }
    const projects = normalizeBackup(parsed);
    db.replaceAll(projects);
    return projects.length;
  },
};
