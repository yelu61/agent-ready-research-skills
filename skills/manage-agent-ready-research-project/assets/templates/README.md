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
results/intermediate/ restartable intermediate outputs
results/tables/       final analytical tables
results/figures/      final analytical figures
results/reports/      durable reports
docs/                 project memory and provenance
```

Unknown scientific or experimental details are marked `TODO:` and must not be
treated as confirmed.
