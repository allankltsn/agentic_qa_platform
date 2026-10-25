export const CATEGORIES = {
  usability: { label: 'Usabilidade', icon: '◌', description: 'Experiência e clareza' },
  functionality: { label: 'Funcionalidade', icon: '▤', description: 'Fluxos e regras' },
  vulnerabilities: { label: 'Vulnerabilidades', icon: '◇', description: 'Falhas exploráveis' },
  security: { label: 'Segurança', icon: '◇', description: 'Controles e proteção' },
};

export const TYPES = {
  api: { label: 'API', icon: '⌘' },
  frontend: { label: 'Frontend', icon: '▧' },
  agent: { label: 'Agente', icon: '✳' },
};

export const SEVERITIES = {
  critical: { label: 'Crítica', rank: 4 },
  high: { label: 'Alta', rank: 3 },
  medium: { label: 'Média', rank: 2 },
  low: { label: 'Baixa', rank: 1 },
};

export const STATUSES = { pending: 'Pendente', passed: 'Aprovado', failed: 'Falhou', skipped: 'Não se aplica' };
export const FINDING_STATUSES = { open: 'Aberto', in_progress: 'Em correção', resolved: 'Resolvido' };

export const CHECKS = {
  api: {
    usability: ['Documentação descreve parâmetros, erros e exemplos de uso', 'Mensagens de erro são claras e acionáveis', 'Paginação e filtros são consistentes entre rotas'],
    functionality: ['Contratos de entrada e saída atendem aos casos principais', 'Validação cobre entradas inválidas e limites', 'Operações repetidas respeitam idempotência quando aplicável', 'Falhas de dependências têm comportamento previsível'],
    vulnerabilities: ['Entradas resistem a injeção e manipulação de parâmetros', 'Rotas impedem acesso a recursos de outro usuário ou tenant', 'Erros não expõem stack trace, segredos ou dados internos'],
    security: ['Autenticação e autorização são aplicadas por rota', 'Tokens, segredos e dados sensíveis são protegidos', 'Limites de requisição e logs de auditoria são adequados'],
  },
  frontend: {
    usability: ['Fluxos principais são compreensíveis sem instruções extras', 'Interface responde a telas pequenas e navegação por teclado', 'Estados de carregamento, vazio e erro orientam o usuário', 'Textos, foco e contraste são acessíveis'],
    functionality: ['Formulários validam entradas e preservam dados em erros', 'Navegação e ações funcionam nos navegadores alvo', 'Estados de sucesso e falha correspondem às respostas da API'],
    vulnerabilities: ['Campos e conteúdo exibido resistem a scripts injetados', 'Links e redirecionamentos não aceitam destinos inseguros', 'Dependências e arquivos estáticos não expõem segredos'],
    security: ['Sessão expira e logout encerra o acesso', 'Permissões são verificadas no servidor, além da interface', 'Dados sensíveis não ficam expostos em URL ou armazenamento local'],
  },
  agent: {
    usability: ['Instruções e limites do agente são compreensíveis', 'Respostas citam fontes ou incertezas quando necessário', 'Usuário consegue corrigir entradas e entender falhas'],
    functionality: ['Tarefas principais retornam resultados verificáveis', 'Ferramentas lidam com falhas, timeout e respostas inesperadas', 'Saídas estruturadas atendem ao contrato esperado', 'Efeitos externos exigem o nível correto de confirmação'],
    vulnerabilities: ['Injeções de prompt em entradas e ferramentas são testadas', 'O agente não executa instruções vindas de conteúdo não confiável', 'Dados de um usuário ou tenant não aparecem em outro contexto'],
    security: ['Ferramentas seguem menor privilégio e permissões por usuário', 'Segredos e dados sensíveis não aparecem em prompts ou logs', 'Ações e chamadas de ferramentas deixam trilha auditável'],
  },
};

export const uid = () => globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`;

export function templateItems(type, categories) {
  return categories.flatMap(category => (CHECKS[type]?.[category] ?? []).map((title, i) => ({
    id: `${type}:${category}:${i}`, category, title, status: 'pending', custom: false,
  })));
}

export function createProject({ name, type, categories, description = '', stack = '', reference = '' }) {
  const now = new Date().toISOString();
  return { id: uid(), name: name.trim(), type, categories, description: description.trim(), stack: stack.trim(), reference: reference.trim(), createdAt: now, updatedAt: now, items: templateItems(type, categories), findings: [] };
}

export function activeItems(project) {
  return project.items.filter(item => project.categories.includes(item.category) && (item.custom || item.id.startsWith(`${project.type}:`)));
}

export function progress(project) {
  const items = activeItems(project);
  const done = items.filter(item => item.status !== 'pending').length;
  return { done, total: items.length, pct: items.length ? Math.round(done * 100 / items.length) : 0 };
}

export function openFindings(project) {
  return project.findings.filter(f => f.status !== 'resolved');
}

export function priority(project) {
  return [...openFindings(project)].sort((a, b) => SEVERITIES[b.severity].rank - SEVERITIES[a.severity].rank)[0]?.severity ?? null;
}

export function syncTemplates(project) {
  const existing = new Set(project.items.map(item => item.id));
  for (const item of templateItems(project.type, project.categories)) {
    if (!existing.has(item.id)) project.items.push(item);
  }
  return project;
}

export function validateBackup(value) {
  if (!value || value.format !== 'prismaqa-v1' || !Array.isArray(value.projects) || value.projects.length > 100) throw new Error('Formato de backup inválido.');
  return value.projects.map(p => {
    if (!p || typeof p.id !== 'string' || typeof p.name !== 'string' || !TYPES[p.type] || !Array.isArray(p.categories) || !Array.isArray(p.items) || !Array.isArray(p.findings) || p.items.length > 500 || p.findings.length > 1000) throw new Error('O backup contém projetos inválidos.');
    const categories = [...new Set(p.categories.filter(c => CATEGORIES[c]))];
    if (!categories.length || !p.name.trim()) throw new Error('O backup contém categorias ou nomes inválidos.');
    const items = p.items.map(i => {
      if (typeof i?.id !== 'string' || typeof i.title !== 'string' || !CATEGORIES[i.category] || !STATUSES[i.status]) throw new Error('O backup contém testes inválidos.');
      return { id: i.id, title: i.title.slice(0, 180), category: i.category, status: i.status, custom: Boolean(i.custom) };
    });
    const findings = p.findings.map(f => {
      if (typeof f?.id !== 'string' || typeof f.title !== 'string' || !CATEGORIES[f.category] || !SEVERITIES[f.severity] || !FINDING_STATUSES[f.status]) throw new Error('O backup contém achados inválidos.');
      return { id: f.id, title: f.title.slice(0, 120), category: f.category, severity: f.severity, status: f.status, description: String(f.description ?? '').slice(0, 2000), steps: String(f.steps ?? '').slice(0, 1500), evidence: String(f.evidence ?? '').slice(0, 1500), itemId: String(f.itemId ?? ''), createdAt: f.createdAt ?? new Date().toISOString() };
    });
    return { id: p.id, name: p.name.slice(0, 80), type: p.type, categories, description: String(p.description ?? '').slice(0, 600), stack: String(p.stack ?? '').slice(0, 120), reference: String(p.reference ?? '').slice(0, 300), createdAt: p.createdAt ?? new Date().toISOString(), updatedAt: p.updatedAt ?? new Date().toISOString(), items, findings };
  });
}
