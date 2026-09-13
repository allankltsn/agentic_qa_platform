# Kiro Steering Files

Repositório padronizado de steering files do Kiro para uso global pelo time. Os steerings fornecem contexto persistente ao Kiro durante sessões de desenvolvimento, cobrindo padrões de código, AWS serverless, IA Generativa, frameworks de agentes, configuração e testes.

## Como Usar

### Clonando o Repositório

Clone este repositório e a pasta `.kiro/steering/` será reconhecida automaticamente pelo Kiro:

```bash
git clone <url-do-repositorio>
```

Os steerings são carregados automaticamente conforme o modo de inclusão configurado no frontmatter de cada arquivo.

### Modos de Inclusão

Cada steering possui um modo de inclusão definido no frontmatter YAML:

- **`always`** — Carregado automaticamente em toda sessão do Kiro. Usado para padrões universais que se aplicam a qualquer contexto de desenvolvimento.
- **`fileMatch`** — Carregado automaticamente quando o Kiro lê um arquivo que corresponde ao padrão glob definido em `fileMatchPattern`. Usado para contexto específico de linguagem ou tipo de arquivo.
- **`manual`** — Carregado apenas quando referenciado explicitamente via `#` no chat do Kiro. Usado para frameworks especializados de uso sob demanda.

### Referenciando Steerings Manuais

Para carregar um steering manual durante uma sessão, digite `#` no chat do Kiro seguido do nome do arquivo:

```
# 07-agentes-agno
# 08-agentes-strands
# 09-agentes-langchain
```

Isso injeta o conteúdo do steering no contexto da sessão atual, sem afetar outras sessões.

## Inventário de Steerings

| # | Arquivo | Inclusão | Padrão `fileMatchPattern` | Descrição |
|---|---------|----------|---------------------------|-----------|
| 01 | `01-padroes-gerais.md` | `always` | — | Padrões gerais de código: nomenclatura, commits, documentação, segurança, logging, observabilidade |
| 02 | `02-well-architected.md` | `always` | — | AWS Well-Architected Framework: checklist acionável dos 6 pilares |
| 03 | `03-sam-python.md` | `fileMatch` | `**/*.py` | Backend serverless com AWS SAM e Python: handlers Lambda, Powertools, boto3, testes pytest |
| 04 | `04-sam-nodejs.md` | `fileMatch` | `**/*.{ts,js}` | Backend serverless com AWS SAM e Node.js/TypeScript: handlers Lambda, Powertools TS, SDK v3, testes Jest/Vitest |
| 05 | `05-sam-templates.md` | `fileMatch` | `**/template.{yaml,yml}` | Templates AWS SAM: estrutura, Globals, IAM, API Gateway, criptografia, VPC |
| 06 | `06-bedrock-genai.md` | `fileMatch` | `**/*.py` | IA Generativa com AWS Bedrock: Converse API, engenharia de prompts, RAG, guardrails |
| 07 | `07-agentes-agno.md` | `manual` | — | Framework Agno: agentes, ferramentas, orquestração multi-agente, integração Bedrock |
| 08 | `08-agentes-strands.md` | `manual` | — | Framework Strands Agents: agentes, ferramentas, integração nativa Bedrock |
| 09 | `09-agentes-langchain.md` | `manual` | — | LangChain e LangGraph: chains, agents, tools, grafos de estado, integração Bedrock |
| 10 | `10-configuracao-iac.md` | `fileMatch` | `**/Dockerfile,**/samconfig.{toml,yaml},**/.github/workflows/*.yml,**/requirements.txt,**/pyproject.toml,**/package.json` | Configuração e IaC: Dockerfile, samconfig, GitHub Actions, dependências Python/Node.js |
| 11 | `11-testes-qualidade.md` | `fileMatch` | `**/test_*.py,**/*_test.py,**/*.test.{ts,js},**/*.spec.{ts,js}` | Testes e qualidade: pytest, Jest/Vitest, estratégias de teste AWS, cobertura |
| 12 | `12-organizacao-dataclasses.md` | `fileMatch` | `**/*.py` | Organização de dataclasses por papel arquitetural: DTO, entidade, objeto-valor, schema; regra de decisão finalidade→pasta e `dataclass` vs Pydantic |
| 13 | `13-execucao-terminal.md` | `always` | — | Disciplina operacional de execução no terminal: sem loops/gambiarra, validar shell/comando, um comando por vez, git explícito, verificação honesta |
| 14 | `14-nomenclatura-specs.md` | `always` | — | Nomenclatura de specs com prefixo ordinal `<N>-<nome>` para ordenar a pasta e tornar o fluxo de execução explícito |

## Contexto por Cenário de Desenvolvimento

| Cenário | Steerings Ativos |
|---------|-----------------|
| Editando handler Python Lambda | 01, 02, 03, 12 |
| Editando handler Python com Bedrock | 01, 02, 03, 06, 12 |
| Editando handler Node.js Lambda | 01, 02, 04 |
| Editando template SAM | 01, 02, 05 |
| Escrevendo testes Python | 01, 02, 03, 11 |
| Escrevendo testes Node.js | 01, 02, 04, 11 |
| Editando Dockerfile ou CI/CD | 01, 02, 10 |
| Desenvolvendo agente com Agno | 01, 02, 03, 06 + manual 07 |
| Desenvolvendo agente com Strands | 01, 02, 03, 06 + manual 08 |
| Desenvolvendo com LangChain/LangGraph | 01, 02, 03, 06 + manual 09 |

## Estrutura do Frontmatter

Cada steering segue o formato:

```yaml
---
inclusion: always | fileMatch | manual
fileMatchPattern: "<glob_pattern>"  # obrigatório apenas para fileMatch
---
```

## Contribuindo

- Manter cada steering focado em um escopo único (responsabilidade única)
- Usar bullet points e regras acionáveis — evitar parágrafos longos
- Limitar cada arquivo a no máximo 250 linhas
- Usar referências cruzadas `#[[file:.kiro/steering/<arquivo>]]` em vez de duplicar conteúdo
- Atualizar este README ao adicionar ou modificar steerings
