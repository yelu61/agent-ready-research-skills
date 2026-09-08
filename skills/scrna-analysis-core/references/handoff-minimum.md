# Minimum Portable Handoff: 0.2-draft

This is a small document contract, not a software orchestration framework.
The same version is packaged independently in both skills; neither loads a
sibling package. The repository tests apply the same valid/invalid payloads to
both validators to detect semantic drift. Extensions are allowed, but they must
not replace the fields below or silently change identifiers.

## Checked minimum

Every document has nonempty question_id, schema_name and schema_version.
The version is 0.2-draft. A ReasoningBrief or WorkflowReview also has a
claim_boundary object with supported, exploratory and unsupported string lists.

| Document | Additional checked fields |
| --- | --- |
| ReasoningBrief | primary_question; estimand.experimental_unit as string or explicit null; required_evidence list, each entry with a unique evidence_id |
| WorkflowReview | review_id; overall_status; evidence_coverage list with unique evidence_id and feasibility; stages list with stage name and status |
| RunEvidence | evidence_id, run_id, execution_status completed/failed, quality_status; artifact.path_or_key; method.name and a version field; result.summary |

Statuses are BLOCKED, REVIEW, READY, NOT_RUN. RunEvidence cannot use NOT_RUN.
Feasibility is feasible, partial, infeasible or unknown. An empty evidence list
can represent unfinished framing, but is not a complete evidence plan.
Unknown scientific fields remain null and need explanation; do not invent them
to obtain a successful validation result. For an unknown method version, use
null plus a limitation. Scope, estimand detail, effect/uncertainty, falsifiers,
alternative explanations and provenance still require substantive review.

With an upstream brief, the checker requires the same question_id and requires
WorkflowReview to cover each upstream evidence_id exactly once. To add evidence,
revise the brief explicitly and preserve existing IDs. RunEvidence must refer
to one upstream evidence item. Without a brief, use local IDs and record
identity_source: workflow_review_local rather than inventing an upstream source.

## Run the optional checker

Python 3.9+ standard library only. Resolve the script path from this skill.

```bash
python scripts/validate_handoff.py REVIEW.json --brief BRIEF.json
```

Exit 0 means valid structure/identifiers, 1 means rejected structure, and
2 means unreadable input or invalid JSON. The tool does not read an artifact,
verify a scientific claim, prove that a run occurred, or validate any scLucid
interface. A fabricated but structurally valid record is still fabricated.

The [paired response brief](../assets/examples/paired-response-brief.json) and
[review](../assets/examples/paired-response-review.json) are synthetic authored
examples. They contain a feasible association question and a missing causal
mechanism, not experimental findings or an independent model-evaluation result.
They can be passed directly to the checker. For qualitative evaluation, use
[evaluation cases](evaluation-cases.md) and keep input material separate from
reviewer criteria in an isolated run.

## Migration from 0.1-draft

The earlier documentation-only draft showed two incomplete WorkflowReview
field sets. Version 0.2-draft aligns the shared minimum and claim boundary;
the larger scientific fields remain optional extensions. Add missing minimum
fields, keep question/evidence IDs and mark unknowns; change the version only
after reviewing the conversion. For RunEvidence, add explicit execution_status
and do not convert a planned analysis into a run record. Older drafts are
rejected by the checker with a migration message; there is no silent upgrade.

The legacy field name validation_ladder, when used, means a prioritized plan
for additional evidence across independent axes. It is not an ordinal ranking
that makes clinical association more causal than a controlled experiment.
