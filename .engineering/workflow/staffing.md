# Staffing: choosing the right specialists, models and team shape

The principal's main job is to manage specialists so the final product is delivered with
quality and efficiency. Staffing is a decision made per task, recorded in the brief
(templates/staffing.md), not a fixed roster.

## 1. Understand before staffing
Identify: outcome, domain(s), actual stack and versions (from project.json, profiles and the
repository), risk (blast radius, data, money, health, law), phase, affected artifacts and
repositories, constraints (deadline, budget, permissions), and what already exists to reuse.
If any is unknown, ask the human or run a bounded read-only discovery first.

## 2. Select specialists
- Match task to the role whose contract covers the domain; read the role and the catalog
  descriptions. Filter out incompatible expertise (a Python role does not review a Go service).
- One specialist per question. Add another only for a different domain, a required
  independent gate, or a justified second opinion.
- Separate expertise from function: author, consultant, QA, compliance reviewer, technical
  reviewer, security, privacy, verifier. A specialist may author one task and review another,
  never their own delivery.
- Gaps: if no qualified role exists, record the gap and propose (a) adapting an existing role
  with a profile, (b) creating a new role in the template, or (c) an approved external agent
  (policies/installations.md). Never substitute a similar-sounding role silently.
- External catalogs (for example integrations/voltagent) can supplement roles, never replace
  a canonical contract without a recorded decision.

## 3. Standard team shapes
| Work | Author(s) | Consult | Independent gates |
|---|---|---|---|
| New product capability | product-owner -> ux-designer, ui-designer -> frontend-senior and/or backend/python | architect, brand-strategist, privacy-compliance | qa, reviewer, security, privacy-compliance, usability round for user-facing flows |
| Backend/API change | backend or python | architect, security | qa, reviewer, security |
| UI-only change | frontend-senior | ux-designer, ui-designer | qa (viewports, themes, a11y), reviewer, usability round if flow changed |
| Brand / marketing launch | brand-strategist, marketing | ui-designer, ux-designer | privacy-compliance (tracking, claims, consent), reviewer, brand audit |
| Infrastructure / platform | aws, kubernetes, docker, hosting, cicd, ingress, orchestration, deployment (as the stack requires) | cloud, finops, sre | devsecops-infra, security, sre by impact, qa probes |
| Incident | sre | domain role | reviewer (postmortem), qa regression |
| Architecture decision | architect | cloud, security, finops | reviewer, security; privacy-compliance if personal data |
| Backlog / requirement work | product-owner | architect (feasibility), qa (testability) | reviewer (traceability) |

The table is a starting point. Drop gates only with a recorded reason; "to save tokens" is
not one (policies/models.md).

## 4. Choose the model tier per dispatch
Apply policies/models.md and write `Model: <tier> - <reason>` for each dispatch. Defaults come
from the role; override by risk, ambiguity and prior failure.

## 5. Shape the work
- Slice into vertical tasks with a single owner each and disjoint write scopes. Shared files
  (lockfiles, migrations, root config, design tokens, shared contracts) have one owner.
- Run independent tasks in parallel; sequence dependent ones; put the cheapest validation
  first (static checks before long end-to-end runs).
- Give each dispatch the brief (templates/brief.md): objective, criteria, paths, snapshot,
  authorizations, expected evidence, tier. Pass paths and focused context, not histories.
- For many similar items (screens, endpoints, repositories) define a contract first, then fan
  out builders against it, then converge with a single integration owner.

## 6. Run, monitor, recover
- The issue on the board is the state: Status before action, evidence after, LOG events.
- No activity for ~10 minutes: inspect through authorized status, then retry once with a
  sharper brief, then replace the specialist or report blocked. Silence never approves.
- Failed or incomplete delivery: keep finding IDs, return to the same author with the delta;
  after two consecutive failures on the same finding change tier, add a third independent
  specialist, or request diagnosis.
- When context fills or a session restarts, a replacement resumes from the issue, brief,
  evidence and handoff files only.

## 7. Close
Principal verifies per workflow/engineering.md, records the postmortem facts (what worked,
what failed, which staffing or tier choices should change), updates the backlog, and hands
open risks and decisions to the human with a recommendation.
