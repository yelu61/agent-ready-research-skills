# Research project layout contract v2

## Ownership model

A v2 project has four non-overlapping layers:

1. `workflows/` owns human-authored executable analysis source.
2. `analysis/` owns immutable specifications, readiness records, native runs
   and optional scratch notebook output.
3. `results/` owns reviewed deliverables grouped by question or domain module.
4. `provenance/` owns source, layout, artifact and execution identity.

The data layer is orthogonal: source bytes belong in `data/raw/`, metadata in
`data/metadata/`, deterministic reusable derived data in `data/processed/`,
and frozen external references in `data/references/`.

## Workflow contract

Use one stable lowercase kebab-case workflow ID. Authored files belong only
under:

    workflows/<workflow_id>/
    ├── README.md
    ├── config/
    ├── scripts/
    ├── notebooks/
    └── backend.lock.json

Do not create top-level `scripts/` or `notebooks/`, or `analysis/config/`,
`analysis/scripts/` or `analysis/notebooks/`. A project may contain multiple
workflow directories, but each executable entry point has one owner.

The backend lock records a cloneable source and immutable revision. Backend
source is materialized outside the project; it is not a second project
framework and must not be stored under `analysis/backend/`.

## Execution contract

Formal notebook and CLI runs use:

    analysis/runs/<workflow_id>__<run_label>/

The run is one immutable backend-native bundle. Names such as `0-Config`,
`1-DEG` or `3-Visualization` may exist inside it and do not define project
navigation. Run-local checkpoints and intermediates remain inside that run.

Notebook source stays under the workflow; generated outputs and execution
records belong to the native run. Validate the notebook from a clean kernel
and retain configuration, environment, execution order and provenance. A
script conversion or second full CLI run is not a prerequisite for delivery.
`analysis/notebook_output/<workflow_id>/` remains an optional scratch path for
legacy compatibility, not a required second output tree or a deletion policy.

## Curated results contract

Choose first-level folders for the audience: scientific question IDs or domain
modules, for example RNA-seq `01_qc/`, `02_degs/`, `03_ORA/`, `04_GSEA/`.
Question-oriented projects may keep:

    results/<question_id>/
    ├── tables/
    ├── figures/
    └── report/

Document the chosen layout once in `results/README.md` or its HTML index.
Complete reviewed modules and selected headline findings can coexist; source
intermediates stay in native runs. Register delivery copies as distinct
artifacts linked to their native source. Use physical files and relative report
resources so the delivery remains usable after copying outside the project.
Source-run paths belong in provenance; they must not be needed to open results.

## Layout identity and compatibility

New projects declare v2 in `provenance/PROJECT_LAYOUT.json`. The manifest
contains the canonical roots, run-ID pattern and backend policy. Agents and
domain skills must read it before choosing project paths.

Projects without that manifest are legacy layouts. Audit them against their
existing canonical entry points. Retrofit may add missing governance records
but must not create `workflows/`, move files or synthesize a v2 manifest.
Migration is a separate, explicitly approved operation.
