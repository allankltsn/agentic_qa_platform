# Usability rounds with simulated lay users and the decision brainstorm

Purpose: find where ordinary people hesitate, fail or feel afraid, then decide fixes
together without breaking crucial business rules, privacy law or user health and safety.
Applies to any user-facing screen or flow (web, mobile, documents, emails, onboarding).
It complements, never replaces, accessibility audits, QA and tests with real users.

## Cast
- **Principal**: runs the process, owns decisions, records them, persists reports.
- **ux-researcher**: plans the round, moderates, triages, prepares the brainstorm.
- **Exactly two lay-user instances**: the weakest, cheapest tier (light; today Haiku), distinct
  personas, no technical knowledge, read-only.
- **Brainstorm participants**: ux-designer, ui-designer, brand-strategist (copy and voice),
  product-owner (business rules), privacy-compliance, the implementing specialist
  (frontend-senior or backend) and, when the topic needs them, security, qa, marketing.

## Precedence (decides conflicts)
1. User safety and health, privacy and data-protection law (for example LGPD, GDPR), consumer-protection law.
2. Crucial business rules (cited by BR-id).
3. Usability and accessibility.
4. Copy and brand voice.
5. Preference.
A usability improvement that violates 1 or 2 loses; look for an option that satisfies both.
Items needing a lawyer are marked `[LEGAL-REVIEW]` and go to the human; they do not ship on
an agent's say-so.

## Protocol
1. **Prepare** (ux-researcher). Personas (templates/persona.md) with realistic constraints and
   emotions; two personas that differ (for example a hurried small-business owner and an older
   user with reduced vision on a phone). Tasks in plain words with success conditions. The
   screens or pages the personas may view (screenshots or static HTML), nothing else.
2. **Isolate**. Each lay user receives only persona + one task at a time + permitted screens.
   No code, tokens, contracts, rules registry or the other persona's report. Run both in
   parallel; neither sees the other's output.
3. **Execute**. Each reports per task in templates/usability-report.md. Reports are persisted
   verbatim by the principal in the project's usability folder, one file per round and persona.
4. **Triage** (ux-researcher). Merge duplicates, rate severity (blocker / major / minor /
   cosmetic) and frequency (both personas / one), map to screen and criterion, separate
   comprehension, navigation, trust/fear, accessibility and bug problems. Reports that point
   to defects (broken link, wrong data) go to the issue tracker, not the brainstorm.
5. **Brainstorm** (principal + participants, new round of dispatches). For each triaged item:
   state the problem in the user's words; list options; each participant states constraints
   from their domain (BR-ids, privacy findings, health risks, brand, effort); pick the option
   by the precedence order. Record a decision (templates/decision.md) for each item: problem,
   options, choice, rule/privacy/health impact, owner, status (final / provisional pending
   human). Disagreements need evidence, not volume; the principal breaks ties by precedence
   and escalates real value trade-offs to the human.
6. **Fix**. Decisions become tasks on the board with owners, tiers and gates (QA, privacy,
   accessibility). Copy changes go through brand-strategist; flow changes through ux-designer.
7. **Re-test**. Repeat with the same two personas plus any new one if the audience changed.
   Compare task results across rounds. Stop when no blocker or major item remains, or the
   human accepts the residual risk. Record the round summary and the evidence class
   ("simulated lay users").

## Guardrails for the brainstorm
- No dark patterns: no pre-ticked consent, hidden opt-outs, false urgency or guilt copy to win a usability or conversion metric.
- Never trade consent clarity, data minimization, cancellation ease, price transparency or
  safety messaging for conversion or convenience. Prefer clearer wording and better defaults.
- Do not remove a required legal or safety notice; make it readable (short summary first,
  details one tap away, plain language, adequate size).
- Do not hide an inconvenient business rule; explain it where the user meets it.
- Health-related products: no guilt, streak pressure, restrictive or unsafe nudges; keep
  "stop and seek professional help" guidance; non-judgmental body language.
- Personal and health data are never kept in drafts, URLs, logs or analytics as a usability
  convenience.
- Simulated users can miss real needs: for high-risk flows, plan validation with real users.

## Outputs
Persona files, per-round lay-user reports, triage table, decision records, board issues for
the fixes, round summary with severity counts before and after, and open items for the human.
