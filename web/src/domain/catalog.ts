import type { IconName } from '@/brand';
import type { CategoryId, FindingStatus, ItemStatus, ProjectType, Severity } from './types';

export const CATEGORIES: Record<CategoryId, { label: string; icon: IconName; description: string }> = {
  usability: { label: 'Usabilidade', icon: 'usability', description: 'Experiência e clareza' },
  functionality: { label: 'Funcionalidade', icon: 'functionality', description: 'Fluxos e regras' },
  vulnerabilities: { label: 'Vulnerabilidades', icon: 'vulnerabilities', description: 'Falhas exploráveis' },
  security: { label: 'Segurança', icon: 'security', description: 'Controles e proteção' },
};
export const CATEGORY_IDS = Object.keys(CATEGORIES) as CategoryId[];

export const TYPES: Record<ProjectType, { label: string; icon: IconName; description: string }> = {
  api: { label: 'API', icon: 'api', description: 'Endpoints e serviços' },
  frontend: { label: 'Frontend', icon: 'frontend', description: 'Interfaces e jornadas' },
  agent: { label: 'Agente', icon: 'agent', description: 'IA e ferramentas' },
};
export const TYPE_IDS = Object.keys(TYPES) as ProjectType[];

export const SEVERITIES: Record<Severity, { label: string; rank: number }> = {
  critical: { label: 'Crítica', rank: 4 },
  high: { label: 'Alta', rank: 3 },
  medium: { label: 'Média', rank: 2 },
  low: { label: 'Baixa', rank: 1 },
};
export const SEVERITY_IDS = Object.keys(SEVERITIES) as Severity[];

export const ITEM_STATUSES: Record<ItemStatus, string> = { pending: 'Pendente', passed: 'Aprovado', failed: 'Falhou', skipped: 'Não se aplica' };
export const FINDING_STATUSES: Record<FindingStatus, string> = { open: 'Aberto', in_progress: 'Em correção', resolved: 'Resolvido' };

export const CHECKS: Record<ProjectType, Record<CategoryId, string[]>> = {
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

/** Equipe de especialistas: um agente por categoria de teste. Nesta fase, apenas descrição para a interface. */
export interface AgentSpec {
  id: CategoryId;
  name: string;
  role: string;
  approach: string;
  tools: string[];
}

export const AGENTS: Record<CategoryId, AgentSpec> = {
  usability: {
    id: 'usability',
    name: 'Ana · Usabilidade',
    role: 'Especialista em UX e acessibilidade',
    approach: 'Percorre as jornadas como um usuário leigo e observa clareza, foco, contraste e mensagens.',
    tools: ['Navegador (Playwright)', 'Axe (acessibilidade)', 'Capturas de tela'],
  },
  functionality: {
    id: 'functionality',
    name: 'Caio · Funcionalidade',
    role: 'Especialista em testes funcionais',
    approach: 'Descreve objetivos em linguagem natural, executa os fluxos e confirma o resultado com asserções.',
    tools: ['Navegador (Playwright)', 'Cliente HTTP', 'Asserções semânticas'],
  },
  vulnerabilities: {
    id: 'vulnerabilities',
    name: 'Vera · Vulnerabilidades',
    role: 'Especialista em testes ofensivos autorizados',
    approach: 'Tenta injeção, acesso cruzado entre tenants e vazamento de detalhes internos em ambiente de teste.',
    tools: ['Cliente HTTP', 'Fuzzing de parâmetros', 'Navegador (Playwright)'],
  },
  security: {
    id: 'security',
    name: 'Sol · Segurança',
    role: 'Especialista em controles e conformidade',
    approach: 'Revisa autenticação, autorização, segredos, limites de requisição e trilhas de auditoria.',
    tools: ['Cliente HTTP', 'Revisão de configuração', 'Análise de cabeçalhos'],
  },
};
