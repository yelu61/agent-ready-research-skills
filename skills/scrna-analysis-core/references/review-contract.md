# Executable Review Contract

Status: `WorkflowReview 0.2-draft`, portable skill output with a minimal
structural checker. It does not imply a scLucid Python class. Read
[Minimum handoff](handoff-minimum.md) for exact checked fields, runnable examples,
and explicit migration from the documentation-only `0.1-draft`.

## Contents

- Contract position
- Status semantics
- WorkflowReview schema
- Stage and parameter decisions
- Results guide and prioritization
- Minimum RunEvidence handoff

## Contract Position

```text
ReasoningBrief
  -> WorkflowReview
  -> execution
  -> RunEvidence
```

- Consume scientific meaning from `ReasoningBrief` when available.
- Own scRNA-seq feasibility, workflow decisions, diagnostics, interpretation
  guidance, and rerun scope.
- Request `RunEvidence` from the executor for evidence that was actually
  produced.
- Never replace a missing scientific question with an invented one.

## Status Semantics

- `BLOCKED`: required input or identifiable design is absent.
- `REVIEW`: executable, but an unresolved choice can alter interpretation.
- `READY`: adequate for the explicitly stated next use.
- `NOT_RUN`: no auditable execution evidence.

`READY` is use-specific. A dataset may be ready for exploratory annotation
but blocked for treatment-effect inference.

## WorkflowReview Schema

```yaml
schema_name: WorkflowReview
schema_version: 0.2-draft
review_id: WR1
question_id: Q1
input_reasoning_version: 0.2-draft
overall_status: REVIEW
objective_and_estimand: null
context:
  experimental_unit: null
  sample_key: null
  batch_key: null
  condition_key: null
evidence_coverage:
  - evidence_id: E1
    feasibility: partial
    planned_stage: analysis
    required_artifact: null
    limitation: null
stages: []
parameter_decisions: []
results_guide: []
claim_boundary:
  supported: []
  exploratory: []
  unsupported: []
blockers: []
assumptions: []
prioritized_actions: []
missing_evidence: []
```

Use `question_id` and `evidence_id` values from the upstream brief. If no
brief exists, create local identifiers and mark their source as
`workflow_review_local`.

## Stage Review Table

Return one row per relevant stage:

| Field | Meaning |
| --- | --- |
| stage | provenance, design, QC, preprocess, integration, annotation, inference, advanced |
| status | BLOCKED, REVIEW, READY, or NOT_RUN |
| evidence | files, object fields, plots, tables, logs, or metrics inspected |
| risk | failure mode and likely consequence |
| decision | the question that must be resolved |
| next_action | smallest concrete action |
| rerun_scope | earliest stage invalidated by a changed decision |

## Parameter Decision Card

For each consequential parameter, emit:

```yaml
decision: integration_method
status: REVIEW
candidates: [unintegrated, harmony, scvi]
diagnostic:
  - batch mixing within shared cell types
  - biological conservation
  - condition preservation
recommended: null
reason: batch and condition are partly confounded
sensitivity: compare unintegrated and two defensible corrected spaces
rerun_scope: neighbors -> clustering -> annotation review
```

Never invent precision. A bounded range or unresolved decision is better than a
false optimum.

## Results Guide

For every key output explain:

1. what is plotted or tabulated;
2. which data representation was used;
3. what pattern is reassuring or concerning;
4. which parameter or scientific decision it informs;
5. what it cannot establish;
6. what to do if the result is ambiguous.

## Prioritization

Order actions by dependency and risk:

1. design blockers and count provenance;
2. QC failures that change retained populations;
3. integration or annotation choices that affect all downstream results;
4. formal inference;
5. optional advanced analyses and presentation.

Do not recommend a full rerun when a later stage can be safely repaired. Do not
recommend a local patch when upstream evidence invalidates the object.

## Minimum Handoff

End with:

- current overall status;
- decisions already locked;
- decisions still requiring review;
- smallest next action;
- exact artifact to inspect after that action;
- supported and unsupported claims.

For each feasible evidence item, request a downstream `RunEvidence` record
containing the executed method, version, parameters, artifact, representation,
experimental unit, effect or summary, uncertainty, sensitivity, status,
supporting or challenging implications, and limitations. A planned analysis is
not `RunEvidence`.

RunEvidence must identify an actual run, completed/failed execution status,
artifact, method (including version or explicit unknown), and observed result.
The minimal checker verifies structure and upstream IDs, not that execution
occurred or that a mechanistic conclusion is warranted.
