# Regression Evaluation Cases

Use these cases when changing routing, thresholds, status semantics, or the
output contract.

These prose cases are evaluation designs, not completed agent evaluations.
Save actual isolated-agent inputs/outputs and model/version before grading;
keep reviewer criteria out of the agent's input. Helper regressions and JSON
contract checks only establish their own executable behavior. They do not
measure full pipeline accuracy or scientific reasoning performance.

## Case 1: Single-Sample PBMC Exploration

Input: one 10x PBMC library, no condition comparison, raw counts preserved.

Expected behavior:

- permit exploratory QC, clustering, and annotation;
- do not demand integration;
- do not claim population-level differential effects;
- explain how QC and resolution choices are evaluated.

## Case 2: Confounded Treatment Study

Input: treated samples sequenced in batch A and controls in batch B.

Expected behavior:

- mark treatment-effect inference `BLOCKED`;
- do not propose integration as a remedy for confounding;
- allow carefully labeled descriptive exploration;
- request design or independent validation evidence.

## Case 3: Replicated Paired Tumor Study

Input: paired pre/post tumors from multiple patients with counts and patient ID.

Expected behavior:

- set patient as experimental and paired unit;
- route condition DE to paired pseudobulk;
- review tissue sampling and composition changes;
- separate malignant inference from epithelial annotation.

## Case 4: Integrated Object Without Counts

Input: only an integrated latent space and normalized matrix.

Expected behavior:

- allow review of embedding or annotation if provenance is adequate;
- mark count-based formal inference `BLOCKED` or `REVIEW`;
- request the authoritative counts object;
- never treat integrated values as raw counts.

## Case 5: Rare Fragile Population

Input: rare cells have higher mitochondrial fraction and lower counts.

Expected behavior:

- reject an unexamined global fixed cutoff;
- compare per-sample and provisional-lineage distributions;
- assess retention sensitivity and marker coherence;
- preserve or flag uncertainty before irreversible removal.

## Case 6: RNA Velocity in Steady-State Blood

Input: PBMC data with spliced and unspliced layers but no plausible transition.

Expected behavior:

- do not recommend velocity merely because layers exist;
- mark the biological applicability as `REVIEW` or `BLOCKED`;
- explain kinetic and process assumptions;
- suggest an analysis matching the actual question.

## Case 7: Result Interpretation Request

Input: user has QC plots, several integration embeddings, resolution sweep, and
DE tables but cannot choose parameters.

Expected behavior:

- provide a results guide, not another parameter list;
- connect each artifact to a concrete decision;
- compare candidate choices with sensitivity;
- identify locked decisions and smallest next action.

## Case 8: ReasoningBrief Handoff

Input: a `ReasoningBrief 0.2-draft` requests evidence E1 for a replicated
condition effect and E2 for a causal mechanism, but only cross-sectional
scRNA-seq data are available.

Expected behavior:

- preserve the upstream question and evidence IDs;
- mark E1 feasible only if sample-level replication and counts are adequate;
- mark E2 incomplete rather than substituting pathway or communication scores;
- emit a `WorkflowReview`, not a `RunEvidence`;
- specify the additional perturbational or orthogonal evidence required.

## Case 9: Contrast-specific disconnected design

Input material: synthetic eight specimens, one per observed pair:

| Batch | Conditions represented |
| --- | --- |
| b1 | A, B |
| b2 | A, B |
| b3 | C, D |
| b4 | C, D |

User asks for both A−C and A−B adjusted for batch. Counts and independent
specimen IDs exist; no other covariates have yet been reviewed.

Reviewer criteria: identify two connected components; additive design rank 6
with 7 treatment-coded columns; A−C not estimable, A−B potentially estimable;
do not block every contrast or call a connected subcomparison causally valid.
Explain the need to review remaining experimental-unit/model assumptions.
The helper regression exercises this actual synthetic structure.

## Case 10: Paired analysis and missing causal evidence

User material: [synthetic brief](../assets/examples/paired-response-brief.json),
eight patients with pre/post specimens, specimen_id distinct from patient_id;
some CAF strata have no post specimen cells; batch partly crossed; normalized
expression available but authoritative counts not yet inspected; LR ranks rise;
no spatial, protein or perturbation measurements. User asks for a runnable plan.

Reviewer criteria: retain Q7/E1/E2; aggregate by specimen×cell type and pair by
patient without collapsing pre/post; inspect effective donor/paired coverage
per cell type and full model; request count provenance for count-based inference;
permit appropriate descriptive review; mark mechanism evidence incomplete;
emit WorkflowReview, not a claimed execution record. The supplied
[review example](../assets/examples/paired-response-review.json) is authored
material for structural checks, not an independently generated model result.

## Case 11: Numerically imperfect but interpretable input

Input material: a filtered h5ad with a layer named counts containing fractional
ambient-corrected estimates, documented original integer counts elsewhere;
sample metadata are complete; a single-library annotation question. User asks
whether to delete the object and rerun everything.

Reviewer criteria: do not destroy or overwrite data; distinguish integer
provenance from a numeric heuristic; inspect correction/consumer requirements;
use the authoritative source when a count model requires it; allow review of
the existing annotation if adequate; choose the smallest justified rerun scope.
Do not automatically round or declare every fractional estimate biologically
invalid. The helper test verifies REVIEW rather than automatic BLOCKED for
finite nonnegative fractional sampled values.

## Case 12: Display-only UMAP edit

Prompt: “Set legend_fontsize=8 in this existing sc.pl.umap call. The data,
embedding, labels and scientific interpretation are unchanged.”

Expected: make the display edit and check the relevant syntax/API or rendering
when available. A UMAP call or nearby h5ad file does not alone require object
inspection, integration review, a WorkflowReview or a scientific-reasoning
handoff. Do not claim to have rendered or validated data that were not supplied.

## Case 13: Reuse adequate evidence, refresh changed evidence

Input: a current integrity report is bound to the exact unchanged h5ad and
documents counts and specimen/patient metadata. Prompt: “Explain the report's
sample-versus-patient distinction.” Then a separate request says the object has
been replaced and asks to run count-based differential analysis using that report.

Expected: explain the first request from adequate existing evidence without
rerunning the inspector. For the changed object, inspect current relevant
provenance and design before new inference; do not reuse stale counts or
experimental-unit evidence merely to keep the task lightweight.
