# Truthful evidence and reproducible snapshots

Evidence is generated from actual inspection/execution, never from memory, inferred
success or invented results. Record exact command, cwd, date/time UTC, exit code,
Git SHA, comparison base and complete local snapshot including untracked files.
For uncommitted work record inventory/content hashes and staged/unstaged diff;
plain git diff omits staged and new files. Record exclusions and why.

Record stdout/stderr or path to sanitized raw output, warnings, failures, not-verified
items and criteria mapping: satisfied with proof / partial / unmet. Do not clean away
failures, summarize inaccurate counts or equate absent tooling with a pass.
Redact secrets before saving, preserving useful nonsecret evidence and redaction note.

Distinguish static file inspection, unit/integration tests, build, final-image startup,
local runtime, remote environment and human acceptance. Build green is not deployed.
An issue/file/report marked completed is not evidence of its asserted behavior.

Every finding: stable ID, original/common severity, criterion, file:line/resource,
reproduction or technical rationale, author, responsible fixer, resolution condition,
evidence, state and confirming independent instance/snapshot. Consolidate duplicates
without losing author attribution. Do not silently discard optional recommendations.

Final validity is per gate and snapshot. A later change requires impact analysis and
revalidation of affected gates; unchanged evidence may be reused with explicit
justification. An old SHA never automatically approves the new tree. Principal
checks gate coverage, outstanding IDs and at least one relevant evidence command
before consolidating. No independent gate substitutes for another.
