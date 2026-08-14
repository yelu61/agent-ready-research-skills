# Analysis Output Contract

## Required handoff

At completion, report:

1. Backend and repository revision used.
2. Input files, assay scale, species, and identifier type.
3. Sample inclusion/exclusion and final group sizes.
4. Statistical design, contrasts, thresholds, and correction methods.
5. Configuration or notebook path.
6. Native run directory, curated result directory, and primary tables/figures.
7. Dependency, data-quality, and interpretation warnings.
8. Reproduction command, run ID, session/toolkit version, and repository state.

## Recommended manifest

When the backend does not already create equivalent metadata, write a small
machine-readable manifest beside the outputs:

```json
{
  "backend": "rnaseq-templates",
  "backend_revision": "<git-commit>",
  "analysis_type": ["deg", "enrichment"],
  "species": "human",
  "input_scale": "raw-counts",
  "run_id": "20260813_01",
  "config": "<relative-path>",
  "config_checksum": "<sha256>",
  "input_checksums": {"counts": "<sha256>", "metadata": "<sha256>"},
  "native_run_root": "analysis/runs/20260813_01",
  "curated_results_root": "results",
  "results": ["<relative-result-path>"],
  "warnings": []
}
```

Prefer relative paths inside the analysis project. Never include credentials,
tokens, private remote URLs, or unrelated absolute home-directory paths.

## Two-layer ownership

- The native run bundle is complete and immutable; it preserves backend-native
  tables, figures, configuration, logs, and session information.
- The curated result layer contains only reviewed deliverables. Every curated
  artifact records its source run and source file.
- A figure manifest records role (primary/supplementary/diagnostic), source
  table, final dimensions, master format, preview path, and visual-QA status.
- `report_assets/` is a rebuildable preview cache. It is not a second canonical
  figure directory.
- Do not overwrite a completed run or create byte-identical compatibility
  copies. Use a new run ID or a manifest alias.

## Single execution path

Choose **one** execution path per analysis (one dataset + design); do not run
both a full CLI bundle and a full notebook over the same inputs.

- **Batch / production** → the CLI runner (`config.R` + `run_analysis.R`).
  Outputs land in `analysis/runs/<run_id>/` and are curated into `results/`.
- **Interactive exploration** (iterating on thresholds, gene sets, figures) →
  a notebook. Outputs land in `analysis/notebook_output/<analysis>/` and are
  **exploratory and regenerable — never curated** into `results/`.

Running both paths over the same inputs duplicates the entire pipeline output
(the run bundle and `notebook_output/` mirror each other) and doubles storage.
If exploration later hardens into a final result, re-run the CLI bundle once and
curate from that bundle; do not curate from `notebook_output/`. Treat
`notebook_output/` as disposable — keep the notebook source (`.ipynb` / `.R`)
and any recompute caches, and delete the bulky figures/tables freely.

## Cross-backend handoffs

Use explicit, versioned files:

- Gene/signature TSV: `gene`, optional `weight`, optional `direction`.
- DEG table: gene identifier, effect estimate, test statistic, raw P value,
  adjusted P value, and comparison label.
- Risk model: feature coefficients plus preprocessing/scaling metadata.
- Expression matrix: genes by samples, with a separate sample metadata table.

Document identifier conversion and dropped features. Never infer that symbols,
Ensembl IDs, transcript IDs, and platform probe IDs are interchangeable.
