# Changelog

All notable repository changes are recorded here. Skill releases use
skill-scoped semantic-version tags.

## Unreleased

### Changed

- Made project management proportional to scope: added a four-file exploratory
  profile and narrow memory audit, explicit existing-layout mapping with mapped
  document/source checks, and mapped default source-baseline scopes. Existing
  formal profiles and fixed layout v2 remain compatible. Maps preserve paths,
  reject ownership aliases/collisions, and do not configure analysis backends.
- Added an optional read-only multimodal measurement/pair validator for donor,
  specimen, section, cell and longitudinal relationships. Partial/unpaired
  designs remain valid; ambiguous identity requests review, and record
  consistency never implies biological authenticity or scientific validation.
- Added regression fixtures for exploratory selection, non-overwriting mapped
  retrofit, source drift, unsafe/colliding paths, template rendering and
  multimodal pairing constraints; documented proportional checkpoint/archive use.

- Corrected scientific claim calibration: causal identification, local
  mechanism, replication, prediction and external validity are separate axes.
  Added material-backed paper-reading cases for replicated association,
  pseudoreplication, incomplete source material and justified local causality.
- Hardened bulk upstream reference/index byte validation, current-sample
  processing, count-column and integer validation, Xengsort identity/direction,
  and explicit strandedness evidence. Reference manifests now use schema 2;
  old unbound manifests require recovery/rebuild before execution.
- Hardened downstream input-scale compatibility, formula-derived interaction
  checks, patient-level external prediction validation, claim-class eligibility,
  and revision/capability-bound execution readiness. Planning remains possible
  without an execution backend.
- Marked project-manager readiness v2 as an experimental library with an explicit
  failing CLI; readiness v1 remains the supported interface. Added unsupported
  locking-runtime errors before registry mutation and documented proportional
  exploratory checkpoints.
- Made scLucid, named researcher perspectives and sibling skills optional,
  with native reasoning/review fallback and explicit unperformed execution.
- Added recursive standalone-resource validation, package licenses, dependency
  and methodological-source ledgers, and a numerical CI regression environment.

### Added

- Promoted `scientific-reasoning` and `scrna-analysis-core` into this canonical
  public source collection. The private source is retired through local
  compatibility links after independent-install validation.
- Added compatible, package-local handoff validation and single-cell regressions
  covering same-file/alias overwrite prevention, atomic reports, invalid counts,
  missing labels, storage-consistent sampling and contrast estimability in
  disconnected batch-condition designs.
- Added MIT licensing at repository and standalone-package scope. External
  sources and runtimes retain their own rights and are not bundled.

### Earlier unreleased changes

- Added scoped historical-result review after backend defects: the bulk skill
  checks the actual revision, execution path and affected calculations; the
  manager preserves original runs and records correction lineage and dependent
  claim updates. Current skill capabilities must be checked against a project's
  locked backend, without inventing saved-state support for legacy runs.

- Aligned `bulk-rnaseq-analysis` and `manage-research-project` with formal
  notebook or CLI execution, complete declared-threshold coverage, dependency-
  scoped recalculation and portable module-oriented delivery. Updated generated
  project instructions and removed question-only result-layout audit errors.
  Capability preflight, execution verification and scientific assessment remain
  distinct; legacy projects and independent skill installation remain supported.
- Added native RNA-seq metadata mapping and a generic, idempotent run/artifact
  registry importer with checksum verification and delivery-parent links.
  Native reference handling verifies external annotation dependencies without
  copying them and deduplicates frozen reference snapshots within a run.
  Native path resolution honors explicit run-relative bases, supports legacy
  project-relative paths only with unique checksum matches, and rejects lost
  or ambiguous reference locations.
  Fixed mixed manifest commit values and portable delivery-relative paths in
  the project audit without suppressing missing-file or unsafe-path checks.

- Made the project AGENTS template load context by task: status and handoff
  first, analysis/design/data records when needed, and only relevant sections
  for narrow documentation or configuration edits. Readiness and data-governance
  checks remain required when applicable. Local checkout/link/update examples
  now use the `~/Skills/` source-root convention.

- Rebuilt `manage-research-project` around orthogonal source,
  implementation, execution, validation, readiness, claim, lifecycle and
  reproduction states. Structure audits now explicitly leave scientific
  readiness unassessed; project templates add estimands, independent units,
  data freezes, null findings, scoped readiness, artifact/run lineage and
  human-data access boundaries, with a non-upgrading migration rule for legacy
  `confirmed`/`supported` labels.
- Unified `manage-research-project` and `bulk-rnaseq-analysis` on the project
  layout v2 contract: authored sources live only under `workflows/`, specs and
  immutable native bundles under `analysis/`, curated deliverables under
  domain-selected `results/`, and lineage under `provenance/`. New projects
  receive a validated `PROJECT_LAYOUT.json`; legacy retrofit remains
  non-migrating and accepts the historical root `PIPELINE.md`.
- Synced `bulk-rnaseq-analysis` with the RNAseq-Templates backend: all six
  templates (General plus the five topic templates) now ship a
  `config.R` + `run_analysis.R` + `visualize_results.R` CLI runner, so the
  template-selection table lists a production runner per template, the routing
  rules reference the template CLI runners rather than only the General runner,
  and the backend reference documents the `tools/notebook_to_runner.R`
  notebook-to-runner converter.
- Renamed `manage-agent-ready-research-project` to `manage-research-project`;
  the original v1.0.0 release record remains below for historical accuracy.
- Clarified that the collection contains only user-authored, redistributable
  scientific skills and excludes third-party or client-managed installations.

### Added

- Added v2 structure-audit checks for parallel source roots, embedded Git
  backends and malformed layout manifests, plus an
  external backend-lock helper that records and verifies cloneable Git origins
  and full commits and materializes them in a project-external cache.
- Added policy-bound `research-readiness/v1` and generic AnalysisSpec
  validation; versioned gate-policy and source-manifest schemas;
  non-overwriting source/code baseline verification; typed, hash-bound evidence
  closure; structured claim-class authorization; symlink-safe scaffold writes;
  provenance/readiness templates; and adversarial regression tests for
  `manage-research-project`. The contracts now also separate requested claims
  from authorized claims, target validation from achieved validation, and
  declared readiness from contract/currency/policy/source-integrity states;
  bind domain and study-type applicability; reject placeholder scientific
  identities; require structured gate failure effects and technical-validation
  evidence fields; and restrict external-reference identities to DOI/URN while
  requiring mutable web content to be captured as a hash-bound artifact.
  The hardened contracts additionally bind assessor versions, explicit data
  requirements and code entry points; derive source IDs from path plus digest;
  validate artifact rows and byte sizes; require run input/output/validation
  IDs and logs to close; propagate assessed source IDs through artifacts; bind
  output artifacts back to runs; require scoped, dated decisions with reasons;
  and hash exact artifact, run, transitive run-artifact and log records so later
  rebinding cannot silently preserve readiness. Analysis units
  must also close against an explicitly ordered unit hierarchy, exposing common
  pseudoreplication-inducing declaration errors without claiming to validate
  the biological independence assumption itself.
- Added `bulk-rnaseq-upstream`, a self-contained paired-end FASTQ-to-count
  workflow with immutable shared-reference validation, HISAT2/featureCounts
  execution, transcript BED12 generation, human-mouse Xengsort routing,
  provenance manifests, forward-test prompts, and shell workflow smoke tests.
- Migrated and substantially refined `critical-paper-reading` with explicit
  source-completeness gating, claim–evidence provenance, causal calibration,
  domain-specific validity checks, reading modes, and forward-test prompts.
- Migrated `bulk-rnaseq-analysis` from RNAseq-Templates into the central skill
  collection while preserving RNAseq-Templates and TCGA as independent
  analysis backends.
- Added deterministic routing, backend discovery, scientific input-scale
  warnings, forward-test prompts, and automated router tests for
  `bulk-rnaseq-analysis`.

## manage-agent-ready-research-project-v1.0.0 - 2026-07-30

### Added

- Lifecycle modes: `init`, `retrofit`, `checkpoint`, `audit`, and `archive`.
- `minimal`, `research`, and `manuscript` project profiles.
- Safe non-overwriting project scaffold generator.
- Project-memory, portability, staleness, and manifest audit tool.
- Research and manuscript templates, conditional references, agent metadata,
  and forward-test prompts.
