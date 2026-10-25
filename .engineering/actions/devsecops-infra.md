# Action: devsecops-infra
Intent/scope: IaC security review. Arguments narrow area; without arguments inspect complete change snapshot. Use available authorized Checkov/Trivy/terrascan or explicit fallback. Missing scanner is a coverage limit, not a pass.
Responsible specialist: devsecops-infra; principal routes, questions and consolidates.
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
