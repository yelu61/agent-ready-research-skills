# Exploratory profile

Use `--profile exploratory` for a small question, pilot analysis or short-lived
exploration whose history fits in one working note. This profile adds exactly
four root files and no directories:

- `README.md`: project entrance and question;
- `AGENTS.md`: concise working and scientific-integrity agreements;
- `CLAUDE.md`: points to the same agreements;
- `PROJECT_NOTES.md`: question, inputs, actions/runs, observations,
  limits/decisions and next step.

The notes declare `<!-- research-project-profile: exploratory/v1 -->`.
`exploratory/v1` is a profile marker, **not** a layout version or scientific
readiness schema. Keep existing files in their current locations. The
`minimal`, `research` and `manuscript` profiles retain their existing contracts.

```bash
python scripts/scaffold_project.py /path/to/project --profile exploratory --json
python scripts/scaffold_project.py /path/to/project --profile exploratory --apply
python scripts/audit_project.py /path/to/project --profile exploratory --json
```

The scaffold starts with a reviewable dry run. Existing files are preserved;
conflicting or unsafe destinations are reported, not replaced. For an existing
project, use `--mode retrofit`. The profile does not require `docs/`, `analysis/`,
`provenance/`, `results/` or a fixed data/code layout.

The audit's default `--profile auto` recognizes this marker when no formal
project records take precedence. Use an explicit profile only to select the
scope of a check; `--profile exploratory` does not retire a formal contract.

## Proportionate records

Update the parts that actually changed after meaningful work. For an initial
look at a matrix, it may be enough to record the matrix/source identity,
experimental unit, inspection command or notebook, observation, relevant
limitation and next check. An unavailable fact is recorded as unknown. Record
material parameters, tool/reference versions and output paths when analyses
actually run. Existing relative links to logs, metadata or notebooks can supply
the detail; no second inventory or full readiness report is necessary merely
to maintain this project memory.

Use dated action entries for work with lasting consequences. Retain superseded
interpretations and their reason for replacement. Do not change the update date
to silence a freshness warning without reviewing the record. No observations,
successful runs or verification are inferred from template creation.

## What the audit checks

The exploratory check only reads the four fixed, root-level memory files. It
checks their presence, the explicit profile marker, six nonempty note sections
and the update date. Missing facts may be explicitly unassessed; nonempty text
does not prove that the information is complete or true. The check does not
open linked data or logs, rerun analyses, validate scientific claims, generate
readiness authorization or require optional skills or scLucid.

Unsafe memory-file inputs, including symlinks, special files and hard-link
aliases, are refused. Reads use a directory descriptor and do not follow file
symlinks; the check requires a supported POSIX runtime (Linux, macOS or WSL).
It does not audit every file in the project. Memory files over 2 MiB are refused
so history should then be kept in ordinary separate records and referenced.

## Moving to sustained research

Reconsider the profile when independent runs, multiple collaborators or formal
deliverables need more explicit traceability. Keep `PROJECT_NOTES.md` as history,
review the formal scaffold in retrofit mode, and map existing records into the
chosen formal contract. An existing formal project contract takes precedence
over a retained exploratory marker during automatic profile selection.
Neither an exploratory audit nor this transition grants scientific readiness.
Do not convert layout versions, move input data, discard earlier records or
fabricate missing run provenance as part of that transition.
