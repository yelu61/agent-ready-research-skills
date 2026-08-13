---
name: manage-research-project
description: Build and maintain an agent-ready scientific research workspace across its full lifecycle. Use when starting a research project, safely retrofitting an existing analysis directory, establishing reproducible bioinformatics or multi-omics structure, updating project memory after substantive work, auditing stale documentation or provenance, preparing a session handoff, or freezing a manuscript/archive snapshot. Triggers include project initialization, project organization, agent-ready structure, research project audit, 项目初始化, 项目整理, 持续记录, 项目交接, 项目归档, and 分析项目管理.
---

# Manage an Agent-Ready Research Project

Create durable project memory without turning agent instructions into a project
encyclopedia. Preserve existing work, distinguish evidence from interpretation,
and update documentation in the same session as the analysis it describes.

Unknown scientific facts must remain `TODO:` or enter `AUTHOR_QUERIES.md`. Never
invent sample counts, group identities, methods, file provenance, results, or
database versions.

## Select one operating mode

| Mode | Use when | Primary outcome |
|---|---|---|
| `init` | A new project path is empty or nearly empty | Safe scaffold and first executable task |
| `retrofit` | Analysis files already exist | Current layout documented; missing controls added without reorganization |
| `checkpoint` | Meaningful analysis or writing just changed | Status, handoff, decisions, evidence and manifests updated |
| `audit` | The project may be stale, inconsistent or hard to resume | Evidence-backed gap report and bounded repair |
| `archive` | A phase, manuscript version or handoff is being frozen | Immutable snapshot manifest and explicit open issues |

If the user does not name a mode, inspect the target first and choose the least
destructive mode. A populated directory defaults to `retrofit`, never `init`.

## Load only relevant references

- Read [document-contract.md](references/document-contract.md) for every mode
  except a structure-only audit. It defines sources of truth, document ownership,
  evidence states and update triggers.
- Read [project-profiles.md](references/project-profiles.md) when tailoring the
  scaffold or analysis checklist to a modality.
- Read [retrofit-and-archive.md](references/retrofit-and-archive.md) for
  `retrofit` or `archive`.

## Phase 1 — Inspect before asking

1. Resolve the exact target directory.
2. Inspect existing `AGENTS.md`, `CLAUDE.md`, README, docs, notebooks, scripts,
   data directories, results, manifests and environment files.
3. Determine whether the directory is new, established or manuscript-stage.
4. Infer stable facts only from files or explicit user statements.
5. Ask only for a missing choice that changes the scaffold or scientific
   meaning. For a new project, target path is mandatory; project name, type,
   objective and stage may remain `TODO:` if the user prefers.

Do not ask for information that can be discovered locally. Do not postpone safe
work merely because optional metadata are unknown.

## Phase 2 — Initialize or retrofit safely

Use the deterministic scaffold script for missing files:

```bash
python scripts/scaffold_project.py /path/to/project \
  --profile research \
  --project-name "Project name" \
  --project-type "bulk RNA-seq + proteomics" \
  --objective "Main scientific question"
```

The command is a dry run by default. Review its plan, then rerun with `--apply`.

Profiles:

- `minimal`: agent rules, core project memory and safe data/result directories.
- `research` (default): minimal plus pipeline, results summary, reproducibility
  record and reusable review prompts.
- `manuscript`: research plus author queries and figure/source manifests.

Safety rules:

- Never overwrite an existing file.
- Never modify anything under `data/raw/`.
- Never reorganize an established project unless the user explicitly requests
  that separate action.
- Prefer documenting the existing layout over forcing the template layout.
- For computational backends, keep each complete native run bundle under
  `analysis/runs/<run_id>/` and only curated deliverables under `results/`
  (the two-layer contract used by the analysis skills). The scaffold creates
  `results/`; `analysis/runs/` is created by the pipeline on first run.
- Back up before replacing instructions or retiring a canonical document.
- Use relative project paths in generated docs and code.

## Phase 3 — Establish the project contract

After scaffolding, populate only facts supported by the project:

1. `PROJECT_BRIEF.md`: stable meaning, design and constraints.
2. `DATA_DICTIONARY.md`: data inventory, sample mapping and transformation state.
3. `ANALYSIS_PLAN.md`: planned comparisons, statistical units, validation and
   risks.
4. `PROJECT_STATUS.md`: current state and one next minimal executable task.
5. `PIPELINE.md`: actual entry points, dependencies, outputs and execution
   status—not the intended workflow alone.
6. `REPRODUCIBILITY.md`: environment, versions, commands and unresolved gaps.

Keep behavior in `AGENTS.md`/`CLAUDE.md`; keep science and task state out of
those instruction files.

## Phase 4 — Checkpoint after meaningful work

Treat documentation as part of the task's definition of done. Update only the
documents whose trigger fired:

1. Update `PROJECT_STATUS.md` when completed work, blockers or next task changed.
2. Replace `SESSION_HANDOFF.md` with the current resumable state.
3. Append to `DECISION_LOG.md` when a threshold, model, exclusion, annotation,
   reference, interpretation or deliverable choice was made.
4. Update `DATA_DICTIONARY.md` when data, fields, IDs, missing encodings or
   transformation state changed.
5. Update `ANALYSIS_PLAN.md` and `PIPELINE.md` when planned or actual logic
   changed.
6. Add verified findings to `RESULTS_SUMMARY.md` with source files and evidence
   state.
7. Update figure/source manifests when a deliverable is created, selected,
   superseded or archived.
8. Add unresolvable experimental or reporting facts to `AUTHOR_QUERIES.md`.

Do not rewrite append-only history. Mark replaced conclusions `superseded` and
link the decision that replaced them.

## Phase 5 — Audit

Run:

```bash
python scripts/audit_project.py /path/to/project --profile research
```

Use `--json` for machine-readable output and `--strict` when warnings should
fail CI. The audit checks required files, stale status/handoff dates, unresolved
TODOs, raw-data protection, old absolute paths in active source cells, and
manifest targets.

An audit request authorizes read-only inspection, not broad reorganization.
Repair only bounded, supported issues; report everything else as an open item.

## Phase 6 — Archive or hand off

For a phase freeze:

1. Reconcile `PROJECT_STATUS.md`, `RESULTS_SUMMARY.md`, `DECISION_LOG.md`,
   `PIPELINE.md`, `REPRODUCIBILITY.md` and manifests.
2. Record executed versus merely planned analyses.
3. Freeze exact source files, code entry points, environment/version information
   and open author queries.
4. Copy or package recoverably; do not move the live project or raw data.
5. Generate a restart prompt that names the next task and required reading.

Follow [retrofit-and-archive.md](references/retrofit-and-archive.md) for the
snapshot checklist.

## Scientific integrity rules

- State the experimental unit before statistical testing.
- Separate technical replicates, biological replicates, samples, cells and
  features.
- Record comparisons, models, covariates, thresholds and multiple-testing rules.
- Separate `confirmed`, `supported`, `exploratory`, `superseded` and `blocked`
  evidence.
- Do not infer causality from association, enrichment, co-purification,
  correlation or cross-omics concordance alone.
- Keep exploratory and confirmatory outputs visibly distinct.
- Report limitations that could change the conclusion near that conclusion.
- Preserve raw identifiers and explicit mappings to public/display labels.

## Output contract

At the end of any mode, report:

1. selected mode and target;
2. files inspected, created, updated, skipped and backed up;
3. confirmed facts versus TODOs/author queries;
4. decisions logged and evidence states changed;
5. checks run and their outcomes;
6. next minimal executable task;
7. copy-paste restart prompt.

Do not claim the project is reproducible merely because folders exist. A
reproducible project must expose current inputs, code, parameters, environment,
execution state, outputs and provenance.

## Validation before completion

- Run `scripts/audit_project.py`.
- Validate Markdown links or manifest targets that were added.
- Confirm existing files were not overwritten.
- Confirm `data/raw/` was not modified.
- Confirm `PROJECT_STATUS.md` and `SESSION_HANDOFF.md` agree on the next task.
- Confirm each new result claim has a source and evidence state.
- Confirm planned and executed analyses are not conflated.
- For script or notebook changes, run syntax/parse checks and proportional
  execution tests.
