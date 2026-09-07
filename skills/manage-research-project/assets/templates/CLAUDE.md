@AGENTS.md

# Claude Code entry

Follow `AGENTS.md`. This file is a compact operational entry, not the project
database.

Before substantive work, read:

1. `docs/PROJECT_BRIEF.md`
2. `docs/PROJECT_STATUS.md`
3. `docs/DATA_DICTIONARY.md`
4. `docs/DECISION_LOG.md`
5. `docs/SESSION_HANDOFF.md`

Read `docs/ANALYSIS_PLAN.md`, `docs/PIPELINE.md`, `docs/RESULTS_SUMMARY.md`, and
`docs/REPRODUCIBILITY.md` when relevant and present. Before relying on an
analysis, read `docs/READINESS.md`, its linked machine report, and the matching
entries in `provenance/ARTIFACTS.tsv` and `provenance/RUNS.tsv`.

Inspect existing files before creating alternatives. Do not modify
`data/raw/`. Prefer bounded edits and existing canonical scripts. Validate
Notebook JSON/source cells or script syntax after edits. Update project memory
in the same session as the work it records. Never infer scientific readiness
from a passing structure audit or scientific validity from successful execution.

For a v2 project, keep authored analysis source under
`workflows/<workflow_id>/`; do not create parallel top-level or `analysis/`
source roots. Keep backend source outside the project and bind it with the
workflow's `backend.lock.json`.

Notebook and CLI can both be formal entries after domain validation. Use shared
steps, record a native run, and do not require a duplicate script execution to
deliver notebook results. Let results navigation follow the domain and user;
include portable physical files with source-run provenance.
