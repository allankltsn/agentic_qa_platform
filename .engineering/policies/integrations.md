# Provider and integration capability contract

Core knowledge has no proprietary model/tool syntax. Adapters translate discovery,
invocation, tool permissions and packaging; record provider/version and verification.
Files readable as knowledge do not prove native agent registration. If delegation
is absent, use separately verified independent specialist sessions or report
incompatibility; principal never assumes implementation or review. Reduced mode
needs explicit user decision and is not independent parity.

## Dependency inventory
Each integration records source, observed version or not verified, necessity,
configuration location, capabilities and status: verified / absent / incompatible /
not verified. Do not auto-install globally, enable plugins or extend permissions.
Check only safe bounded version/availability probes authorized by environment.

- RTK: explicit shell command proxy. Prefix shell commands with rtk when configured.
  Use rtk proxy for unsupported tools; PowerShell cmdlets require rtk proxy powershell
  -NoProfile -Command with correct quoting. No Codex automatic rewriting is presumed.
  If missing, report integration gap; use authorized native commands only if the
  applicable environment permits. Never run unsafe interpolation or secret arguments.
- Serena: source has project_name, encoding utf-8, empty language_servers, workspace
  '.', gitignore handling, ignore paths, read_only false, tool/API selections and
  modes. Select language/backend/workspace explicitly; global LSP/JetBrains and
  tool/REPL settings may differ. Empty language_servers is not proof of a working LSP.
  Activation commands require explicit project trust and are not copied/executed.
  Do not copy memories, caches, personal global configs or enlarge workspace silently.
- Superpowers: preferred phase engine when installed/compatible. Preserve
  brainstorming, writing-plans, executing-plans/subagent-driven-development,
  verification-before-completion, requesting-code-review/receiving-code-review.
  Core defines responsibilities/artifacts; does not implement another engine.
  Without it use workflow's explicit manual equivalent and disclose automation gaps.
  Do not copy or reinterpret private .superpowers/sdd state before inspecting its
  producer/schema; portable handoff is independent of provider-private state.
- Voltagent: observed enabled packs core-dev, infra, lang, qa-sec, data-ai, dev-exp,
  biz and research at voltagent-subagents. Enabled settings do not prove installation,
  version, discovery or capability. Optional integration, no silent dependency or
  copying of marketplace artifacts/personal settings.
- GitHub Projects: project manager when the github-projects profile is selected. Use
  the workflow/github-projects.md contract; detect gh (project/repo scopes) or GitHub MCP
  Projects support, never request broader scopes or store tokens. Setup scripts only
  create fields/labels; built-in Status automations are disabled by the principal in
  the UI. CLI success does not prove board rendering or disabled automations.
  Kanban Markdown (VSCode) is retired; existing cards import via the explicit mapping.
- draw.io: optional hediet.vscode-drawio extension or compatible viewer. XML generation
  and parsing differ from actual rendering. Do not install/assume viewer.
- Operational tools: kubectl/helm/istioctl/linkerd/aws/gh/argocd/docker, scanners
  Checkov/Trivy/tfsec/terrascan/Hadolint/Dive/Infracost and cloud CLIs are selected
  by task/profile, not mandatory global requirements. Respect source role limits.

Claude source local settings allowed selected gh/git commands and worktree baseRef
head; these are personal operational state, not reusable permission policy.
Claude plugin root components differ from project .claude components. Codex native
agent/skill formats must be verified for target version; do not reuse Claude tool
frontmatter or promise slash commands identically. Model tiers are logical (policies/models.md);
adapters render a model or reasoning effort per role from template.json, the principal may
override per dispatch, and a field in a generated file never proves the runtime honored it. Never claim textual restrictions are enforced merely
because generated definitions contain them.
