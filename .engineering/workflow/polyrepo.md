# Multi-repository products (hub + code repositories)

Select the polyrepo profile when one product spans several repositories. The principal then
manages the whole product from a hub, and each code repository keeps its own history, CI/CD
and release cadence.

## Hub repository
A repository with no application code that holds what is shared across the product:
requirements and stories, ADRs, specs and plans, sprint records, runbooks, the
install registry, the usability reports and decision records, and the map of repositories.
It is usually private (runbooks and diagrams can contain real infrastructure data).
The single GitHub Project groups issues from the hub and every code repository.

Suggested layout (adapt names):
```
README.md                 how work flows; links to repos and the Project
docs/README.md            index
docs/repositories.md      the map: repo, origin, what it publishes, CI/CD, owners
docs/requirements/        epics and stories
docs/architecture/adr/    decisions (templates/decision.md)
docs/superpowers/ or docs/specs, docs/plans   spec and plan per large change
docs/sprints/             sprint records, board audits
docs/operations/          runbooks, registro-instalacoes.md
docs/design/              contracts, personas, usability, decisions
.github/ISSUE_TEMPLATE/   requirement, task, bug
```

## Flow
1. Requirement/story is an issue in the hub with the outcome, criteria and BR-ids.
2. For each affected repository the principal opens a task issue in that repository, linked as
   a sub-issue or by `<owner>/<hub>#N`, and adds it to the Project.
3. Contracts first: shared schemas/types/packages are changed and released before consumers;
   consumers adopt via version bump. Contract-drift tests live in the consuming repo and the
   producing repo (compare against the published contract).
4. Each repository's PR carries the evidence for its task. The hub story is `completed` only
   when every linked task is verified and the cross-repository behavior is proven (an
   integration or end-to-end check that runs across the pieces).
5. Release/deploy order follows dependencies (packages -> services -> web -> infra values) and
   is written in the story. Rollback is per repository plus the desired-state record.

## Cross-repository rules
- One owner per shared artifact (package, schema, desired-state file, design tokens).
- A change that touches several repositories is staffed as parallel tasks with disjoint scopes
  plus one integration owner; never one agent editing many repositories without a plan.
- Every repository carries the same engineering bootstrap (`init` per repository with the
  same profiles) so specialists behave the same everywhere; `sync` keeps them aligned.
  A repository without the bootstrap is treated as unmanaged: read-only for agents until
  initialized.
- Secrets, tokens and environment credentials are documented (names, scopes, where stored),
  never recorded. Environments do not share production credentials with lower environments.
- Production mutations (deploy, migration, DNS, credentials, destructive operations) require
  the explicit authorization defined in policies/safety.md in each repository's context.
- Document the activation order (registries, tokens, protections, first release) once in
  docs/repositories.md; the principal verifies it with a checklist, not by assumption.
