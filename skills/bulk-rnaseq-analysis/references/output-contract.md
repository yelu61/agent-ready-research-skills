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
  "run_id": "bulk-rnaseq__20260813_01",
  "config": "workflows/bulk-rnaseq/config/<config-file>",
  "config_checksum": "<sha256>",
  "input_checksums": {"counts": "<sha256>", "metadata": "<sha256>"},
  "native_run_root": "analysis/runs/bulk-rnaseq__20260813_01",
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
- Project-authored configuration, scripts and notebooks have one source owner:
  `workflows/bulk-rnaseq/`. The backend itself is external and bound by
  `backend.lock.json`.
- The curated result layer contains only reviewed deliverables. Every curated
  artifact records its source run and source file.
- A figure manifest records role (primary/supplementary/diagnostic), source
  table, final dimensions, master format, preview path, and visual-QA status.
- Any run-local `report_assets/` directory is a rebuildable preview cache. It
  is not a second canonical figure directory.
- Do not overwrite a completed run. Delivery copies are intentional and must
  preserve source identity. Use a stable current delivery index; retain older
  executions in provenance instead of exposing many `v*` navigation trees.

## Execution and change scope

General notebook and CLI are formal entries into the same steps. Both write to
`analysis/runs/bulk-rnaseq__<run_label>/`. A validated notebook need not be
converted or fully rerun by CLI. Keep the source notebook in the workflow,
check clean-kernel execution, and retain parameters, environment, logs and
stage records. Inspect legacy scratch output before using or retiring it.

| Change | Required recomputation |
| --- | --- |
| Counts, included samples, model/design, count filtering | Refit model and dependent stages |
| Pure DEG selection cutoff (padj/pvalue, absolute effect cutoff) | Reuse unchanged all-gene model results; regenerate threshold-dependent DEG/ORA/plots/overlap/report |
| Model-level parameter, including independent filtering or testing hypothesis | Recompute affected model/results; do not call it a display threshold |
| ORA universe/reference, ranking or gene sets | Recompute affected enrichment/scoring and downstream summaries |
| Key-gene list | Regenerate those plots/tests from the matching saved expression and design |
| Colors, labels, figure dimensions or report prose | Rerender affected outputs; preserve statistical results |
| Delivery layout | Re-export saved outputs; no model fitting |

Check cached input/config/backend identity before reuse. Keep completed source
runs immutable; a derivative run records its parent and changed scope. Reuse
only supported backend interfaces, and disclose a missing continuation API
rather than quietly reimplementing the pipeline in a project script.

## Portable complete delivery

Use `tools/export_results.R <run_dir> <delivery_dir>` for a validated General
run. Include complete requested modules for all declared thresholds, alongside
a concise report; `DEFAULT_THRESHOLD` controls only the preferred view.
The module tree uses `00_report/`, `01_qc/`, `02_degs/`, `03_ORA/`, `04_GSEA/`,
`05_custom_genes/` and optional domain modules. Within modules use `tables/`
and `figures/` with consistent threshold subdirectories. Keep question and
claim navigation in the report/index. Existing question-oriented projects need
not migrate.

`MANIFEST.tsv` records each delivery `path`, `source_path` relative to the native
run and `source_run_id`, with byte identity and module metadata. Include actual
files and relative report resources. Test opening the copied delivery without
the original project; source-run links are provenance, not required navigation.
The exporter verifies execution coverage, not scientific interpretation.
For an updated view, use `tools/export_results.R <parent_run> <delivery_dir>
<derivative_run>`; unchanged stages come from the parent and recomputed stages
from the derivative, with their distinct source IDs retained in the manifest.

## Project registry handoff

When a project uses RUNS/ARTIFACTS registries, map the native metadata with this
skill's helper, then use the installed project-manager helper to register it:

```bash
python3 scripts/build_run_registration.py <project> \
  --run analysis/runs/bulk-rnaseq__<run_label> --analysis-id <analysis_id> \
  --entry-point workflows/bulk-rnaseq/notebooks/analysis.ipynb \
  --delivery results --output workflows/bulk-rnaseq/registration.json
```

The output is a generic `{run, artifacts}` JSON, using existing RUNS.tsv and
ARTIFACTS.tsv column names. Each artifact additionally declares `direction`
(`input`, `output`, `delivery`) and optional `parent_paths`. No dependency on
another skill's installation path is embedded. The helper verifies native
input/config MD5 and delivery source identity, then binds current bytes by
SHA-256. It refuses overwrite. Use a new output filename for a new registration.
Installed annotation/reference files outside the project are verified by MD5
and retained as native `run_inputs.csv` evidence with role/checksum notes;
they are not copied into each project or falsely registered as local artifacts.
Frozen GO/KEGG references inside a native run retain their declared input role
and are inventoried once. Analysis inputs such as raw counts still require
project ownership and must not double as files generated by that run.
Schema-v2 native manifests and input rows with `path_base=run` resolve strictly
from the native run. For older records without this field, run-relative and
project-relative candidates must have a unique checksum match. A legacy
external reference recorded only as a basename has lost its location: restore
explicit source provenance instead of guessing a package or similarly named file.
For a direct CLI invocation, record its actual entry as
`backend:rnaseq-templates/templates/General/run_analysis.R`; the native manifest
supplies the backend revision. This avoids creating a wrapper only for metadata.
The symbolic backend entry records invocation identity, not verified source
coverage; a scientific assessment must separately satisfy its code manifest
and entry-point contract. Do not relabel a config file as executed source.

For a derivative delivery assembled from parent and newly computed files, add
`--parent-run-dir analysis/runs/<parent_id>` and set `--run` to the derivative.
The derivative must have schema-v2 native provenance binding that parent ID.
Register the parent first under the same analysis ID. Parent-origin source
files become `direction=reference` records: the importer requires an existing
unique path/SHA-256 artifact and preserves its original run identity. Delivery
copies link to those original artifacts; they are not relabeled as newly
computed derivative outputs. Unknown or mixed unrelated source runs are refused.

The generic manager command is `scripts/register_run.py <project> --metadata
<project-relative-json>`; inspect its dry run and add `--apply` to append to the
existing registries. It computes stable artifact IDs and preserves delivery
source links. Registration is idempotent and rejects rebinding IDs. Fill
unknown source provenance, code/environment evidence and technical-validation
fields only from observed evidence. Neither mapping nor import invents a
scientific readiness assessment. Without project management, keep the complete
native/delivery manifests; bulk analysis remains independently usable.

## Cross-backend handoffs

Use explicit, versioned files:

- Gene/signature TSV: `gene`, optional `weight`, optional `direction`.
- DEG table: gene identifier, effect estimate, test statistic, raw P value,
  adjusted P value, and comparison label.
- Risk model: feature coefficients plus preprocessing/scaling metadata.
- Expression matrix: genes by samples, with a separate sample metadata table.

Document identifier conversion and dropped features. Never infer that symbols,
Ensembl IDs, transcript IDs, and platform probe IDs are interchangeable.
