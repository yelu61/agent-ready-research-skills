# {{PROJECT_NAME}}

Project type: {{PROJECT_TYPE}}

Current stage: {{STAGE}}

## Objective

{{OBJECTIVE}}

## Start here

1. `docs/PROJECT_BRIEF.md`
2. `docs/PROJECT_STATUS.md`
3. `docs/ANALYSIS_PLAN.md`
4. `PIPELINE.md` when present
5. `docs/SESSION_HANDOFF.md`

## Directory responsibilities

```text
data/raw/             immutable source data
data/processed/       derived reusable data
data/metadata/        sample and design metadata
notebooks/            reviewable analysis notebooks
scripts/              reusable pipeline logic
analysis/runs/        native per-run bundles from pipeline backends (created on demand)
results/intermediate/ lightweight restartable intermediates
results/tables/       curated final analytical tables
results/figures/      curated final analytical figures
results/reports/      durable reports
docs/                 project memory and provenance
```

`analysis/runs/<run_id>/` holds the complete, immutable output of one pipeline
run (native tables, figures, config snapshot, logs). `results/` holds only
reviewed deliverables curated from those runs. `analysis/runs/` is created by
the pipeline when it first executes; it is not part of the empty scaffold.

Unknown scientific or experimental details are marked `TODO:` and must not be
treated as confirmed.
