# Changelog

All notable repository changes are recorded here. Skill releases use
skill-scoped semantic-version tags.

## Unreleased

### Changed

- Rebuilt `manage-research-project` around orthogonal source,
  implementation, execution, validation, readiness, claim, lifecycle and
  reproduction states. Structure audits now explicitly leave scientific
  readiness unassessed; project templates add estimands, independent units,
  data freezes, null findings, scoped readiness, artifact/run lineage and
  human-data access boundaries, with a non-upgrading migration rule for legacy
  `confirmed`/`supported` labels.
- Bridged `manage-research-project` to the two-layer analysis output contract:
  the scaffold stays generic, but the `AGENTS.md`/`README.md` templates and the
  `SKILL.md` safety rules now document that pipeline-native run bundles belong
  under `analysis/runs/<run_id>/` (created on demand) while `results/` holds
  only curated deliverables, so the skill composes cleanly with
  `bulk-rnaseq-analysis` and the RNAseq-Templates runners.
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
