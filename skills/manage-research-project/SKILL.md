---
name: manage-research-project
description: Build and maintain an agent-ready scientific research workspace across its full lifecycle. Use when starting a research project, safely retrofitting an existing analysis directory, establishing reproducible bioinformatics or multi-omics structure, recording source/artifact/run provenance, indexing domain scientific-readiness reports, updating project memory after substantive work, auditing stale documentation or integrity, preparing a session handoff, or freezing a manuscript/archive snapshot. Triggers include project initialization, project organization, agent-ready structure, research project audit, 项目初始化, 项目整理, 持续记录, 项目交接, 项目归档, and 分析项目管理.
---

# Manage an Agent-Ready Research Project

Create durable project memory without turning agent instructions into a project
encyclopedia. Preserve existing work, distinguish evidence from interpretation,
and update documentation in the same session as the analysis it describes.

Unknown scientific facts must remain `TODO:` or enter `AUTHOR_QUERIES.md`. Never
invent sample counts, group identities, methods, file provenance, results, or
database versions.

This skill manages contracts and lineage; it is not a universal scientific
assessor. A passing structure audit does not establish scientific readiness. A
successful run does not establish validity, reproduction, causality or truth.
Scientific readiness must come from a named domain assessor using a versioned
gate policy and is always scoped to an intended use.

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

- Read [document-contract.md](references/document-contract.md) whenever creating
  or changing project state, results or handoff records. It defines
  responsibility-specific sources of truth, orthogonal states, ownership and
  legacy-state migration.
- Read [project-profiles.md](references/project-profiles.md) when tailoring the
  scaffold or analysis checklist to a modality.
- Read [readiness-contract.md](references/readiness-contract.md) when creating,
  validating, interpreting or staling a readiness declaration.
- Read [analysis-spec-contract.md](references/analysis-spec-contract.md) when
  creating or validating the generic spec envelope that binds project and
  domain analysis contracts.
- Read [provenance-contract.md](references/provenance-contract.md) for source
  baselines, checkpointing, result curation or archives; its generic
  `register_run.py` imports domain metadata into existing RUNS/ARTIFACTS records
  without creating a scientific readiness declaration.
- Read [human-data-and-access.md](references/human-data-and-access.md) only for
  human, clinical, controlled-access or otherwise sensitive data.
- Read [retrofit-and-archive.md](references/retrofit-and-archive.md) for
  `retrofit` or `archive`.
- Read [layout-contract.md](references/layout-contract.md) when initializing a
  project, selecting executable paths, composing with an analysis skill, or
  auditing multiple source/result roots.

## Phase 1 — Inspect before asking

1. Resolve the exact target directory.
2. Inspect existing `AGENTS.md`, `CLAUDE.md`, README, docs, workflows, legacy
   notebooks/scripts, data directories, results, manifests and environment
   files.
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
Apply uses directory-relative, no-follow creation to prevent symlink path
escape. On platforms without the required `dir_fd` and `O_NOFOLLOW` support,
the helper safely refuses `--apply`; dry-run inspection remains available.

Profiles:

- `minimal`: agent rules, core project memory and safe data/result directories.
- `research` (default): minimal plus pipeline, results summary,
  reproducibility, readiness and run/artifact registries.
- `manuscript`: research plus author queries and figure/source manifests.

Safety rules:

- Never overwrite an existing file.
- Never modify anything under `data/raw/`.
- Never reorganize an established project unless the user explicitly requests
  that separate action.
- Prefer documenting the existing layout over forcing the template layout.
- New projects use `research-project-layout/v2`: authored source is owned only
  by `workflows/<workflow_id>/`, native runs by `analysis/runs/<run_id>/`,
  reviewed deliverables by `results/` and lineage by
  `provenance/`. The scaffold records these roots in
  `provenance/PROJECT_LAYOUT.json`.
- Retrofit does not create a v2 layout manifest or a speculative `workflows/`
  root. Treat a project without `PROJECT_LAYOUT.json` as legacy until a
  separate migration is explicitly approved.
- For computational backends, keep each complete native run bundle under
  `analysis/runs/<run_id>/` and only curated deliverables under `results/`
  (the two-layer contract used by the analysis skills). The scaffold creates
  `results/`; `analysis/runs/` is created by the pipeline on first run.
- Notebook and CLI are both valid formal entry points when the domain workflow
  records inputs, parameters, execution order, environment and validation in a
  native run. Honor the user's entry preference; do not require notebook logic
  to be copied into a script or rerun solely for curation. The optional legacy
  `analysis/notebook_output/<workflow_id>/` path is for scratch work; inspect
  provenance before promoting outputs and never assume it is safe to delete.
- Let the domain and user choose question or module folders within `results/`.
  A delivery may include complete reviewed modules plus a focused report.
  Register intentional delivery copies and their source files; make shared
  results readable without access to the native run. Keep one current delivery
  index instead of accumulating `v*` navigation directories.
- Keep backend repositories outside the project. A workflow binds a cloneable
  source and fixed revision in `workflows/<workflow_id>/backend.lock.json`;
  do not create project-local backend worktrees.
- Back up before replacing instructions or retiring a canonical document.
- Use relative project paths in generated docs and code.
- If the project lives in a cloud-synced folder (iCloud Drive, Dropbox,
  OneDrive), judge run completion by the expected output files on disk, not by
  exit code or the synced file listing — sync can lag, evict, or revert files.
  Confirm key outputs exist before declaring success, and re-check a file that
  looks missing before assuming a step failed.
- The research scaffold creates `analysis/specs/`, `analysis/readiness/` and
  `provenance/`. It does not create a scientific readiness declaration or claim
  that the project is ready.

## Phase 3 — Establish the project contract

After scaffolding, populate only facts supported by the project:

1. `PROJECT_BRIEF.md`: stable meaning, design and constraints.
2. `DATA_DICTIONARY.md`: data inventory, sample mapping and transformation state.
3. `ANALYSIS_PLAN.md`: planned comparisons, statistical units, validation and
   risks.
4. `PROJECT_STATUS.md`: current state and one next minimal executable task.
5. `docs/PIPELINE.md`: actual entry points, dependencies, outputs and execution
   status—not the intended workflow alone.
6. `REPRODUCIBILITY.md`: environment, versions, commands and unresolved gaps.
7. `READINESS.md`: index only domain-assessor declarations by intended use;
   never self-promote a structure audit to readiness.
8. `provenance/ARTIFACTS.tsv` and `provenance/RUNS.tsv`: register actual
   artifact lineage and executions using stable IDs. For each analysis, make
   the spec's data requirement and entry points explicit; bind every entry
   point in the code manifest, every run input/output/validation ID to an
   artifact row, propagate assessed source IDs through those artifacts, and
   bind every output artifact back to its generating run.

For data-bearing projects, establish a non-overwriting source-integrity baseline
after confirming its scope and access rules:

```bash
python scripts/build_source_manifest.py /path/to/project --json
python scripts/build_source_manifest.py /path/to/project --apply \
  --source-system GEO --source-reference GSE12345 \
  --acquired-at 2026-09-03T00:00:00Z --data-freeze-id GSE12345-2026-09-03
python scripts/verify_source_manifest.py /path/to/project --json
```

The metadata above are illustrative. Replace them with verified source values;
omit an unknown optional value instead of copying an example or writing a
placeholder into a machine contract.

The builder defaults to `data/raw/`, hashes regular files, rejects unsafe paths
and symlinks, and refuses to overwrite an existing baseline. A checksum proves
byte identity, not provenance authenticity or scientific validity.

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
5. Update `ANALYSIS_PLAN.md` and `docs/PIPELINE.md` when planned or actual logic
   changed.
6. Add current findings to `RESULTS_SUMMARY.md` with quantitative support,
   artifact/run IDs, scope and intended use, requested and authorized claim
   classes, target and achieved validation levels, a hash-bound readiness
   report, claim authorization and boundary—including important null or
   conflicting results.
7. Update artifact/run/figure/source records when an input, execution or
   deliverable is created, selected, superseded or archived. Readiness evidence
   that cites an artifact, run or decision must include the canonical record
   SHA-256; do not treat a recomputed digest as a substitute for required row
   content or lineage closure. Run evidence additionally binds its log SHA-256
   and the exact record digest of every input, output and validation artifact.
8. Add unresolvable experimental or reporting facts to `AUTHOR_QUERIES.md`.

When a known backend defect may affect existing results, follow the correction
procedure in [retrofit-and-archive.md](references/retrofit-and-archive.md).
Ask the domain workflow to establish the affected scope; preserve old bytes,
record the correction and parent lineage, and update only dependent claims and
delivery selections. Directory compliance cannot clear a numerical concern.
9. Mark affected declarations `currency_status=stale` when any bound input,
   analysis spec, gate policy, code manifest, environment snapshot, backend or
   dependency changes. Do not rewrite their historical `readiness_status`.

Do not rewrite append-only history. Mark replaced conclusions `superseded` and
link the decision/artifact that replaced them. Do not automatically translate a
legacy `confirmed` or `supported` label into a stronger current claim.

## Phase 5 — Audit

Run:

```bash
python scripts/audit_project.py /path/to/project --profile research
```

Use `--json` for machine-readable output and `--strict` when warnings should
fail CI. The audit checks required files, stale status/handoff dates, unresolved
TODOs, raw-data protection, old absolute paths in active source cells, and
manifest targets. When a source manifest exists, it also verifies its contract
and current bytes.

The audit output separates `structure_status`, `source_integrity` and
`scientific_readiness`. `scientific_readiness` is always `not_assessed` here.
To validate a domain declaration without redoing its science, run:

```bash
python scripts/validate_readiness.py /path/to/project \
  analysis/readiness/A-001.json --require-ready \
  --current-code-revision COMMIT_OR_SNAPSHOT \
  --current-code-dirty false \
  --current-backend-revision BACKEND_VERSION --json
```

Interpret `declared_ready_and_current` literally: it is a current,
policy-conformant declaration, not an independent scientific certificate. Read
the assessor's gate policy and evidence before relying on it.

An audit request authorizes read-only inspection, not broad reorganization.
Repair only bounded, supported issues; report everything else as an open item.

## Phase 6 — Archive or hand off

For a phase freeze:

1. Reconcile `PROJECT_STATUS.md`, `RESULTS_SUMMARY.md`, `DECISION_LOG.md`,
   `docs/PIPELINE.md`, `REPRODUCIBILITY.md` and manifests.
2. Record executed versus merely planned analyses.
3. Freeze exact source/artifact IDs, run records, analysis specs, code revision
   and dirty state, environment/backend versions, readiness records and open
   author queries.
4. Record snapshot ID, parent snapshot, included/excluded scope and hashes, then
   verify the copied snapshot.
5. Copy or package recoverably; do not move the live project or raw data.
   Reference restricted raw data rather than copying it unless authorized.
6. Generate a restart prompt that names the next task and required reading but
   contains no credentials or direct identifiers.

Follow [retrofit-and-archive.md](references/retrofit-and-archive.md) for the
snapshot checklist.

## Scientific integrity rules

- State the experimental unit before statistical testing.
- Separate technical replicates, biological replicates, samples, cells and
  features. List the declared unit hierarchy from the independent level toward
  nested observations and require the named independent and observation units
  to occur in it; domain review must still test whether independence is true.
- Record comparisons, models, covariates, thresholds and multiple-testing rules.
- Separate source provenance, source integrity, implementation, execution,
  technical validation, readiness, contract, currency, policy, analysis mode,
  claim authorization, target/achieved validation, lifecycle and reproduction
  states.
- Do not infer causality from association, enrichment, co-purification,
  correlation or cross-omics concordance alone.
- Keep exploratory and confirmatory outputs visibly distinct.
- Bind each readiness assessment to one intended use, exact source IDs,
  analysis spec, gate policy, code manifest, environment snapshot and relevant
  backend. Require policy assessor name/version and domain to match, and policy
  applicability to include the spec study type and explicit data requirement.
- Require data-bearing specs to bind source IDs, a domain spec and domain
  parameters; a data-free declaration is valid only with no source IDs and a
  null domain spec. The generic validator cannot infer a false declaration
  from prose, so the domain assessor must check semantic truth.
- Require evidence runs to match the assessed spec, declared entry point, code
  state, backend and environment; close their artifact IDs and logs before
  using them for `PASS` or `NA`.
- Require a domain-specific gate policy; do not invent generic statistical
  approval rules inside this project-management skill.
- Report limitations that could change the conclusion near that conclusion.
- Preserve raw identifiers and explicit mappings to public/display labels.
- For human data, preserve subject → specimen → library/capture → observation
  hierarchy without recording direct identifiers or re-identification keys.

## Output contract

At the end of any mode, report:

1. selected mode and target;
2. files inspected, created, updated, skipped and backed up;
3. verified project facts versus TODOs/author queries;
4. decisions, provenance records and orthogonal state changes;
5. checks run and their outcomes;
6. structure/source-integrity status and readiness by intended use, explicitly
   separating readiness (`not_assessed`, `ready`, `review`, `blocked`) from
   currency (`not_assessed`, `current`, `unknown`, `stale`), contract and policy
   status;
7. next minimal executable task;
8. copy-paste restart prompt.

Do not claim the project is reproducible merely because folders exist. A
reproducible project must expose current inputs, code, parameters, environment,
execution state, outputs and provenance.

## Validation before completion

- Run `scripts/audit_project.py`.
- Validate Markdown links or manifest targets that were added.
- Confirm existing files were not overwritten.
- Confirm `data/raw/` was not modified.
- Confirm `PROJECT_STATUS.md` and `SESSION_HANDOFF.md` agree on the next task.
- Confirm each new finding has source artifact/run IDs, uncertainty, scope and
  intended use, requested and authorized claim classes, claim authorization,
  target and achieved validation levels, lifecycle and a hash-bound readiness
  reference.
- Confirm planned and executed analyses are not conflated.
- Verify the source manifest when present and validate any readiness report used
  to gate execution or curation.
- Confirm spec/input/code/environment/backend changes did not leave a stale
  readiness declaration marked current.
- Confirm archive completion is not described as reproduction or validation.
- For script or notebook changes, run syntax/parse checks and proportional
  execution tests.
