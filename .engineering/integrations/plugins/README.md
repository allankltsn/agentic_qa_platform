# Plugins e agentes externos (curadoria)

`curated.json` lista o que vale considerar para cobrir UI/UX, marca, marketing, produto e
frontend, com a origem, a popularidade verificada na data (estrelas no GitHub), o comando de
instalação e a quem cada item atende. **Nada é instalado pelo template.**

Regras (ver `core/policies/installations.md`):

1. Só proponha instalar quando houver uma lacuna documentada nos papéis e ações existentes.
2. Prefira o marketplace oficial da Anthropic e catálogos mantidos e populares; popularidade não prova segurança.
3. Antes de instalar, leia manifesto, prompts dos agentes, hooks, comandos de servidores MCP e scripts.
   Rejeite o que executa código remoto na instalação, pede credenciais amplas, desativa prompts de
   permissão ou envia conteúdo do projeto para fora.
4. Instale em escopo de projeto quando possível, fixe versão/commit quando a ferramenta permitir e
   registre em `docs/operations/registro-instalacoes.md`, modelo em `templates/registro-instalacoes.md` (quem aprovou, o que mudou, como remover).
5. A aprovação do usuário é explícita. Silêncio não é aprovação.

Os papéis canônicos do template funcionam sem nenhum plugin; os agentes de catálogo complementam
(por exemplo `ui-ux-tester` ou `accessibility-tester` para testes de interface), nunca substituem um
contrato canônico sem uma decisão registrada.
