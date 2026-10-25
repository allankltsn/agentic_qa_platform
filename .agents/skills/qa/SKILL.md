---
name: qa
description: "Run an adversarial QA pass on the current changes without going through the full feature workflow."
---

The main session ALWAYS orchestrates: consult and delegate implementation and specialized judgments. Separate expertise from task function. Never approve your own work. Independent QA, conformity review, technical review and security must report explicitly on the same reproducible snapshot. Return stable finding IDs to the author; require correction evidence and independent confirmation, and revalidate affected gates after every delta. Silence, timeout, disagreement and exhausted budget never approve. Human acceptance is separate. Without delegation, coordinate verified independent sessions or report blocked; the main session never substitutes for specialists. Read .engineering/workflow/ and .engineering/policies/ explicitly relative to the project root before work. Respect actual permissions; textual scope is not a filesystem sandbox. Staff specialists per workflow/staffing.md, choose the model tier per dispatch per policies/models.md and record both in the brief; hold plans and deliveries to policies/quality-principles.md; install nothing without policies/installations.md, and record every installation of any kind (plugin, agent, skill, MCP, package, tool, image, extension) in docs/operations/registro-instalacoes.md in the same turn. Start in the consuming project root. Before any task, explicitly read .engineering/project.json, .engineering/catalog.json, and each .engineering/profiles/<id>.json selected by project.json, then the relevant role/action contracts. Do not rely on inherited context or automatic discovery. For plugin use, the consuming project must have the shared .engineering tree installed or its verified location explicitly supplied; missing project context blocks execution.

# Action: qa
Intent/scope: Adversarial functional, API-contract and regression review. Inspect boundaries, concurrency, downstream failures and relevant regression suite. Security owns systematic IDOR; report incidental access failures. Without arguments inspect complete change snapshot.
Responsible specialist: qa; principal routes, questions and consolidates.
Input: explicit focus/arguments, criteria, project profiles, environment, permitted
paths and snapshot/base; no proprietary argument variable in common knowledge.

Change review includes staged, unstaged and relevant untracked file contents/hashes.
Plain git diff is insufficient. On a clean branch compare HEAD with merge-base of an
explicitly configured existing base. Missing base requires definition; never assume main.
Record snapshot, base, input scope and exclusions before dispatch.

Use a qualified independent instance for validation, with scoped brief. Native
delegation or separately verified independent sessions is required; missing capability
is an incompatibility, never fallback implementation/review by principal.
Action text grants no permission, tool or sandbox.

Return faithful findings grouped by common severity with stable IDs, author
attribution, snapshot, evidence, coverage limitations and next owner. Do not replace
original findings with a misleading summary. Corrections return to the implementing
specialist and finding authors independently confirm resolution. Common policies
and workflow apply to standalone invocations too.
