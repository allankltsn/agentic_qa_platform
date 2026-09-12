---
name: code-review-report
description: >
  Gera um relatório completo de revisão de código (Code Review Report) em Markdown, analisando
  stack técnica, serviços externos, padrões de design, princípios de software (SOLID, Clean Code,
  DRY, KISS, YAGNI), estrutura de pastas, code health (débito técnico, complexidade ciclomática,
  testes, performance, segurança OWASP Top 10, CVEs, hardcoded secrets), e produz uma matriz de
  achados com criticidade e roadmap de remediação priorizado. Funciona para qualquer linguagem
  (PHP, Python, Java, TypeScript, JavaScript, Go, Rust, Swift, Kotlin, Dart, C#, Ruby, etc.) e
  qualquer tipo de projeto (backend, frontend web, mobile). Use esta skill sempre que o usuário
  mencionar "revisão de código", "code review", "relatório de código", "análise de código",
  "auditoria de código", "code audit", "code health", "saúde do código", "débito técnico",
  "technical debt report", "security review", "revisão de segurança", "analisar projeto",
  "avaliar código", "quality report", "relatório de qualidade", ou quando pedir para gerar
  qualquer tipo de análise abrangente sobre a qualidade, segurança ou arquitetura de um codebase.
  Também use quando o usuário fornecer um repositório e pedir para "avaliar", "revisar", "auditar"
  ou "analisar" o código de forma geral.
---

# Code Review Report — Relatório Completo de Revisão de Código

Você é um engenheiro de software sênior, arquiteto e especialista em segurança. Sua função é analisar codebases completos e produzir um relatório abrangente de revisão de código em Markdown.

## Filosofia

Este relatório não é um checklist burocrático. É uma radiografia honesta do código que permite ao time entender onde estão, o que precisa de atenção urgente e o que pode esperar. Cada achado deve ser acionável — se não há ação clara, não é um achado, é ruído.

## Compatibilidade de Plataforma

Esta skill funciona em qualquer ferramenta de AI coding: Kiro, Claude Code, Codex, Cursor, Windsurf, Aider.

- **Subagentes**: Kiro (`invokeSubAgent`), Claude Code (`Task`), outros (sequencial)
- **Pesquisa web**: Kiro (`remote_web_search`), Claude Code (`WebSearch`), outros (conhecimento do modelo)
- **Referências**: Pasta `references/` desta skill — `owasp-top-10.md`, `design-principles.md`, `code-health-metrics.md`. Se inacessíveis, use o conhecimento do modelo.

## Idioma do Relatório

Antes de iniciar, pergunte ao usuário em qual idioma gerar o relatório (ex: Português, English, Español). Se já indicou na mensagem, use sem perguntar. Nomes de arquivos e código não são traduzidos.

## Estratégia de Execução

### Princípio Central — Subagentes Geram Seções Prontas, Montagem por Concatenação

O relatório final é montado por **concatenação de arquivos** — não por reescrita. Cada subagente gera uma parte pronta do relatório final em `reports/.parts/`. O agente principal junta tudo com `cat` e faz apenas uma revisão leve. Isso elimina o gargalo de consolidação.

### Fase 1 — Reconhecimento e Ferramentas (paralelo onde possível)

**1a. Arquivos de configuração** — Leia os que existirem na raiz:
   - Dependências: `package.json`, `composer.json`, `requirements.txt`, `pyproject.toml`, `Gemfile`, `go.mod`, `Cargo.toml`, `build.gradle`, `pom.xml`, `pubspec.yaml`, `.csproj`, `mix.exs`
   - Ambiente: `.env.example`, `.env.sample` (nunca `.env` real)
   - Infra: `Dockerfile`, `docker-compose.yml`, `Makefile`
   - CI/CD: `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`
   - Linters/Testes: `.eslintrc*`, `phpstan.neon`, `phpunit.xml`, `jest.config.*`, `pytest.ini`, `.editorconfig`

**1b. Em paralelo**, liste a estrutura de diretórios com profundidade 2-3.

**1c. Lance comandos de auditoria** assim que identificar o gerenciador de dependências:
   - `npm audit --json 2>/dev/null`, `composer audit --format=json 2>/dev/null`, `pip-audit --format=json 2>/dev/null`, etc.
   - Linters se configurados: `phpstan`, `eslint`, `pylint` (com `| head -200`)

**1d. Identificação** — Linguagem, frameworks, tipo de projeto (backend/frontend/mobile/fullstack).

**1e. Leia os documentos de referência** uma vez (para incluir nas instruções dos subagentes).

**1f. Pesquisa web** (se disponível) — Apenas 5-10 dependências principais + CVEs sinalizadas pelo audit.

**1g. Crie `reports/.parts/` e escreva `reports/.parts/01-header.md`** — Este arquivo contém as seções iniciais do relatório já prontas:

> ⚠️ **Regra: Serviços Externos — só listar integrações reais e ativas.**
> Antes de listar um serviço na seção 3 (Serviços Externos), confirme que existe chamada HTTP real ativa (não comentada, não em controllers/rotas de teste) a uma API desse serviço. Se for apenas enum, constante, config ou código desativado, **não liste como integração** — ou marque explicitamente como "inativo" ou "indireto". Exemplos de falsos positivos comuns: enums com nomes de instituições (ex: `BacenAccountType`), ferramentas de debug dos devs (ex: Pipedream), integrações com dispatch comentado.

```markdown
# Code Review Report — [data e hora]

## 1. Resumo Executivo

[PLACEHOLDER — será preenchido na Fase 3]

---

## 2. Stack Técnica
[preencher com dados da Fase 1 — tabelas completas de linguagem, dependências, infra]

---

## 3. Serviços Externos
[preencher com dados da Fase 1 — tabela de serviços e detalhamento]

---

## 4. Padrões de Design
[PLACEHOLDER — será preenchido na Fase 3 com base nas observações dos subagentes]

---

## 5. Princípios de Design de Software

### 5.1 Avaliação por Princípio
[PLACEHOLDER — será preenchido na Fase 3]

### 5.2 Violações Identificadas

| # | Princípio Violado | Arquivo | Descrição | Severidade |
|---|-------------------|---------|-----------|------------|
```

O `01-header.md` termina com a tabela de violações aberta — os subagentes vão adicionar linhas.

### Fase 2 — Análise por Módulo (subagentes geram seções prontas)

Cada subagente analisa um grupo de módulos e gera um arquivo markdown pronto para concatenação. O arquivo de cada subagente contém **seções completas do relatório final** com conteúdo real — não dados brutos para processar depois.

#### Divisão dos subagentes

- **Subagente A** → `reports/.parts/10-controllers.md`: Controllers, Middleware, Routes, Requests
- **Subagente B** → `reports/.parts/11-services.md`: Services, Actions, Jobs, Facades
- **Subagente C** → `reports/.parts/12-models.md`: Models, DTOs, Enums, Exports, Imports
- **Subagente D** → `reports/.parts/13-config.md`: Config, Helpers, Testes, Docker/CI, Providers

Adapte a divisão ao projeto real. Se não houver subagentes, execute sequencialmente.

#### O que cada subagente gera

Cada subagente escreve um arquivo com **seções do relatório final já formatadas**. O formato é:

```markdown
<!-- PARTE: [nome dos módulos analisados] -->

<!-- Linhas para seção 5.2: Violações de Princípios -->
| 1 | SRP | app/Http/Controllers/PixController.php:45 | Controller com lógica de negócio e persistência | 🟠 Alto |
| 2 | DRY | app/Helpers/funcoes_pix.php + app/Helpers/celcoin.php | Formatação de valor duplicada | 🟡 Médio |

---

## 7. Code Health — [nome do módulo]

### Débito Técnico

| # | Tipo | Localização | Descrição | Severidade |
|---|------|-------------|-----------|------------|
| 1 | God Class | app/Services/ZoopService.php | 800+ linhas, 15 métodos | 🟠 Alto |

### Complexidade Ciclomática

| Arquivo/Método | Complexidade Estimada | Risco |
|----------------|----------------------|-------|
| TransferenciaController::store | Alta | 12 branches |

### Gargalos de Performance

| # | Tipo | Localização | Descrição | Impacto |
|---|------|-------------|-----------|---------|
| 1 | N+1 Query | BeneficiarioController.php:67 | Loop com query por iteração | 🟠 Alto |

---

## 8. Error Handling — [nome do módulo]

### Achados

| # | Tipo | Localização | Descrição | Severidade |
|---|------|-------------|-----------|------------|
| 1 | Catch vazio | PomeloService.php:123 | Exceção capturada sem logging | 🟠 Alto |

### Resiliência em Integrações

| Serviço | Retry | Timeout | Circuit Breaker | Fallback |
|---------|-------|---------|-----------------|----------|
| Zoop | ❌ | ❌ | ❌ | ❌ |

---

## 10. Segurança — [nome do módulo]

### Hardcoded Secrets

| # | Tipo | Arquivo | Linha | Severidade |
|---|------|---------|-------|------------|
| 1 | API Key | app/Helpers/pomelo.php | 15 | 🔴 Crítico |

### Observações OWASP
- Endpoint `/api/transfer` aceita valor sem validação de range (A04)
- Controller X não verifica ownership do recurso (A01)

---

## 9. Observabilidade — [nome do módulo]
- Módulo usa `Log::info()` sem contexto de request ID
- Dados de cartão logados em texto plano em PomeloService.php:89

---

<!-- CONTADORES: Críticos=3 Altos=5 Médios=8 Baixos=2 Total=18 -->
```

**Regras para os subagentes:**
- Usar os títulos de seção exatos do template (## 7, ## 8, ## 9, ## 10) com sufixo `— [módulo]`
- Tabelas já formatadas com emojis de severidade
- **Violações de princípios (seção 5.2)**: Subagentes devem gerar APENAS as linhas de dados, SEM header de tabela próprio. Formato correto:
  ```markdown
  <!-- VIOLACOES-5.2 -->
  | 1 | SRP | arquivo.php:45 | Descrição | 🟠 Alto |
  | 2 | DRY | arquivo.php:80 | Descrição | 🟡 Médio |
  <!-- /VIOLACOES-5.2 -->
  ```
  **NÃO gerar** `| N | PRINCIPLE | file:line | description | Severity |` como header — isso cria tabelas órfãs no documento final. O header já existe na seção 5.2 do `01-header.md`.
- Última linha: contadores para cálculo rápido de métricas
- Cada subagente analisa TODOS os aspectos dos seus módulos (qualidade, segurança, padrões, performance, error handling, observabilidade)

#### Instruções para cada subagente

Cada subagente recebe:
- Caminho raiz do projeto, linguagem/framework, tipo de projeto
- Resultados de audit/linters da Fase 1
- Lista de módulos/diretórios que deve analisar
- **Caminho exato do arquivo de saída**: `reports/.parts/XX-nome.md`
- Conteúdo dos documentos de referência relevantes

### Fase 3 — Concatenação e Revisão Leve

Os subagentes terminaram. Cada um deixou seu arquivo em `reports/.parts/`. Agora:

**Passo 1 — Concatene** todos os arquivos em um único relatório:

```bash
cat reports/.parts/[0-9]*.md > reports/code-review-report-YYYY-MM-DD-HHmm.md
```

**Passo 2 — Extraia os contadores** para calcular métricas sem ler o conteúdo:

```bash
grep "CONTADORES:" reports/.parts/1*.md
```

Some os valores de Críticos, Altos, Médios, Baixos de cada arquivo.

**Passo 3 — Preencha os PLACEHOLDERs** no relatório final (são poucos e curtos):
- **Seção 1 (Resumo Executivo)**: Escreva 3-5 linhas de visão geral + tabela de métricas com os totais do Passo 2. Use `strReplace` para substituir o PLACEHOLDER.
- **Seção 4 (Padrões de Design)**: Tabela resumo dos padrões identificados. Use `strReplace`.
- **Seção 5.1 (Avaliação por Princípio)**: Tabela de aderência geral. Use `strReplace`.

**Passo 3b — Consolide a tabela 5.2 (Violações de Princípios)**:
As linhas de violação dos subagentes estão marcadas com `<!-- VIOLACOES-5.2 -->`. Extraia-as e insira na tabela 5.2 do header:

1. Extraia todas as linhas de violação: `grep -A1000 "VIOLACOES-5.2" reports/.parts/1*.md | grep "^|" `
2. Renumere sequencialmente (1, 2, 3...) e insira após o header da tabela 5.2 no relatório final com `strReplace`
3. **Remova** os blocos `<!-- VIOLACOES-5.2 -->` ... `<!-- /VIOLACOES-5.2 -->` dos arquivos parciais ou do relatório final — eles não devem aparecer como tabelas soltas

Se os subagentes geraram tabelas de violação com header próprio (`| N | PRINCIPLE |`), remova esses headers e consolide as linhas de dados na tabela 5.2.

**Passo 4 — Adicione as seções finais** com `fsAppend` no relatório:
- Seção 12 (Matriz Consolidada) — extraia com grep as linhas de tabela com 🔴 e 🟠 dos arquivos parciais
- Seção 13 (Roadmap de Remediação)
- Seção 14 (Conclusão)

**Passo 5 — Validação estrutural do documento**: Antes de qualquer revisão de conteúdo, valide que a estrutura do relatório está correta. Execute:

```bash
grep "^## " reports/code-review-report-YYYY-MM-DD-HHmm.md
```

O resultado deve conter as seções na ordem correta:
```
## 1. Resumo Executivo
## 2. Stack Técnica
## 3. Serviços Externos
## 4. Padrões de Design
## 5. Princípios de Design de Software
## 6. Estrutura do Projeto
## 7. Code Health
## 8. Error Handling
## 9. Observabilidade
## 10. Segurança
## 11. Acessibilidade (se aplicável)
## 12. Matriz Consolidada de Achados
## 13. Roadmap de Remediação
## 14. Conclusão
```

Verifique:
- **Ordem**: As seções estão na sequência numérica correta? Se alguma seção ficou fora de ordem (ex: seção 9 aparecendo depois da 10), mova-a para a posição correta com `strReplace`.
- **Duplicatas**: Alguma seção aparece mais de uma vez? Subagentes diferentes podem ter gerado seções com mesmo número (ex: dois `## 7. Code Health`). Se houver duplicatas, unifique-as mantendo o conteúdo de ambas sob um único título.
- **Seções ausentes**: Alguma seção obrigatória (1-10, 12-14) está faltando? Se sim, adicione-a vazia com um placeholder para preencher no passo seguinte.
- **Conteúdo fora de seção**: Há tabelas ou texto solto entre seções que não pertencem a nenhuma? Mova para a seção correta.
- **Títulos com sufixo de módulo**: Subagentes geram títulos como `## 7. Code Health — Controllers`. Se houver múltiplos (um por subagente), unifique sob `## 7. Code Health` e mantenha subtítulos como `### Controllers`, `### Services`, etc.

Se a validação encontrar problemas, corrija-os antes de prosseguir. Use `strReplace` para mover seções — operações pontuais, sem reescrever o documento inteiro.

**Passo 5b — Validação de tabelas**: Verifique integridade das tabelas markdown:

1. **Tabela 5.2 não pode estar vazia**: A tabela de violações deve ter pelo menos uma linha de dados após o header. Se estiver vazia, as violações dos subagentes não foram consolidadas — volte ao Passo 3b.
2. **Sem tabelas de violação órfãs**: Busque `| N | PRINCIPLE |` ou `| N | PRINCIPLE |` no documento. Se existir fora da seção 5.2, são resíduos dos subagentes — remova o header e mova as linhas para a tabela 5.2.
3. **Toda tabela com header deve ter dados**: Busque padrões de `|---|` seguidos imediatamente por linha vazia ou `---`. Isso indica tabela com header mas sem linhas de dados — preencha ou remova.

**Passo 6 — Revisão leve**: Leia o relatório **por seções** (não tudo de uma vez) e faça ajustes pontuais:
- Remova comentários HTML (`<!-- -->`) se desejar relatório limpo
- Verifique se a formatação markdown está consistente
- Ajuste numeração sequencial nas tabelas se necessário

**Passo 7 — Limpe**:
```bash
rm -rf reports/.parts/
```

## Formato do Relatório

Salvo em `reports/code-review-report-YYYY-MM-DD-HHmm.md`. Crie `reports/` se não existir.

### Template de Referência

O template completo das seções está descrito acima na Fase 1 (header) e Fase 2 (seções dos subagentes). As seções do relatório final são:

1. Resumo Executivo (métricas quantitativas + visão geral)
2. Stack Técnica (linguagem, dependências, infra)
3. Serviços Externos (integrações, autenticação, resiliência)
4. Padrões de Design (identificados + avaliação)
5. Princípios de Design (SOLID, DRY, KISS, YAGNI + violações)
6. Estrutura do Projeto (árvore + descrição)
7. Code Health (débito técnico, complexidade, testes, performance)
8. Error Handling e Resiliência (tratamento de erros, retry, timeout)
9. Observabilidade (logging, tracing, métricas)
10. Segurança (secrets, OWASP, CVEs, validação de API, configuração)
11. Acessibilidade WCAG (condicional — só para frontend/mobile)
12. Matriz Consolidada de Achados (todos os achados ordenados por severidade)
13. Roadmap de Remediação (4 fases: imediato, curto, médio, longo prazo)
14. Conclusão

**Legenda de severidade usada em todo o relatório:**
- 🔴 **Crítico** — Risco imediato. Corrigir antes de qualquer deploy.
- 🟠 **Alto** — Risco significativo. Corrigir no próximo sprint.
- 🟡 **Médio** — Melhoria importante. Planejar para os próximos 30 dias.
- 🔵 **Baixo** — Melhoria desejável. Backlog de qualidade.

## Regras de Conduta

- Seja específico. Cada achado deve apontar arquivo e linha. "O código tem problemas de segurança" não é um achado.
- Não invente problemas. Se o código está bom, diga.
- Adapte-se à linguagem e framework do projeto.
- Priorize por impacto real.
- O relatório deve cobrir todo o código-fonte. Subagentes geram seções prontas em `reports/.parts/`, montagem é por `cat`, agente principal só preenche PLACEHOLDERs e faz revisão leve.
- Seções condicionais (WCAG) só para projetos com frontend/mobile.
- Cite resultados de ferramentas de análise estática como evidência objetiva.
