# Delivery quality principles

The principal manages specialists to deliver a product, not just to complete tasks. These
principles apply to every spec, plan, brief and review. A gate can fail a delivery for
violating them; they are criteria, not decoration. Scale the depth to the risk (a prototype
needs less than a payment flow) and record the reasoning when a principle is waived.

## Reuse before build
- Search the repository, shared packages, design system, templates and installed
  specialists/skills before creating anything. Record what was found and why it was or was
  not reused. Prefer extending the one owner of a shared asset over duplicating it.
- Shared contracts (API schemas, types, tokens, packages) have one source of truth and one
  owner; consumers import, never copy.

## Idempotence
- Operations that may run twice must be safe to repeat: scripts, migrations, deploys, jobs,
  webhooks, UI submits, agent dispatches. Use natural keys, upserts, request/idempotency
  keys, "create if absent", and overwrite-not-append for generated artifacts.
- Re-running a specialist on the same input overwrites its own output; it never duplicates it.

## Fault tolerance
- Name the failure modes in the design: dependency down, slow, partial, duplicated or
  out-of-order; bad input; exhausted quota; a failed agent. State the behavior for each:
  timeout, retry with backoff and jitter (only for safe operations), circuit breaker,
  fallback, degrade gracefully, dead-letter, alert.
- Every change that can fail midway states its rollback or compensation and how it is tested.
- Agent work: a silent, timed-out or incomplete specialist is a failure to handle (retry once
  with a sharper brief, then replace or escalate), never an approval. Persist handoffs so a
  replacement can continue from the issue and evidence, not from memory.

## Scalability and operability
- Prefer stateless components, horizontal scaling, bounded queues and pagination; identify
  the first bottleneck and the signal that will show it. No unbounded loops, lists or fan-out.
- Observability by design: logs without secrets or personal data, metrics for the golden
  signals, traces across services, health checks, and a runbook for what pages someone.
- Versioned, backward-compatible interfaces; expand/contract migrations; feature flags for risky
  rollouts.

## Simplicity and cost
- The smallest design that meets the criteria. No speculative abstraction, no premature
  platform. Any added component needs a stated reason and an owner.
- Right-size infrastructure and model usage (policies/models.md). Record cost assumptions.

## Security and privacy by default
- Least privilege, secrets outside the repository, validated input, authorization on every
  route, minimal personal data with a stated purpose. Privacy and security review are gates,
  not a final polish (policies/safety.md).

## Verifiability
- Every requirement has an observable acceptance criterion and an owner of the proof.
  "Done" means evidence on the final snapshot (policies/evidence.md): commit or PR, tests
  executed with output, and runtime proof where the claim is runtime behavior.
- Decisions that cost something to reverse are written down (templates/decision.md) with
  context, options, choice, consequences and who approved.

## Management checks the principal runs at each phase
1. Spec: criteria testable? business rules cited? risks and failure modes named? reuse noted?
2. Plan: tasks small, vertical, with disjoint write scopes, owners, models, gates, rollback?
3. Dispatch: brief complete, tier justified, independent validators assigned?
4. Delivery: evidence real and on the final snapshot? findings dispositioned? idempotence
   and failure paths exercised, not only the happy path?
5. Closure: postmortem facts recorded, decisions logged, backlog and docs updated, open
   risks handed to the human with a recommendation.
