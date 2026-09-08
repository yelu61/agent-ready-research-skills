# scLucid Reasoning Bridge

This optional adapter is used only when scLucid is requested and available.
Without it, deliver the portable brief and workflow requirements directly; no
part of the core skill depends on scLucid. The field names below are historical
mapping candidates, not a verified current API. Inspect the installed version,
available fields and serialization before using them and record that version.
No supported scLucid version is claimed by this package. The P0
schemas are defined in
[Reasoning contract](reasoning-contract.md) as portable, structurally checkable
`0.2-draft` objects.

## Candidate Mapping Into ProjectContext

| Reasoning field | Candidate scLucid field to verify |
| --- | --- |
| assay | `assay` |
| tissue or system | `tissue`, `tissue_type`, `dataset_type` |
| cancer context | `cancer_type` |
| primary objective | `study_objective` |
| biological sample | `sample_key` |
| technical batch | `batch_key` |
| comparison | `condition_key` |
| experimental unit | `experimental_unit_key` |
| paired or repeated unit | `paired_key` |
| identity field | `cell_type_key` |

Store the full scientific question, estimand, alternatives, validation ladder,
and claim boundary outside these fields until a versioned reasoning schema is
implemented. Do not overload `study_objective` with an entire protocol.

## Handoff to plan_analysis

Provide:

- explicit context fields above;
- requested stages;
- count provenance and available object fields;
- design blockers;
- evidence required for the primary claim;
- analyses that are exploratory versus confirmatory.

The `AnalysisPlan` should then express structural prerequisites, decisions,
assumptions, risks, and smallest next step. It cannot decide biological truth
from metadata alone.

## Handoff From review_run

Translate stage reviews into scientific consequences:

| Workflow status | Reasoning consequence |
| --- | --- |
| QC BLOCKED | downstream state or abundance claims are not interpretable |
| Integration REVIEW | cluster and annotation conclusions require sensitivity |
| Analysis READY | only the analyses and claim levels actually reviewed are ready |
| Tumor REVIEW | malignant-state conclusions remain provisional |
| NOT_RUN | absence of evidence, not evidence of absence |

## Three-Object Handoff

```text
ReasoningBrief
  -> AnalysisPlan and WorkflowReview
  -> scLucid execution
  -> RunEvidence
  -> scientific claim audit
```

When these interfaces exist, keep metadata, executable plan and cross-stage
review separate. Do not claim that `ReasoningBrief`, `WorkflowReview`, or
`RunEvidence` are implemented scLucid APIs until code, compatibility,
serialization, and real-project tests exist.

Pass only the identity-independent scientific content of a stabilized
`ReasoningBrief`. Do not make scLucid depend on a named researcher skill or
serialize perspective identity as evidence.
