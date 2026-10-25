<!--
Issue title: [S-NNN] <verb + outcome>   (epic: [E-NN] <outcome>)
Project fields (not in the body): Status=open, Priority, Type=story, Estimate, Sprint (optional), Due date (optional).
Labels: type:story, epic:E-NN, repo:<name> as needed. Tasks are sub-issues (templates/issue.md).
Hub/polyrepo: the story lives in the hub; tasks live in the repositories that change.
-->
# [S-NNN] <verb + outcome>
Epic: <E-NN / #issue> | Release: <milestone> | Priority: <value> (method: <RICE/WSJF/MoSCoW>, inputs: <...>) | Estimate: <points/size>

## Narrative
As a <persona link> I want <goal> so that <value>.
Problem / job to be done: <in the user's words; no solution here>
Success metric: <how we will know it worked>

## Business rules
- <BR-NNN: rule, source> (must not be broken by usability, copy or implementation decisions)

## Acceptance criteria
- [ ] AC1 Given <context> When <action> Then <observable result> -- proof: <test/check>
- [ ] AC2 (negative / permission / boundary / failure) ...

## Flow and states
Flow: <link to diagram / screen specs>
Screens: <list>. States per screen: default, empty, loading, error, success, partial, no-permission.

## Non-functional
Accessibility: WCAG 2.2 AA <specifics> | Performance: <budget> | Security/privacy: <data touched, purpose, basis, retention>
Reliability: <idempotence, retries, rollback> | Observability: <logs/metrics/alerts> | Scale: <expectation>

## Assets and links
| Asset | Link | Owner | Status |
|---|---|---|---|
| Design / copy deck / brand asset / API contract / ADR / research | <url or path> | <function> | draft/approved |

## Metadata
Components/repositories: <...> | Depends on / blocks: <#issues> | Risks: <...> | Analytics events: <...>
Feature flag: <name/none> | Regulatory tags: <e.g. personal-data, health, payment, minors>

## Out of scope
- <...>

## Open questions / assumptions
- [OPEN QUESTION] <...> -- recommended answer: <...> -- owner/date: <...>
- [ASSUMPTION] <...> -- validated by: <...>

## Definition of Ready
- [ ] Persona, goal, value; problem separate from solution
- [ ] Criteria testable incl. negative and failure paths
- [ ] Business rules cited; no conflict
- [ ] Design/flow/copy inputs available or not needed
- [ ] Dependencies and repositories listed; contracts agreed
- [ ] Non-functional, privacy and security needs identified (privacy-compliance consulted if applicable)
- [ ] Estimated; fits one sprint
- [ ] Open questions answered or recorded as assumptions
- [ ] Priority set; staffing and tiers proposed

## Definition of Done
- [ ] Every criterion proven on the final snapshot
- [ ] Commit/PR in the owning repository; tests executed with output
- [ ] Independent QA, compliance/technical review, security; no pending Critical/High
- [ ] Privacy-compliance verdict (if applicable); usability round and decisions recorded (if user-facing)
- [ ] Accessibility checks executed (UI)
- [ ] Idempotence and failure paths exercised; rollback known
- [ ] Observability in place (runtime)
- [ ] Docs, ADR/decisions, rules registry, runbooks updated
- [ ] No secrets or personal data in code, issues, evidence
- [ ] Principal re-ran an evidence command; Status by authority rules
- [ ] Human acceptance recorded

## Tasks (sub-issues)
| Task issue | Function | Model tier | Gate / dependency |
|---|---|---|---|

## Evidence and acceptance
Evidence: <links> | Acceptance: <pending or user/date/scope/decision>
