# Map an existing project without moving files

Use `PROJECT_MAP.json` when an established project's paths already have clear
owners. This is an authored local contract, `research-project-map/v1`; it is
neither a new layout version nor a general workflow-engine configuration.
A small combined working note is better served by the exploratory profile.

## Declare responsibilities

Start with [the synthetic example](../assets/examples/project-map.json), inspect
the real project, and replace the paths with verified locations:

```json
{
  "schema_version": "research-project-map/v1",
  "docs_root": "notes",
  "source_roots": ["src", "notebooks"],
  "raw_roots": ["inputs/raw"],
  "run_root": "outputs/runs",
  "results_root": "reports",
  "documents": {
    "docs/PROJECT_STATUS.md": "notes/current.md",
    "docs/SESSION_HANDOFF.md": "notes/next-session.md"
  }
}
```

All root fields are required. `source_roots` names authored code/notebooks;
`raw_roots` names original source bytes. Each is a nonempty list. Multiple
source roots are allowed when their responsibilities are clear. `run_root`
owns native execution bundles and `results_root` owns selected deliveries.
Declared roots need not exist yet; their absence proves neither missing data
nor successful execution.

`documents` is optional. It maps the known logical `docs/<NAME>.md` roles to
actual files; unspecified documents default to `docs_root/<NAME>.md`.
Supported names are PROJECT_BRIEF, PROJECT_STATUS, DECISION_LOG, TODO,
DATA_DICTIONARY, ANALYSIS_PLAN, SESSION_HANDOFF, PIPELINE, READINESS,
RESULTS_SUMMARY, REPRODUCIBILITY and DATA_GOVERNANCE (all `.md`).
Two roles cannot share a document; use exploratory notes when separate records
are unnecessary. To reuse an existing root `PIPELINE.md`, map that role
explicitly. Mapping does not rewrite or validate an existing document's content.

Paths must be normalized, non-hidden, project-relative and free of symlink
components. Root responsibilities cannot overlap. Documents cannot point into
raw inputs, code, runs, deliveries or reserved controls. Conflicts are checked
without case sensitivity to keep projects portable between filesystems.
Mapping is refused before writes when ownership conflicts; it does not repair
paths automatically.

## Use and audit

```bash
python scripts/scaffold_project.py /path/to/project --mode retrofit \
  --profile research --layout-map /path/to/map.json --json
python scripts/scaffold_project.py /path/to/project --mode retrofit \
  --profile research --layout-map /path/to/map.json --apply
python scripts/audit_project.py /path/to/project --json
```

The initial command is a dry run. Apply adds only missing controls and records
the map as `PROJECT_MAP.json`; it never replaces existing files. Retrofit does
not create declared source/raw/run roots or a second `workflows/` hierarchy.
Later scaffold and audit calls load the saved map automatically. For a read-only
preview, `audit_project.py --layout-map /path/to/map.json` uses the map without
saving it. The audit resolves document checks and scans mapped authored sources
for nonportable absolute paths; it does not scan raw data as executable code.

`build_source_manifest.py` defaults to saved `raw_roots`, otherwise `data/raw`.
An explicit `--include` replaces the default scope. Check scope and data access
before hashing; neither a valid map nor a checksum authenticates the source.

## Compatibility and limits

- Formal machine ledgers stay in `provenance/`; specifications and readiness
  records stay in `analysis/specs/` and `analysis/readiness/`. Root README,
  AGENTS and CLAUDE files and manuscript control files also keep their names.
  This version does not remap these contracts or relocate historical references.
- A saved map cannot silently be replaced by a different map. A project cannot
  combine it with fixed `provenance/PROJECT_LAYOUT.json` v2 ownership. Review
  and authorize a layout migration separately if either contract must change.
- `--layout-map` is unavailable with `--profile exploratory`, which intentionally
  has no formal root layout. Moving to a formal profile preserves the old notes.
- Third-party analysis backends do not automatically understand this map.
  Check their actual path/configuration support before execution. If a backend
  requires fixed v2, explain the incompatibility; mapping is not permission to
  move an existing project or claim unsupported execution.
- Mapping does not recover undocumented runs, perform scientific assessment,
  infer specimen identity, or make an existing project reproducible by itself.
