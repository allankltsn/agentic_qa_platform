# Prisma QA · web

Recriação em React do protótipo do Prisma QA, na mesma stack do aura-web: React 18, Vite, Tailwind 3 com tokens semânticos,
react-aria-components (só dentro de `src/components/ui`), react-hook-form + zod, react-router 7, TanStack Query e Vitest.

**Fase atual: 100% mockado.** Não há API. Os dados ficam no `localStorage` (`prismaqa.web.v1`) e os agentes especialistas são
simulados. Quando as telas forem aprovadas, só `src/mock/` é trocado por chamadas HTTP.

```bash
pnpm install
pnpm dev          # http://localhost:5174
pnpm test && pnpm lint && pnpm typecheck && pnpm check:ui
pnpm build
```

## Estrutura

```
src/
  brand/            # tokens (CSS), preset do Tailwind, logo e ícones
  components/ui/    # primitivas: botão, campos, diálogo, abas, badge... (único lugar com react-aria e tags cruas)
  domain/           # tipos, catálogo (checklists, categorias, agentes), schemas zod e seletores
  hooks/queries.ts  # TanStack Query sobre a API (hoje mock)
  mock/             # db (localStorage), api (assíncrona, com latência), runner (simulador de execuções de agentes)
  layouts/          # shell: sidebar de projetos, topo, backup
  pages/            # HomePage e project/* (visão geral, checklist, achados, agentes)
```

## Regras herdadas do aura-web

- Páginas não usam tags HTML cruas, cores hexadecimais, `style` inline nem cores não semânticas do Tailwind:
  use as primitivas de `components/ui` e os tokens (`pnpm check:ui` falha o build).
- `react-aria-components` e `@radix-ui/*` só são importados dentro de `components/ui`.
- Páginas carregadas sob demanda (`React.lazy`); sem source maps em produção.

## Agentes (simulação)

Cada categoria ativa do projeto tem um especialista (`domain/catalog.ts` → `AGENTS`). Ao executar, `mock/runner.ts` percorre as
verificações da categoria em passos `agent.act` / `agent.assert`, atualiza o checklist (`verifiedBy`) e **sugere** achados para o
que falhar (cerca de 1 em 4, determinístico pelo título). A pessoa aceita ou descarta cada sugestão; só o aceito vira achado.
A execução real (tester-army/e2e, Playwright, modelos) ainda não está ligada.

## Migrando do protótipo anterior

O backup JSON do protótipo (`prismaqa-v1`) é aceito em "Importar backup".
