# Changelog

All notable repository changes are recorded here. Skill releases use
skill-scoped semantic-version tags.

## Unreleased

### Changed

- Clarified that the collection contains only user-authored, redistributable
  scientific skills and excludes third-party or client-managed installations.

### Added

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
