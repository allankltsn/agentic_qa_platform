---
inclusion: always
---

# Nomenclatura de Specs — Prefixo Ordinal de Fluxo

Regra obrigatória para nomear specs em `.kiro/specs/`. O objetivo é manter a
pasta ordenada e tornar o **fluxo correto de execução** explícito na própria
listagem. Para convenções gerais de nomenclatura, consulte
#[[file:.kiro/steering/01-padroes-gerais.md]].

## Formato

- Toda spec nova nasce com o padrão: `<N>-<nome-kebab-case>`.
  - `<N>` — inteiro ordinal **sem zero à esquerda** (`0`, `1`, `2`, ... `10`, `11`),
    indicando a posição da spec no fluxo/ordem de execução do projeto.
  - `<nome-kebab-case>` — nome descritivo em `kebab-case`, como já é padrão.
  - Exemplos: `0-start-project`, `1-workflow-orchestrator-skeleton`,
    `2-durable-run-state-store`.
- A **primeira** spec do projeto usa `0-`. Cada spec subsequente incrementa `N`
  na ordem em que deve ser executada.

## Como Escolher o Número

- O número reflete **dependência e ordem de execução**, não a data de criação.
  Uma spec que só faz sentido após outra recebe número maior.
- Antes de criar, liste `.kiro/specs/` e identifique o maior `<N>` existente. A
  nova spec normalmente recebe `<N>+1`, salvo quando ela pertence a um ponto
  anterior do fluxo (nesse caso, ver "Inserir no Meio").
- Em caso de dúvida sobre a posição, **pergunte ao usuário** onde a spec se
  encaixa no fluxo antes de fixar o número.

## Inserir no Meio / Reordenar

- Renomear specs **já implementadas e verificadas** é operação de risco: os nomes
  costumam ser referenciados em `PROJECT.md`, ADRs, docs e marcadores
  `# Feature: <nome>` nos testes. Não renomeie em massa por conta própria.
- Se precisar inserir uma spec entre duas existentes, **proponha ao usuário** o
  plano de renumeração e só prossiga após aprovação, atualizando todas as
  referências cruzadas afetadas na mesma mudança.

## Verificação

- Após criar a pasta da spec, confirme que o nome segue `<N>-<nome>` e que `<N>`
  não colide com outra spec no mesmo fluxo.
- O nome da spec (o slug reconhecido pelo Kiro) é o próprio nome da pasta —
  garantir o prefixo no nome da pasta é suficiente.
