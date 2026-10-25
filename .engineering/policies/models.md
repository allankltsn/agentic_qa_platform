# Model selection: the right capability for each dispatch

Goal: best quality per token. Use the cheapest tier that reliably does the job, escalate on
evidence, never on habit. Over-modelling (a top model for a mechanical task) and
under-modelling (a weak model on a judgment that gates a release) are both defects.

## Logical tiers
Core contracts name tiers, not products. template.json `model_tiers` maps each tier to the
provider's model and reasoning effort; adapters render it. Today: deep = Opus, standard =
Sonnet, light = Haiku (Codex: reasoning effort high / medium / low). If a model above deep
exists in the runtime, use it only with explicit user approval for a stated, critical reason.

| Tier | Use for | Do not use for |
|---|---|---|
| deep | Architecture with cross-cutting trade-offs; security and privacy judgment; production-impacting or irreversible decisions; root-cause of problems a lower tier failed twice; reconciling conflicting specialist verdicts | Formatting, routine implementation, simple reviews, summaries |
| standard (default) | Normal specialist work: implementation, design, copy, QA, code and technical review, diagnostics, planning inside an approved design | Trivial mechanics (waste); decisions the table sends to deep |
| light | Mechanical or low-context work: formatting LOG/issue/changelog from structured input, indexes, status summaries, renaming, simulated lay-user testing, obvious lookups | Anything that approves, gates, designs, secures or decides |

Each role in template.json has a default tier. The default is a starting point, not a rule.

## Per-dispatch decision (the principal records it in the brief)
Choose by these signals, in order; write `Model: <tier> - <one-line reason>`.
1. Blast radius: production, data loss, security, privacy, money, health -> at least standard,
   deep when the specialist is the gate or the decision is irreversible.
2. Novelty and ambiguity: a clear pattern in the repo -> standard or light; open design space,
   conflicting constraints, unfamiliar domain -> deep.
3. Context size: large cross-file reasoning favors standard/deep; small, structured input
   favors light.
4. Prior failure: same finding unresolved after two rounds -> next tier up, or a third
   independent specialist (workflow/engineering.md).
5. Cost of being wrong versus cost of the tier: a wrong light-tier format costs a retry; a
   wrong light-tier security verdict costs an incident.

## Escalate and de-escalate
- light -> standard: two failed attempts, ambiguity the brief cannot resolve, any need to judge.
- standard -> deep: the signals above, or a gate role (security, privacy-compliance,
  reviewer of a high-risk change) on a critical path, or contested verdicts.
- deep -> standard: after the hard decision is recorded, implementation and routine work go
  back down. A deep decision becomes a written spec/ADR that cheaper tiers execute.
- Record each change and the reason in the event log (`LOG ESCOLHA`).

## Gate independence and diversity
Independence is by instance, snapshot and function, never by tier alone. For high-risk
changes prefer validators on a different tier or provider than the author to reduce
correlated blind spots; never downgrade a gate below standard to save tokens.

## Token economy rules
- Give each dispatch paths and focused context, not full histories (brief template).
- One specialist per question; do not fan out to many specialists for a single-domain task.
- Parallelize only independent work with disjoint write scopes.
- Reuse validated evidence and spec/ADR decisions; do not re-derive them with a larger model.
- Use light-tier scribe for bookkeeping once the principal has decided the content.
- Prefer a short deep consultation (decision + rationale) followed by standard execution over
  deep execution of a whole task.
- Cap exploration: ask for a recommendation and at most three options.

## Project overrides
A project may change a role's tier (for example a regulated product raising reviewer to deep).
Record it in .engineering/project.json via `--tier role=tier` at init/sync so generated
agents and the manifest stay consistent; do not edit generated agent files by hand.
Overrides never lower a gate role below standard.

## Provider notes
Claude Code: the agent file's `model` is the default; the principal may override per dispatch.
Codex: reasoning effort is set per agent file; the concrete model is inherited from the
session. Support for these fields depends on the installed version and is verified per
environment; a field in a generated file is not proof that it was honored.
