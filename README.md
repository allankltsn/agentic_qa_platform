# Prisma QA

Protótipo privado para organizar avaliações de API, frontend e agentes.

## Executar

```sh
npm run build
python3 -m http.server 4173 --directory dist
```

Os dados são gravados no `localStorage` do navegador. O menu lateral oferece exportação e importação de backup JSON. Não há análise automática de código ou sincronização entre dispositivos nesta versão.
