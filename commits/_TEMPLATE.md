# Arquivo de commit — modelo

Este arquivo descreve UM commit (e, opcionalmente, o PR que o acompanha). O
comando `uv run commit` o consome e executa o fluxo git.

Nomeie cada arquivo como `<N>-<nome>.md` (ex.: `0-setup.md`, `1-fix.md`). Sem
argumento, `uv run commit` usa SEMPRE o de maior `N`. Ao concluir com sucesso, o
arquivo e removido (use `--keep` para preservar).

Formato: seções delimitadas por marcadores `>>> NOME` ... `<<<`. Tudo fora de
uma seção conhecida é ignorado (pode escrever notas livremente, como aqui).

Seções reconhecidas:

- `COMMIT`   (obrigatória) — a mensagem completa do commit (título + corpo).
- `FILES`    (opcional)    — uma linha por caminho a versionar (`git add`).
                             Se ausente ou vazia, versiona tudo (`git add -A`).
- `CHANGELOG`(opcional)    — texto de referência da entrada de CHANGELOG.
                             NÃO é aplicado automaticamente; é só documentação.
- `PR`       (opcional)    — título na 1ª linha, descrição no resto.
                             Usada SÓ quando você roda com `--pr`. Sem `--pr`, o
                             fluxo é apenas add + commit + push.

>>> COMMIT
tipo(escopo): descrição curta em até 72 caracteres

Corpo opcional explicando o PORQUÊ da mudança, em linhas de até ~72 colunas.

BREAKING CHANGE: descreva aqui se houver quebra de compatibilidade.
<<<

>>> FILES
<<<

>>> CHANGELOG
### Added

- Entrada concisa orientada ao impacto para quem consome o software.
<<<

>>> PR
tipo(escopo): título do PR

## Resumo
- O que mudou e por quê.

## Como testar
- Passos de verificação.

## Notas
- Riscos, trade-offs, itens bloqueados.
<<<
