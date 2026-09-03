# Project-wide agent instructions

## Read before work

Read `README.md`, `docs/PROJECT_BRIEF.md`, `docs/PROJECT_STATUS.md`,
`docs/ANALYSIS_PLAN.md`, and `docs/SESSION_HANDOFF.md`. Read
`docs/DATA_DICTIONARY.md` before using data and `docs/DECISION_LOG.md` before
changing established logic. Read `docs/READINESS.md` and the named readiness
report before treating an analysis as ready. Read `docs/DATA_GOVERNANCE.md` when
present and honor its access boundaries.

## Scientific integrity

- Protect scientific integrity over speed.
- Separate source provenance/integrity, implementation, execution, technical
  validation, declared readiness, contract, currency, policy, analysis mode,
  claim authorization, target/achieved validation and lifecycle status.
- A structure audit does not assess scientific readiness. A successful command
  does not establish scientific validity, truth, reproduction or causality.
- State the experimental unit, comparison, model/test, covariates, cutoff and
  multiple-testing rule.
- Report effect sizes and uncertainty when applicable.
- Do not infer causality from association, enrichment, correlation,
  co-purification or cross-omics concordance alone.
- Do not silently exclude samples, cells, features or observations.
- Record normalization, imputation, filtering, annotation and reference versions.
- Use stable analysis, scope, claim, artifact, run, gate and decision IDs. Keep
  claims within the current hash-bound readiness report's intended use and
  `authorized_claim_classes`; `review` and `blocked` authorize no class.

## File safety

- Treat `data/raw/` as read-only. Never edit source data in place.
- Never place direct human identifiers, re-identification keys, credentials or
  access tokens in project documents, manifests, logs or prompts.
- Inspect before editing; preserve unrelated user changes.
- Do not overwrite, move or delete material files without clear authorization.
- Use project-relative paths or one configurable project root.
- Write reusable derived data to `data/processed/`, lightweight restartable
  intermediates to `results/intermediate/`, and curated final outputs to
  `results/tables/`, `results/figures/` or `results/reports/`.
- When a pipeline backend (for example an RNAseq-Templates runner) produces a
  complete native run bundle, keep that immutable bundle under
  `analysis/runs/<run_id>/` (created on demand by the run, not scaffolded) and
  copy only reviewed deliverables into `results/`. Do not duplicate the full
  native bundle under `results/`; `results/intermediate/` is for lightweight
  files, not a second copy of a run.
- Use one execution path per analysis: a CLI run bundle for batch/production,
  or a notebook for interactive exploration writing to
  `analysis/notebook_output/` (exploratory, regenerable, never curated into
  `results/`). Do not run a full bundle and a full notebook over the same
  inputs; `analysis/notebook_output/` is disposable.
- Back up before substantial notebook, script or canonical-document replacement.

## Reproducibility

- Prefer reusable scripts for final logic; notebooks may own exploration and
  review when inputs, parameters and execution order are explicit.
- Record deterministic seeds.
- Maintain environment/version information in `docs/REPRODUCIBILITY.md`.
- Distinguish planned analyses from successfully executed analyses in
  `PIPELINE.md`.
- Keep deliverables traceable to source data and generating code.
- Register actual runs in `provenance/RUNS.tsv` and artifacts in
  `provenance/ARTIFACTS.tsv`; hashes establish byte identity, not scientific
  validity.

## Project memory is part of done

After meaningful work:

- update `docs/PROJECT_STATUS.md` if state, blockers or next task changed;
- replace `docs/SESSION_HANDOFF.md` with a resumable handoff;
- append `docs/DECISION_LOG.md` for scientific/computational decisions;
- update `docs/DATA_DICTIONARY.md`, `docs/ANALYSIS_PLAN.md`, `PIPELINE.md`,
  `docs/READINESS.md`, `docs/RESULTS_SUMMARY.md` and provenance records only when
  their update trigger fires;
- add facts that require collaborator confirmation to
  `manuscript/AUTHOR_QUERIES.md` when that file exists.

Never erase decision history. Mark replaced interpretations `superseded` and
name the replacing decision or artifact.

## Verification and reporting

- Do not claim verification without running a relevant check.
- At handoff, report inspected and modified files, checks, failures, decisions,
  provenance/readiness changes, unresolved issues and the next minimal task.
