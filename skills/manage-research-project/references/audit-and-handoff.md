# Audit, hand off or archive a project

## Phase 5 — Audit

Run:

```bash
python scripts/audit_project.py /path/to/project --json
```

The default profile `auto` recognizes an explicit exploratory marker only when
no formal project records take precedence; otherwise it audits `research`.
Select `--profile manuscript` for manuscript-specific requirements. An explicit
exploratory check is a narrow memory check, not a downgrade of a formal project.
Use `--strict` when warnings should fail CI. The formal audit checks required files, stale status/handoff dates, unresolved
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

For an exploratory freeze, preserve the note and declared artifacts, record
included/excluded scope and hashes, verify the copied bytes, and state which
execution, provenance and scientific checks were not performed. Do not invent
formal registries or assessments to fill a template. Formal delivery uses the
full checklist below, proportionate to the declared snapshot scope.

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

Follow [retrofit-and-archive.md](retrofit-and-archive.md) for the
snapshot checklist.

## Output contract

For a narrow checkpoint, briefly report changed records, checks and the next
action; provide a restart prompt when a handoff is requested. For initialization,
retrofit, comprehensive audit or archive, report the applicable fields:

1. selected mode, profile, layout and target;
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

- Run `scripts/audit_project.py` for a requested project audit, initialization,
  retrofit or archive, and when changes affect structural controls or source
  integrity. A records-only checkpoint validates changed records, their links
  and consistency with cited evidence; it does not require a full project audit.
  Changes to source/spec/code/environment/backend or a readiness-dependent
  delivery still require the relevant freshness, integrity and domain checks.
- Validate Markdown links or manifest targets that were added.
- Confirm existing files were not overwritten.
- Confirm raw-input locations, including mapped roots, were not modified.
- Confirm `PROJECT_STATUS.md` and `SESSION_HANDOFF.md` agree on the next task,
  or that exploratory `PROJECT_NOTES.md` has one current next step.
- For formal findings, confirm source artifact/run IDs, uncertainty, scope and
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
