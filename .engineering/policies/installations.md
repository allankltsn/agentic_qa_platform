# Installing agents, plugins, skills and tools

**Mandatory rule: every installation is recorded in `docs/operations/registro-instalacoes.md`
(relative to the project root; the hub repository in a polyrepo product).** This covers any
action that adds software or access to the machine or project, by anyone (principal,
specialist, script or the user at the principal's request): plugins and marketplaces, agents,
skills, MCP servers, global or project packages (npm, pip, winget, brew, cargo...), CLI
tools, Docker images pulled or built, VS Code extensions, generated tokens/connections, and
configuration written outside the repository. Add the row in the same turn, before reporting
the task done; an unrecorded installation is a defect the reviewer must flag. If the file does
not exist, create it from templates/registro-instalacoes.md.

Nothing is installed, enabled or granted globally by this template. When a task would benefit
from an external agent, plugin, skill, MCP server or tool, the principal proposes it; the user
approves; the principal records it. No specialist installs anything on its own initiative.

## Selection criteria (all must hold; write the evidence in the registry)
1. **Need**: the capability is missing from the roles, actions and already-installed
   components, and a gap is documented (workflow/staffing.md). Do not install to "have it".
2. **Provenance**: published by the platform vendor or a maintained, identifiable
   organization; source repository is public and readable before install.
3. **Adoption**: among the most used for its purpose (installs/stars/downloads checked on the
   day, with the number and date recorded) and actively maintained (recent commits/releases).
4. **Security review**: read the manifest, agent/skill prompts, hooks, MCP server commands and
   scripts before installing. Reject or isolate anything that executes remote code on
   install, requests broad credentials, disables permission prompts, phones home with
   project content, or obfuscates behavior. Pin a version or commit where the tool allows.
5. **Scope**: install at project scope when possible; user/global scope needs explicit
   approval. Grant the narrowest permissions; never add bypass permissions.
6. **Reversibility**: record the uninstall command and any file it changes.

Prefer, in order: the provider's official marketplace; the maintained catalogs listed in
integrations/plugins/curated.json; then individual repositories after manual review.
Popularity alone is not a safety proof.

## Procedure
1. Principal drafts a proposal: need, candidate, criteria evidence, install command,
   scope, permissions, rollback. Security (and devsecops-infra for tools that run code)
   reviews it independently.
2. User approves explicitly. Silence or a generic go-ahead is not approval.
3. Principal (or an authorized specialist) installs, verifies discovery with a bounded
   probe, and records the result in the registry (templates/registro-instalacoes.md): what, source, version
   or commit, scope, date, approver, files changed, how to remove, verification result.
4. A tool recorded as installed but not verified stays `not verified` until a probe proves it.

## Registry
Keep one registry per project, always at docs/operations/registro-instalacoes.md. Also record
attempted installs that did not install anything and temporary files created outside the
repository. The registry feeds the project documentation and postmortems.
