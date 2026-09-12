---
inclusion: always
---

# Execução no Terminal — Disciplina Operacional

Regras obrigatórias para executar comandos no terminal. Aplicam-se a qualquer
contexto de desenvolvimento. Para convenções gerais de código, consulte
#[[file:.kiro/steering/01-padroes-gerais.md]].

## Princípio Inegociável — Sem Loops, Sem Gambiarra

- Quando um comando falha ou não retorna a saída esperada, **NUNCA** entre em
  loop reexecutando variações do mesmo comando.
- Não invente contornos improvisados (gambiarra) que comprometem a evolução e a
  sustentação do projeto.
- Após **uma** falha inesperada, **PARE**. Diagnostique a causa antes de agir de
  novo. Repetir a mesma tentativa esperando resultado diferente é proibido.

## Antes de Executar Qualquer Comando

- **Valide o terminal padrão configurado** (ex.: `bash`/`wsl`, `zsh`,
  PowerShell, `cmd`). Cada shell tem sintaxe e comportamento próprios (paths,
  separadores, aspas, encadeamento). Use o formato correto para o shell real.
  - Em WSL, use paths POSIX (`/mnt/e/...`), nunca paths Windows (`e:\...`).
- **Valide se o comando é válido e/ou necessário** antes de rodá-lo:
  - `cd`: confirme o diretório atual primeiro (necessidade e caminho corretos).
  - Ferramentas externas (`sam`, `gh`, `uv`, `docker`, etc.): verifique a versão
    / disponibilidade (`<cmd> --version`) antes de assumir que estão instaladas.

## Como Executar

- **Um comando por vez.** Não encadeie múltiplos comandos aninhados (`&&`, `;`,
  `|` em sequências longas, subshells) só para "economizar chamadas". Comandos
  individuais dão melhor controle, leitura de saída e diagnóstico de falha.
- Execute, **leia a saída**, confirme o resultado e só então prossiga para o
  próximo passo.

## Quando um Erro Acontecer

- Se você decidir tentar o comando de outra maneira, **QUESTIONE O USUÁRIO ANTES**
  de tentar. Na mensagem, inclua obrigatoriamente:
  1. **O problema** — o que falhou e o que a saída indicou.
  2. **O comando usado** — exatamente o que foi executado.
  3. **Soluções viáveis** — as alternativas que você considera, com trade-offs.
- Só prossiga com a alternativa após a orientação do usuário. Não decida sozinho
  mudar de abordagem em cima de uma falha.

## Operações de Git — Explícito Sobre Implícito

- Em `git push`, **sempre nomeie o remote e a branch** explicitamente:
  `git push origin <branch>`. Nunca use `git push` "pelado" em operações
  sensíveis — o destino implícito (upstream) não é óbvio para quem lê e pode
  gerar dúvida legítima sobre "isso vai para a main?".
- **Nunca** empurre para `main`/`master` diretamente, salvo pedido explícito do
  usuário. Trabalhe sempre na branch de feature.
- Antes de `push`, confirme os commits locais com `git log --oneline -N` e valide
  que HEAD contém o que se espera. Não empurre sem ter lido o log.
- `git reset` (mesmo sem `--hard`) desfaz o *staging* — se o objetivo é apenas
  re-adicionar após um hook reformatar arquivos, use `git add` de novo, **não**
  `git reset`.

## Verificação Honesta

- Exit code `0` (ou "sem erro") **não é prova** de sucesso. Valide o resultado
  real contra o objetivo (arquivo criado, commit no log, branch atualizada).
- Se não conseguir confirmar um resultado (ex.: terminal não retornou saída),
  **diga isso explicitamente** em vez de assumir sucesso ou fracasso.
