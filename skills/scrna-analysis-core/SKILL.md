---
name: scrna-analysis-core
description: Plan, troubleshoot or review scRNA-seq workflow decisions and sample-level inference; skip isolated syntax, format conversion and plot styling. Use for 单细胞流程审查、分析设计、注释依据、批次整合判断、患者级统计 and interpretation of scientific results. A file type, package name or UMAP alone is not a trigger.
---

# scRNA Analysis Core

Act as the executable mid-level reviewer for scRNA-seq workflows. Convert
project context and available artifacts into auditable decisions, stop unsafe
inference, and identify the smallest defensible next action.

Do not treat a community best-practice workflow as a universal recipe. Match
each method and parameter to the assay, biological question, sample design, and
downstream estimand.

The core review is self-contained. `scientific-reasoning`, statistical-review
skills and scLucid are optional: if absent, define the question, experimental
unit, evidence needs and claim boundary here, then complete the review and
portable handoff. Do not require installation of another skill.

Scope the review to the requested decision or failure and the prerequisites
that can change it. A focused code/API or presentation edit stays a focused
task even if this skill is explicitly named; do not expand it into a pipeline
review. Add another skill only for a distinct unresolved specialist question,
not to repeat an adequate review of the same evidence.

## Select the Operating Mode

- **Plan**: design the next workflow before execution.
- **Audit**: assess an existing object, notebook, pipeline, or result.
- **Troubleshoot**: localize a failure and recommend the smallest rerun scope.
- **Interpret**: explain outputs, uncertainty, and what decisions they support.

State the selected mode. If the request combines modes, perform them in the
order audit -> troubleshoot -> plan -> interpret.

## Establish Context

Determine only fields that can change the decision:

1. species, tissue, assay, and study objective;
2. input provenance: raw reads, unfiltered droplets, filtered counts, or a
   processed object;
3. biological samples or donors, conditions, technical batches, pairing,
   repeated measures, and known confounders;
4. current stage and available object fields, logs, plots, tables, or code;
5. experimental unit, target population, contrast, and intended claim.

Ask only for missing details that materially change the next step. Inspect
provided artifacts before proposing a replacement workflow. Never reuse a
biological sample identifier as a technical batch unless that relationship is
explicitly true.

When a `ReasoningBrief 0.2-draft` is provided, preserve its `question_id`,
`evidence_id`, estimand, alternatives, and claim boundary. Audit feasibility
and missing evidence; do not silently redefine the scientific question.

## Inspect Before Recommending

When the requested scientific decision depends on local AnnData integrity,
metadata or count representation, inspect the relevant object. Reuse current
inspection evidence when it covers the same unchanged object and question;
otherwise run:

```bash
python /path/to/this-skill/scripts/inspect_anndata.py INPUT.h5ad
```

Use `--sample-key`, `--batch-key`, and `--condition-key` when automatic
key discovery is ambiguous. Treat the script as structural evidence, not proof
of biological validity. For Seurat, SingleCellExperiment, notebooks, or result
directories, inspect equivalent matrix provenance, metadata, sample design,
and parameter records manually.

The presence of an h5ad file alone does not require this inspection. For
isolated syntax, conversion or plot styling, perform only the checks needed
to preserve the requested data or presentation behavior.

For a requested condition comparison, add `--contrast TREATED CONTROL`. This
checks estimability only in the additive batch + condition model; inspect the
full pairing/covariate design and biological replication separately. Missing
metadata yields an unknown result, not an assurance. Output defaults to stdout;
`--output REPORT.json` creates a report without replacing an existing file;
`--overwrite-output` explicitly replaces a JSON report, never the input/aliases.
Read [Runtime and audit limits](references/runtime-and-audit-limits.md) for
dependencies, tested versions, sampled-value scope and exit-code semantics.

## Route the Work

- For object integrity, QC, normalization, feature selection, integration,
  clustering, annotation, and tumor-specific gates, read
  [Workflow stages](references/workflow-stages.md).
- For differential expression, abundance, pathways, trajectories, RNA
  velocity, regulatory networks, and communication, read
  [Statistical inference](references/statistical-inference.md).
- For the `ReasoningBrief -> WorkflowReview -> RunEvidence` handoff,
  statuses, parameter decisions, claim boundaries, and required report fields,
  read [Review contract](references/review-contract.md).
- For the external benchmark mapping and maintenance policy, read
  [Source map](references/source-map.md).
- When changing this skill, test against
  [Evaluation cases](references/evaluation-cases.md).

Use `differential-analysis-review`, if available, when the main question is contrast design,
covariates, pseudobulk, repeated measures, effect sizes, or FDR control.
Use `scientific-reasoning`, if available, when the main task is to define the biological
question, evidence ladder, alternative explanations, validation, or allowable
claim before selecting a workflow. Use a literature-search skill when external
evidence is primary. Use a named perspective skill only when the user
explicitly requests that researcher's viewpoint.

When these extensions are absent, use this package's design, inference and
claim-calibration references and available primary-source tools. An unavailable
named perspective must not delay or impersonate the ordinary scientific review.

## Apply Stage Gates

Review the affected stages and their decision-relevant prerequisites in
dependency order; reuse applicable current evidence. Assign one status:

- **BLOCKED**: a prerequisite is absent or the design cannot identify the
  requested comparison.
- **REVIEW**: execution is possible, but a consequential assumption, parameter,
  or biological interpretation remains unresolved.
- **READY**: prerequisites, evidence, and decision rationale are adequate for
  the stated next use.
- **NOT_RUN**: no evidence that the stage was executed.

Do not let a downstream plot override an upstream blocker. Review in this order:

1. data provenance and object integrity;
2. sample design and identifiability;
3. per-sample QC, ambient RNA, and doublets;
4. normalization, feature selection, dimensionality reduction;
5. necessity and quality of integration;
6. clustering stability and annotation evidence;
7. sample-level expression or abundance inference;
8. pathway, trajectory, velocity, GRN, or communication assumptions;
9. biological interpretation and claim boundary.

## Make Parameters Decidable

For every consequential parameter, report:

1. **decision** — what is being chosen;
2. **candidates** — plausible values or methods;
3. **diagnostic** — evidence used to compare them;
4. **recommended** — selected option, or a bounded range;
5. **reason** — why it matches the objective and data;
6. **sensitivity** — whether conclusions persist across reasonable choices;
7. **rerun scope** — earliest affected stage if the decision changes.

Avoid universal fixed thresholds for mitochondrial fraction, detected genes,
HVG count, PC count, neighborhood size, Leiden resolution, or integration
strength. Defaults may seed an exploration; they do not justify the final
choice.

## Boundaries

Do not use this skill as:

- a package API manual for an isolated syntax question;
- a bulk RNA-seq workflow;
- a TCGA mutation or copy-number workflow;
- a substitute for literature verification;
- an automatic license to rerun or overwrite user data.

## Output Contract

For a workflow review or handoff, return a compact `WorkflowReview 0.2-draft`
package with the fields below. For a focused interpretation or troubleshooting
question, return only the relevant decision, evidence, claim boundary, and next
action; do not force a full package.

1. **Objective and estimand**
2. **Context and experimental unit**
3. **Stage table** — status, evidence, risk, decision, next action, rerun scope
4. **Parameter decision table**
5. **Results guide** — how to read each key artifact and what choice it informs
6. **Claim boundary** — supported, exploratory, and unsupported statements
7. **Prioritized actions** — smallest defensible next step first
8. **Missing evidence**

Separate observations, interpretations, and decisions. Label exploratory
results explicitly. Do not make condition-level biological claims from
cell-level replication alone, infer mechanism from expression association, or
infer clinical benefit from a discovery cohort without appropriate validation.
