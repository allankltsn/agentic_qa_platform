# Serena

Copie project.yml para .serena/project.yml no projeto e escolha language_servers conforme suas linguagens. Mescle claude.mcp.json em .mcp.json ou codex.toml na configuração MCP do Codex, preservando servidores existentes. Execute o provedor a partir do projeto para --project-from-cwd localizar sua raiz.

Pré-requisito: executável serena instalado e disponível no PATH. O comando e as opções foram confirmados com serena start-mcp-server --help em 2026-10-08. Nenhuma instalação ou configuração global é feita pelo template. O contexto ide-assistant deve existir na sua instalação; confirme os contextos antes de habilitar. Configuração preparada não comprova conexão MCP nem indexação.

Não copie caches, memórias privadas ou configuração global de outra máquina.
