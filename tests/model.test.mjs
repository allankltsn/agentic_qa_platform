import test from 'node:test';
import assert from 'node:assert/strict';
import { createProject, progress, priority, syncTemplates, validateBackup, activeItems } from '../model.js';

test('a checklist follows the project type and selected categories', () => {
  const p = createProject({ name: ' Agente de suporte ', type: 'agent', categories: ['functionality', 'security'] });
  assert.equal(p.name, 'Agente de suporte');
  assert.equal(p.items.length, 7);
  assert.ok(p.items.every(item => p.categories.includes(item.category)));
  p.items[0].status = 'passed';
  p.items[1].status = 'skipped';
  assert.deepEqual(progress(p), { done: 2, total: 7, pct: 29 });
  p.categories = ['functionality'];
  assert.equal(progress(p).total, 4);
  p.categories = ['functionality', 'security'];
  syncTemplates(p);
  assert.equal(p.items.length, 7);
  assert.equal(p.items[0].status, 'passed');
  p.type = 'api';
  syncTemplates(p);
  assert.ok(activeItems(p).every(item => item.id.startsWith('api:')));
});

test('only unresolved findings affect priority', () => {
  const p = createProject({ name: 'API', type: 'api', categories: ['security'] });
  p.findings.push({ severity: 'critical', status: 'resolved' }, { severity: 'medium', status: 'open' }, { severity: 'high', status: 'in_progress' });
  assert.equal(priority(p), 'high');
});

test('backup rejects invalid records and retains valid project data', () => {
  const p = createProject({ name: 'Interface', type: 'frontend', categories: ['usability'] });
  const [restored] = validateBackup({ format: 'prismaqa-v1', projects: [p] });
  assert.equal(restored.items.length, p.items.length);
  assert.throws(() => validateBackup({ format: 'prismaqa-v1', projects: [{ ...p, type: 'unknown' }] }));
});
