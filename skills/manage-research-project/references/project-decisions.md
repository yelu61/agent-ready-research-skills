# Review, plan and accept project work

Use only the section needed for the current project decision. Start from the
existing goal, current milestone and related evidence; retain the project's
layout and approved scope. A diagnosis is not an instruction to redesign the
whole study or run every analysis.

## Review progress or diagnose a blocker

Establish the deliverable at risk and the observed symptom. Check which parts
are actually delivered, checked, waiting on external input or unverified. An
old status or an inaccessible file is an information gap, not proof of failure.

For a material blocker, connect:

1. observable symptom and affected milestone;
2. inspected evidence, source/version and relevant limitations;
3. plausible causes and evidence for/against each;
4. the smallest check that would change the next decision;
5. actions if that check supports, rejects or cannot distinguish the causes.

Possible causes include a missing input, unsuitable design, implementation
defect, inadequate evidence, unclear acceptance, collaborator dependency or
unnecessary optimization. Do not identify a root cause from a symptom alone.
When evidence already explains the next step, give that step directly rather
than filling a blocker card. A dependency is blocking only the work that
actually needs it; other useful project actions may remain possible.

For a delivery-stage project, distinguish core evidence gaps from presentation
repairs and optional extensions. A new method or interesting paper alone does
not justify restarting a nearly finished analysis. For exploration, prioritize
the feasibility assumption that determines whether more investment is useful.
For infrastructure, tie improvements to actual user scenarios and reliability.

## Plan a stage or execution assignment

Recommend one bounded approach; add a fallback or alternative only when the
uncertainty or resource tradeoff warrants it. Explain which uncertainty the
work resolves and how the result changes the project decision.

Use existing task and milestone IDs. For new substantive tasks, specify the
intended deliverable, inputs/version, dependencies, output location or type,
acceptance criteria, next action and an owner if known. Unconfirmed owners,
deadlines and effort remain unknown. Small administrative updates need not
acquire a full task schema.

For research tasks, define what a supporting, negative or inconclusive result
would permit. Acceptance concerns the question and evidence, not obtaining a
preferred positive result. State the smallest useful stopping or escalation
condition; do not keep adding analyses until a result becomes significant.

An execution assignment contains the approved question/scope, task IDs,
input/version references, method constraints, deliverable, checks and return
format. The executor should return actual actions, output identities, checks
and remaining gaps. Preparing the assignment does not dispatch it or authorize
extra compute. A session-resumption handoff instead uses
[Audit and handoff](audit-and-handoff.md).

## Compare literature only when it can affect the decision

Name the project decision and the missing external evidence before searching.
Reuse adequate supplied material; otherwise use available lawful search tools
with a bounded scope and a decision-relevant stopping condition. Do not require
a literature search for every review.

Compare question, sample/design, method, evidence, validation, limitations,
transferable component and its prerequisites/cost. Preserve source identifiers,
version/date and whether the material was read as abstract or full text. A
search result, journal prestige or simulated expert view is not independent
scientific evidence; a failed search does not establish novelty.

Conclude whether to keep the route, narrow a claim, make one necessary check,
propose repositioning, defer an opportunity or record a specific evidence gap.
Learning needs should enable a current project action; do not turn every
interesting finding into a task or reusable global skill.

## Accept a milestone

Read the agreed deliverable and acceptance criteria before judging completion.
Map each criterion to an inspected artifact, log, review or explicit missing
evidence. Missing criteria call for a proposed definition, not retroactive
invention of a passing standard. Record one of:

- **passed**: applicable agreed criteria are supported;
- **conditional**: a scoped delivery is supported with explicit restrictions;
- **failed**: evidence shows an applicable criterion is unmet;
- **not_assessed**: required criteria or evidence are unavailable.

Keep task status, milestone acceptance, execution, scientific readiness and
claim authorization separate. Accept a valid negative result when the agreed
question and checks are satisfied. A file's existence or the user's report
alone does not establish an unobserved scientific assessment. A well-supported
administrative completion need not wait for unrelated scientific validation.

Where scientific validity is an acceptance criterion, inspect the scoped
domain evidence and [scientific integrity rules](scientific-integrity.md).
Validate a readiness declaration if it is used for a delivery/execution gate;
the generic validator cannot itself establish its scientific truth. Propose
only the corrections needed for unmet criteria, with a clear reassessment
condition; no automatic full structural audit is needed for this mode.

## Record only authorized, supported changes

Use [the document contract](document-contract.md) to resolve ownership and
state meanings. A read-only review ends with its findings/proposals. When
recording an accepted plan or assessment is authorized, update the existing
task/status/decision records using stable IDs and evidence references; a local
checkpoint must not create a competing external task master.

Report verified facts, user reports, inferences, proposed actions and actual
writes separately. Prefer at most three immediate priorities, while retaining
additional requested detail when it matters. Do not report invented progress
percentages without a defined work breakdown, weights and actual evidence.
