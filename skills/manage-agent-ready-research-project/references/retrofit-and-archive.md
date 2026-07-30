# Retrofit and archive procedures

## Retrofit an established project

1. Inventory the existing layout and canonical entry points.
2. Identify duplicate, stale and orphaned documents without moving them.
3. Determine which results are generated, manually curated or externally
   supplied.
4. Add missing project-memory files using the scaffold dry run.
5. Populate documents from verified files; leave uncertain facts as TODOs.
6. Add a migration decision describing any chosen canonical document.
7. Move or rename files only under a separate, explicitly approved migration.
8. Preserve a mapping from legacy to current paths.

Do not rewrite a working project merely to match the template tree.

## Freeze an archive or manuscript snapshot

Record:

- snapshot date and purpose;
- raw/source data identities and checksums when feasible;
- canonical code and notebook entry points;
- environment files and package/database versions;
- executed versus planned workflow stages;
- selected figures/tables and their source data;
- open author queries and known limitations;
- current conclusions with evidence states;
- restart instructions.

Prefer a copied snapshot or versioned archive. Do not move the live workspace,
delete raw data or overwrite a previous snapshot.

## Handoff quality gate

Another agent should be able to answer within minutes:

1. What is the scientific question?
2. What data and experimental units exist?
3. What has actually run?
4. What are the current supported conclusions?
5. Which earlier conclusions are superseded?
6. What is blocked?
7. What is the next smallest useful action?
8. Which exact files should be read or executed?
