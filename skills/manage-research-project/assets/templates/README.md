# {{PROJECT_NAME}}

Project type: {{PROJECT_TYPE}}

Current stage: {{STAGE}}

## Objective

{{OBJECTIVE}}

## Start here

1. `docs/PROJECT_BRIEF.md`
2. `docs/PROJECT_STATUS.md`
3. `docs/ANALYSIS_PLAN.md`
4. `docs/READINESS.md` when present
5. `docs/PIPELINE.md` when present
6. `docs/SESSION_HANDOFF.md`

## Layout contract

This project uses `research-project-layout/v2`. Its four owned layers are:

    workflows/                 authored analysis source, grouped by workflow
    analysis/specs/            immutable or versioned analysis specifications
    analysis/readiness/        readiness declarations bound to specs and inputs
    analysis/runs/<run_id>/    complete immutable backend-native run bundles
    analysis/notebook_output/  optional scratch output; inspect before retiring
    results/                   reviewed deliverables by question or domain module
    provenance/                source, artifact, run and layout identities

Data have separate roles:

    data/raw/                  immutable source bytes
    data/metadata/             sample and design metadata
    data/processed/            deterministic reusable derived data
    data/references/           versioned reference resources

Create analysis source only under `workflows/<workflow_id>/`:

    workflows/<workflow_id>/
    ├── README.md
    ├── config/
    ├── scripts/
    ├── notebooks/
    └── backend.lock.json

Do not create parallel top-level `scripts/`, `notebooks/`, `analysis/scripts/`,
`analysis/config/`, or `analysis/notebooks/` source roots. A run ID is
namespaced as `<workflow_id>__<run_label>`.

## Output ownership

The backend may use its native internal layout inside
`analysis/runs/<run_id>/`. Treat that directory as one closed run bundle; its
internal module names do not define project navigation.

Curate reviewed artifacts using a documented question or domain-module layout.
For a question-oriented project:

    results/<question_id>/tables/
    results/<question_id>/figures/
    results/<question_id>/report/

For RNA-seq, `01_qc/`, `02_degs/`, `03_ORA/` and `04_GSEA/` can instead hold
`tables/` and `figures/`. Keep a current results index and source manifest;
include physical files and report assets so results can be shared independently.
Run-local intermediates stay in the native run.

The dependency backend is not project source. Record its cloneable source and
fixed revision in `workflows/<workflow_id>/backend.lock.json`, verify it before
execution, and materialize it outside the project. The authoritative layout
paths and backend policy are recorded in `provenance/PROJECT_LAYOUT.json`.

Use notebook or CLI to drive the same domain implementation into a native run.
Either can support formal delivery after input, execution and domain checks.
Do not rerun an entire pipeline merely to switch entry points; reuse verified
saved results for downstream changes and record the source run. Scratch output
may remain under `analysis/notebook_output/<workflow_id>/`; do not assume its
contents are disposable.

Unknown scientific or experimental details remain `TODO` items. Folder
completeness and successful execution do not imply scientific readiness.
