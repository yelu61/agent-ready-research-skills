# Retrofit and archive procedures

## Retrofit an established project

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

Do not rewrite a working project merely to match the template tree.

## Freeze an archive or manuscript snapshot

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
