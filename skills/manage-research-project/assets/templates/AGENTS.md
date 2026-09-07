# Project-wide agent instructions

## Read before work

For project work, start with `docs/PROJECT_STATUS.md` and
`docs/SESSION_HANDOFF.md`. Load `README.md` and `docs/PROJECT_BRIEF.md` when
project context is needed, `docs/ANALYSIS_PLAN.md` before analysis changes,
`docs/DATA_DICTIONARY.md` before using data, and the relevant
`docs/DECISION_LOG.md` entries before changing established logic.
For a narrow documentation or configuration edit, read only the sections
needed to preserve its meaning; do not reload unrelated analysis material.

Read `docs/READINESS.md` and the named readiness report before treating an
analysis as ready. Read `docs/DATA_GOVERNANCE.md` when present and honor its
access boundaries.

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
- Write reusable deterministic derived data to `data/processed/`. Keep
  run-local intermediates inside the native run, and curate reviewed outputs
  under `results/` using question or domain-module navigation.
- Keep authored analysis source under `workflows/<workflow_id>/`. Do not create
  parallel top-level `scripts/` or `notebooks/`, or source roots under
  `analysis/`.
- When a pipeline backend (for example an RNAseq-Templates runner) produces a
  complete native run bundle, keep that immutable bundle under
  `analysis/runs/<run_id>/` (created on demand by the run, not scaffolded) and
  copy reviewed deliverables into the agreed layout under `results/`.
  Do not duplicate the full native bundle under `results/`.
- Do not put a backend checkout or worktree inside the project. Record a
  cloneable source and fixed revision in
  `workflows/<workflow_id>/backend.lock.json`, verify it before execution, and
  materialize it outside the project.
- Notebook and CLI may both generate formal native runs. Honor the user's
  preference and use shared domain steps; do not duplicate a complete run to
  switch entry points. Validate execution order, configuration and provenance
  before delivery. Scratch notebook output is not automatically disposable.
- Deliver complete reviewed modules plus a focused report when requested.
  Register intentional copies; shared results must open independently of
  `analysis/runs/`, using relative links and included report resources.
- Back up before substantial notebook, script or canonical-document replacement.

## Reproducibility

- Keep reusable domain logic in shared functions. Scripts and notebooks call
  those functions; project-specific code is reserved for project-specific work.
- Record deterministic seeds.
- Maintain environment/version information and backend locks in
  `docs/REPRODUCIBILITY.md`.
- Distinguish planned analyses from successfully executed analyses in
  `docs/PIPELINE.md`.
- Keep deliverables traceable to source data and generating code.
- Register actual runs in `provenance/RUNS.tsv` and artifacts in
  `provenance/ARTIFACTS.tsv`; hashes establish byte identity, not scientific
  validity.

## Project memory is part of done

After meaningful work:

- update `docs/PROJECT_STATUS.md` if state, blockers or next task changed;
- replace `docs/SESSION_HANDOFF.md` with a resumable handoff;
- append `docs/DECISION_LOG.md` for scientific/computational decisions;
- update `docs/DATA_DICTIONARY.md`, `docs/ANALYSIS_PLAN.md`, `docs/PIPELINE.md`,
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
