import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CATEGORY_IDS } from '@/domain/catalog';
import { activeItems, progress } from '@/domain/selectors';
import { api, mockLatency } from './api';
import { db } from './db';
import { runnerConfig, simulatedFailure } from './runner';

beforeEach(() => {
  localStorage.clear();
  db.reset();
  mockLatency.ms = 0;
  runnerConfig.stepDelayMs = 0;
});

const create = () => api.createProject({ name: 'Alvo', type: 'api', categories: [...CATEGORY_IDS], description: '', stack: '', reference: '' });

describe('simulador de agentes', () => {
  it('executa os passos, atualiza o checklist e gera sugestões só para o que falhou', async () => {
    const project = await create();
    await api.startRun(project.id, 'security');
    await vi.waitFor(async () => expect((await api.getProject(project.id)).runs[0].status).toBe('completed'));

    const after = await api.getProject(project.id);
    const items = activeItems(after).filter((i) => i.category === 'security');
    const failing = items.filter((i) => simulatedFailure(i.title));
    expect(after.runs[0].steps).toHaveLength(items.length * 2);
    expect(after.runs[0].proposals).toHaveLength(failing.length);
    expect(items.every((i) => i.verifiedBy === 'security' && i.status === (simulatedFailure(i.title) ? 'failed' : 'passed'))).toBe(true);
    expect(progress(after).done).toBe(items.length);
  });

  it('só vira achado quando a pessoa aceita a sugestão', async () => {
    const project = await create();
    // Escolhe uma categoria em que o resultado simulado tenha ao menos uma falha.
    const agent = CATEGORY_IDS.find((c) => activeItems(project).some((i) => i.category === c && simulatedFailure(i.title)));
    expect(agent).toBeDefined();
    await api.startRun(project.id, agent!);
    await vi.waitFor(async () => expect((await api.getProject(project.id)).runs[0].status).toBe('completed'));

    const run = (await api.getProject(project.id)).runs[0];
    expect((await api.getProject(project.id)).findings).toHaveLength(0);
    await api.resolveProposal(project.id, run.id, run.proposals[0].id, 'accepted');
    const after = await api.getProject(project.id);
    expect(after.findings).toHaveLength(1);
    expect(after.findings[0]).toMatchObject({ source: 'agent', runId: run.id, status: 'open' });
    await expect(api.resolveProposal(project.id, run.id, run.proposals[0].id, 'accepted')).rejects.toThrow();
  });

  it('recusa executar duas vezes o mesmo agente e permite interromper', async () => {
    runnerConfig.stepDelayMs = 50;
    const project = await create();
    await api.startRun(project.id, 'usability');
    await expect(api.startRun(project.id, 'usability')).rejects.toThrow('já está em execução');
    const run = (await api.getProject(project.id)).runs[0];
    await api.cancelRun(project.id, run.id);
    const after = (await api.getProject(project.id)).runs[0];
    expect(after.status).toBe('cancelled');
    expect(after.steps.some((s) => s.status === 'running')).toBe(false);
  });
});

describe('backup', () => {
  it('exporta e importa, aceitando backups do protótipo anterior (sem runs)', async () => {
    const legacy = JSON.stringify({
      format: 'prismaqa-v1',
      projects: [{ id: 'p1', name: 'Antigo', type: 'api', categories: ['security'], description: '', stack: '', reference: '', createdAt: '', updatedAt: '', items: [], findings: [{ id: 'f', title: 't', category: 'security', severity: 'low', status: 'open', itemId: '', description: 'd', steps: '', evidence: '', createdAt: '' }] }],
    });
    expect(await api.importBackup(legacy)).toBe(1);
    const [p] = await api.listProjects();
    expect(p.runs).toEqual([]);
    expect(p.findings[0].source).toBe('manual');
    expect(JSON.parse(await api.exportBackup()).projects).toHaveLength(1);
    await expect(api.importBackup('{"format":"outro"}')).rejects.toThrow('inválido');
    await expect(api.importBackup('não é json')).rejects.toThrow('JSON');
  });
});
