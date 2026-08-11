# Project-wide agent instructions

## Read before work

Read `README.md`, `docs/PROJECT_BRIEF.md`, `docs/PROJECT_STATUS.md`,
`docs/ANALYSIS_PLAN.md`, and `docs/SESSION_HANDOFF.md`. Read
`docs/DATA_DICTIONARY.md` before using data and `docs/DECISION_LOG.md` before
changing established logic.

## Scientific integrity

- Protect scientific integrity over speed.
- Separate confirmed facts, supported interpretations, exploratory findings,
  superseded conclusions and unresolved questions.
- State the experimental unit, comparison, model/test, covariates, cutoff and
  multiple-testing rule.
- Report effect sizes and uncertainty when applicable.
- Do not infer causality from association, enrichment, correlation,
  co-purification or cross-omics concordance alone.
- Do not silently exclude samples, cells, features or observations.
- Record normalization, imputation, filtering, annotation and reference versions.

## File safety

- Treat `data/raw/` as read-only. Never edit source data in place.
- Inspect before editing; preserve unrelated user changes.
- Do not overwrite, move or delete material files without clear authorization.
- Use project-relative paths or one configurable project root.
- Write reusable derived data to `data/processed/`, intermediate results to
  `results/intermediate/`, and final outputs to `results/tables/`,
  `results/figures/` or `results/reports/`.
- Back up before substantial notebook, script or canonical-document replacement.

## Reproducibility

- Prefer reusable scripts for final logic; notebooks may own exploration and
  review when inputs, parameters and execution order are explicit.
- Record deterministic seeds.
- Maintain environment/version information in `docs/REPRODUCIBILITY.md`.
- Distinguish planned analyses from successfully executed analyses in
  `PIPELINE.md`.
- Keep deliverables traceable to source data and generating code.

## Project memory is part of done

After meaningful work:

- update `docs/PROJECT_STATUS.md` if state, blockers or next task changed;
- replace `docs/SESSION_HANDOFF.md` with a resumable handoff;
- append `docs/DECISION_LOG.md` for scientific/computational decisions;
- update `docs/DATA_DICTIONARY.md`, `docs/ANALYSIS_PLAN.md`, `PIPELINE.md`,
  `docs/RESULTS_SUMMARY.md` and manifests only when their update trigger fires;
- add facts that require collaborator confirmation to
  `manuscript/AUTHOR_QUERIES.md` when that file exists.

Never erase decision history. Mark replaced interpretations `superseded`.

## Verification and reporting

- Do not claim verification without running a relevant check.
- At handoff, report inspected and modified files, checks, failures, decisions,
  evidence-state changes, unresolved issues and the next minimal task.
