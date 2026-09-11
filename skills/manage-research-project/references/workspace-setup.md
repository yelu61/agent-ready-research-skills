# Initialize or adapt a research workspace

## Choose a proportionate profile and layout

When tailoring records or an audit checklist to a modality, read
[Scientific project profiles](project-profiles.md). These are record/audit
prompts, not instructions to select scientific methods or execute analyses.

Directory names are conventions, not a scientific quality standard. Inspect
existing ownership and the intended use before choosing a scaffold:

| Need | Profile and layout |
|---|---|
| Small question, pilot or short exploration | `exploratory`: four root memory files, no new directories; keep current paths |
| Sustained analysis with several runs or collaborators | `research`: explicit records for design, execution, provenance and handoff |
| Manuscript or formal delivery | `manuscript`: research records plus figure/source manifests and author queries |
| Compatibility with an older compact formal scaffold | `minimal`: retains its existing document/data structure; it is larger than exploratory |

For an established project, preserve its layout. When existing paths differ
from defaults, use [project-map.md](project-map.md) to map document,
source, raw-input, run and delivery responsibilities. Do not add a second
`docs/`, `workflows/` or results tree merely to satisfy a template. The fixed v2
layout is the default for a new formal project with no explicit mapping; it is
not required for every research activity.

For exploratory work, read [exploratory-profile.md](exploratory-profile.md)
and use `PROJECT_NOTES.md` for the question, inputs, actual actions, observations,
limits/decisions and next step. The formal document/registry requirements below
apply when those responsibilities are needed; do not generate a full readiness
package for a pilot checkpoint. Scientific uncertainty still stays explicit.

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

Select `--profile exploratory` for the four-file profile. The CLI keeps
`research` as its compatibility default; choose the profile deliberately.
For an existing custom layout, supply `--mode retrofit --layout-map map.json`
on the first scaffold. Apply saves `PROJECT_MAP.json`; subsequent scaffold and
audit calls read it automatically. An audit can inspect an external map with
`--layout-map` without saving it. Review a map before use; never infer its
ownership from similar filenames alone.

Safety rules:

- Never overwrite an existing file.
- Never modify source bytes under `data/raw/` or declared mapped raw roots.
- Never reorganize an established project unless the user explicitly requests
  that separate action.
- Prefer documenting the existing layout over forcing the template layout.
- New formal projects without a custom map use `research-project-layout/v2`: authored source is owned only
  by `workflows/<workflow_id>/`, native runs by `analysis/runs/<run_id>/`,
  reviewed deliverables by `results/` and lineage by
  `provenance/`. The scaffold records these roots in
  `provenance/PROJECT_LAYOUT.json`.
- Retrofit does not create a v2 layout manifest or a speculative `workflows/`
  root. An explicit `PROJECT_MAP.json` owns mapped paths; projects with neither
  manifest remain legacy. Both manifests cannot own one project simultaneously.
  Mapping records ownership without moving files or migrating a layout version.
- For computational backends, keep each complete native run bundle under
  `analysis/runs/<run_id>/` and only curated deliverables under `results/`
  in fixed v2, or under the declared mapped roots. The scaffold creates
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
  in mapped/legacy projects use the existing canonical source location instead.
  Do not create project-local backend worktrees. A domain backend must explicitly
  support any custom run paths; a manager map does not configure that backend.
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

For exploratory work, fill the corresponding sections of `PROJECT_NOTES.md`
from evidence and stop when the next task is resumable. For formal projects,
document names below denote roles; resolve their actual locations from the map.
Formal machine ledgers remain under `provenance/`, with specs/readiness under
`analysis/specs/` and `analysis/readiness/`; these paths are not remapped.

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

The builder defaults to saved map `raw_roots`, otherwise `data/raw/`;
`--include` explicitly replaces that scope. It hashes regular files, rejects unsafe paths
and symlinks, and refuses to overwrite an existing baseline. A checksum proves
byte identity, not provenance authenticity or scientific validity.

For single-cell, spatial or multi-omics identity records, optionally run:

```bash
python scripts/validate_sample_map.py --measurements measurements.tsv \
  --pairs declared-pairs.tsv --json
```

Retain original pseudonymous IDs and explicit matching evidence. Unpaired or
partially overlapping assays are allowed. Equal barcodes, nearby sections or
similar expression do not establish the same cell. Exit 0 means declared
records are structurally consistent; 1 requests review and 2 identifies invalid
records. Identity authenticity and scientific validity remain unassessed.

Keep behavior in `AGENTS.md`/`CLAUDE.md`; keep science and task state out of
those instruction files.
