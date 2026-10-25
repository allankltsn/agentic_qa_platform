# User stories, requirements and board hygiene

Applies when the github-projects profile is selected (and is good practice otherwise).
Product-owner authors; the principal checks Definition of Ready before dispatch and
Definition of Done before verification. Human acceptance stays separate.

## Hierarchy
Initiative/Epic (outcome) -> Story (user-visible behavior, one sprint or less) -> Task
(specialist work item: design, implement, QA, review, security, privacy). Stories are
sub-issues of the epic; task issues are sub-issues of the story. Bugs and spikes use their own
type. Cross-repository work: the requirement lives in the hub repository when the project uses
the polyrepo profile; tasks live where the code lives and link back.

## Story contents (templates/user-story.md)
- **Title** `[S-NNN] <verb + outcome>`; **type** epic / story / bug / spike; **priority** and
  the method/inputs that produced it; **estimate**.
- **Narrative**: As a <persona> I want <goal> so that <value>. Persona links to
  templates/persona.md. Job-to-be-done and the problem, not the solution.
- **Business rules**: ids from the rules registry (BR-NNN) that apply and must not be broken.
- **Acceptance criteria**: Given/When/Then, each testable and mapped to a test or check.
  Include negative paths, permissions, boundaries and failure behavior.
- **Flow**: link to flow diagram or screen specs; list screens and all states.
- **Non-functional**: performance, accessibility (WCAG 2.2 AA), security, privacy and
  retention, observability, compatibility, scalability, resilience and idempotence needs.
- **Assets and links**: designs, copy deck, brand assets, API contracts, ADRs, research,
  prior issues, external references; each with owner and status.
- **Metadata**: epic, release/milestone, labels, components/repositories, dependencies
  (blocks/blocked-by), risks, analytics events, feature flag, data touched, regulatory tags.
- **Out of scope** and **open questions** (with a recommended answer).
- **DoR** and **DoD** checklists (below), ticked by the person who verifies them.
- **Tasks** (sub-issues) with owner function, model tier and gates.
- **Evidence** links and **acceptance** record.

## INVEST check
Independent (or dependencies explicit), Negotiable, Valuable to a user or the business,
Estimable, Small enough for one sprint, Testable. A story failing a letter is split, reworked
or marked blocked with the reason; never dispatched as is.

## Definition of Ready (default; projects may extend)
- [ ] Persona, goal and value stated; problem separated from solution
- [ ] Acceptance criteria testable, with negative and failure paths
- [ ] Applicable business rules cited; no unresolved rule conflict
- [ ] Design/flow/copy inputs available or explicitly not needed
- [ ] Dependencies and affected repositories listed; contracts agreed
- [ ] Non-functional, privacy and security needs identified; privacy-compliance consulted
      when personal or health data, consent, payment or tracking is involved
- [ ] Estimated and small enough for one sprint
- [ ] Open questions answered or recorded as assumptions with an owner and date
- [ ] Priority set; staffing and model tiers proposed (templates/staffing.md)

## Definition of Done (default; projects may extend)
- [ ] Every acceptance criterion satisfied with evidence on the final snapshot
- [ ] Commit/PR exists in the owning repository; tests executed with recorded output
- [ ] Independent QA, compliance and technical review, and security verdicts with no pending
      Critical/High findings
- [ ] Privacy-compliance verdict where applicable; usability round done for user-facing flows
      with decisions recorded
- [ ] Accessibility checks (keyboard, contrast, semantics, zoom) executed for UI changes
- [ ] Idempotence and failure paths exercised; rollback or compensation known
- [ ] Observability in place (logs without secrets/personal data, metrics, alerts) if runtime
- [ ] Docs, ADR/decision records, rules registry and runbooks updated
- [ ] No secrets or personal data in code, issues or evidence
- [ ] Principal re-ran at least one evidence command; Status moved by authority rules
- [ ] Human acceptance recorded (identity, date, scope, decision)

## Estimation and prioritization
Use relative points (or t-shirt sizes) and re-estimate when scope changes. Record the
prioritization method and inputs; reprioritize only with a logged reason. Keep WIP bounded:
do not start a story that cannot be finished with the current staffing and gates.

## Board hygiene
One issue per story and per task, added to the single Project; fields kept current (Status,
Priority, Type, Estimate, Agent, Sprint, Due date). Epics show progress through sub-issues.
Stale items are reviewed in grooming and closed with a reason. Titles are searchable and
stable; the ID in the title is the identity, the issue number is the link.
