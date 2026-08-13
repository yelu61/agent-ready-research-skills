# Changelog

All notable repository changes are recorded here. Skill releases use
skill-scoped semantic-version tags.

## Unreleased

### Changed

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
