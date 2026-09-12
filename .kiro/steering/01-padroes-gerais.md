---
inclusion: always
---

# Padrões Gerais de Código

Convenções e padrões de qualidade aplicáveis a qualquer linguagem ou projeto do time.

## Convenções de Nomenclatura

- Variáveis e funções: `snake_case` (Python), `camelCase` (TypeScript/JavaScript)
- Classes: `PascalCase` em todas as linguagens
- Constantes: `UPPER_SNAKE_CASE`
- Arquivos: `kebab-case` ou `snake_case`, consistente por projeto
- Diretórios: `kebab-case`, nomes descritivos e curtos
- Interfaces TypeScript: prefixo `I` não obrigatório, preferir nomes descritivos (ex: `UserRepository`)
- Evitar abreviações ambíguas; nomes devem expressar intenção claramente
- Booleanos: prefixar com `is_`, `has_`, `should_`, `can_` para clareza

## Padrão de Commits (Conventional Commits)

- Formato: `<tipo>(<escopo opcional>): <descrição curta>`
- Tipos obrigatórios:
  - `feat:` — nova funcionalidade
  - `fix:` — correção de bug
  - `chore:` — manutenção, dependências, configs
  - `docs:` — documentação
  - `refactor:` — refatoração sem mudança de comportamento
  - `test:` — adição ou correção de testes
  - `ci:` — mudanças em CI/CD
  - `perf:` — melhoria de performance
- Descrição em português ou inglês, consistente por repositório
- Máximo 72 caracteres na primeira linha
- Breaking changes: adicionar `!` após o tipo (ex: `feat!: remove endpoint legado`)
- Corpo do commit opcional para contexto adicional

## Documentação de Código

- Toda função pública deve ter docstring/JSDoc descrevendo propósito, parâmetros e retorno
- Comentários inline apenas para lógica não-óbvia; evitar comentários redundantes
- README.md obrigatório na raiz de cada projeto com: descrição, setup, uso, deploy
- Manter documentação atualizada junto com mudanças de código
- Usar exemplos de uso em docstrings quando a interface não for trivial
- Arquivos de configuração devem ter comentários explicando valores não-padrão

## Segurança Básica

- Nunca fazer hardcode de segredos, tokens, senhas ou chaves de API no código
- Usar variáveis de ambiente para configurações sensíveis
- Arquivo `.env` deve estar no `.gitignore` — nunca commitar
- Fornecer `.env.example` com placeholders para documentar variáveis necessárias
- Usar AWS Secrets Manager ou SSM Parameter Store para segredos em produção
- Validar e sanitizar toda entrada de dados externa (API, eventos, formulários)
- Aplicar princípio do menor privilégio em permissões IAM
- Dependências devem ser auditadas regularmente (`npm audit`, `pip-audit`, `safety`)
- Não expor stack traces ou detalhes internos em respostas de erro para o cliente

## Logging Estruturado

- Formato obrigatório: JSON
- Campos obrigatórios em cada log:
  - `timestamp` — ISO 8601 (ex: `2024-01-15T10:30:00Z`)
  - `level` — `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
  - `message` — descrição legível do evento
  - `correlation_id` — identificador para rastreamento entre serviços
- Campos recomendados:
  - `service` — nome do serviço/função
  - `function_name` — nome da função Lambda ou método
  - `request_id` — ID da requisição (Lambda context)
  - `extra` — dados adicionais relevantes ao contexto
- Usar AWS Lambda Powertools Logger para padronização automática
- Níveis de log:
  - `DEBUG` — detalhes para desenvolvimento, desativado em produção
  - `INFO` — eventos normais de operação
  - `WARNING` — situações inesperadas que não impedem execução
  - `ERROR` — falhas que impedem a operação atual
  - `CRITICAL` — falhas que comprometem o sistema
- Nunca logar dados sensíveis (PII, tokens, senhas, dados de cartão)
- Incluir contexto suficiente para reproduzir problemas sem acesso ao código

## Observabilidade

- Habilitar AWS X-Ray tracing em todas as funções Lambda
- Usar AWS Lambda Powertools Tracer para instrumentação automática
- Métricas customizadas via CloudWatch EMF (Embedded Metric Format):
  - Latência de operações críticas
  - Contagem de erros por tipo
  - Métricas de negócio relevantes
- Alarmes CloudWatch obrigatórios para:
  - Taxa de erros acima do threshold (ex: > 1% em 5 minutos)
  - Latência P99 acima do SLA
  - Throttling de Lambda ou serviços downstream
  - Dead Letter Queue com mensagens
- Dashboards CloudWatch por serviço com métricas-chave
- Correlacionar logs, traces e métricas usando `correlation_id` consistente
- Configurar retenção de logs adequada (ex: 30 dias dev, 90 dias prod)
