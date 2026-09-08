# Retrofit and archive procedures

## Retrofit an established project

Choose the profile first. A small exploration can keep four root files and one
working note. A formal custom layout can use [project-map.md](project-map.md)
to reuse existing document/source/input/run/delivery paths without moving them.
Inspect and reuse an existing canonical document before creating another.

1. Inventory the existing layout and canonical entry points.
2. Identify duplicate, stale and orphaned documents without moving them.
3. Determine which results are generated, manually curated or externally
   supplied.
4. Identify source files, analysis specs, environments, runs and outputs that
   lack stable IDs or lineage; do not infer mappings from similar filenames.
5. Add missing project-memory files using the scaffold dry run.
6. Populate documents from verified files; leave uncertain facts as TODOs.
7. Add a migration decision describing any chosen canonical document.
8. Use `provenance/MIGRATION_MAP.tsv` when paths or legacy state labels change.
9. Move or rename files only under a separate, explicitly approved migration.

Legacy `ARTIFACTS.tsv` files may lack the `analysis_id` or `source_ids` columns,
and legacy readiness run evidence may lack `log_sha256` or
`artifact_record_sha256s`. Preserve and back up those records; add the new
columns/fields only from verifiable lineage. Until migrated, treat affected
readiness as `review`/stale rather than fabricating IDs or rewriting history.

Do not rewrite a working project merely to match the template tree. Do not
create `provenance/PROJECT_LAYOUT.json`, `workflows/` or v2 result categories
during retrofit. A v2 migration is a distinct, explicitly approved operation
with its own inventory and migration map.

## Correct results affected by a backend defect

Use the existing project status, decision log, run/artifact records and scoped
readiness reports; a separate defect registry is not required.

- Record the reported defect and source of evidence, old backend identity,
  potentially affected runs/artifacts and unresolved applicability. A new
  software release alone is neither proof of invalidity nor proof of repair.
- Have the domain workflow determine whether the defect affects numbers,
  interpretation, output completeness or only organization. Keep this scientific
  judgment out of the generic structure audit.
- Preserve original run and delivered bytes. When recomputation is authorized,
  give it a new run identity and parent/change reason; retain verification
  evidence comparing affected outputs. Do not overwrite old manifests or invent
  metadata for undocumented historical executions.
- Mark only impacted current claims/readiness as needing review using existing
  contract states. Preserve the historical assessment record. Supersede current
  result selections only after a replacement is verified, keeping explicit
  old-to-new artifact links and updating reports that consume changed results.
- Correcting numerical results does not imply authorization to reorganize or
  delete the project. Leave unrelated analyses and previously shared archives
  intact, and state any necessary downstream correction in the handoff.

## Freeze an archive or manuscript snapshot

For an exploratory freeze, preserve the working note and explicitly selected
artifacts, record scope and hashes, verify the copy, and state unperformed
execution/provenance/scientific checks. Do not fabricate registries or claim a
full reproducibility archive from sparse notes. For formal snapshots, use the
applicable records below; include the project map when present so paths remain
interpretable.

Record:

- immutable snapshot ID, parent snapshot, date and purpose;
- git revision, dirty state, code manifest and environment snapshot;
- explicitly included and excluded scope;
- raw/source data identities, source-system references and checksums when
  authorized;
- canonical code and notebook entry points;
- environment files and package/database versions;
- executed versus planned workflow stages;
- artifact/run lineage and current readiness reports by intended use;
- selected figures/tables and their source data;
- open author queries and known limitations;
- current findings with separated claim, validation, readiness and lifecycle
  states;
- restart instructions.

Prefer a copied snapshot or versioned archive. Do not move the live workspace,
delete raw data or overwrite a previous snapshot. Recompute and verify the
snapshot manifest after copying. Reference restricted raw data rather than
copying it unless the governing authorization explicitly permits the copy.

Archive completion means the declared snapshot bytes were preserved. It does
not imply that an analysis was reproduced, scientifically validated or
independently confirmed.

## Handoff quality gate

Another agent should be able to answer within minutes:

1. What is the scientific question?
2. What data and experimental units exist?
3. What has actually run?
4. Which readiness declarations are current, and for which intended uses?
5. What findings and claim boundaries are current?
6. Which earlier conclusions are superseded or invalidated?
7. What is blocked or scientifically unassessed?
8. What is the next smallest useful action?
9. Which exact files should be read or executed?
