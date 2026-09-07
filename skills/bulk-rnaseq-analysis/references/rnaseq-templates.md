# RNAseq-Templates Backend

## Repository contract

Validate the root by checking for:

- `RNAseq_lib/`
- `notebooks/`
- `templates/`
- `references/TEMPLATE_SELECTION.md`
- `examples/run_demo_smoke_test.R`

Read the repository's `README.md` and
`references/TEMPLATE_SELECTION.md` before selecting a template. The repository
currently targets downstream analysis from expression matrices, not FASTQ.

## Template selection

Every template ships a CLI runner under `templates/` alongside a notebook.
General's notebook and CLI call one shared implementation. Prefer the notebook
for interactive work, honor a requested entry, and use CLI for batch execution.
Do not assume the other topic notebooks are numerically interchangeable with
their runners without checking their supported design and execution behavior.

| Question | CLI runner | Notebook |
| --- | --- | --- |
| Standard group comparison | `templates/General/run_analysis.R` | `notebooks/RNAseq_General.ipynb` |
| limma-voom or batch-heavy contrast | `templates/Limma_Voom/run_analysis.R` | `notebooks/RNAseq_limma_voom_Template.ipynb` |
| Longitudinal/time-course | `templates/TimeCourse/run_analysis.R` | `notebooks/RNAseq_TimeCourse_Template.ipynb` |
| Immune/stromal deconvolution | `templates/TME/run_analysis.R` | `notebooks/RNAseq_TME_Deconvolution_Template.ipynb` |
| Co-expression modules | `templates/WGCNA/run_analysis.R` | `notebooks/RNAseq_WGCNA_Template.ipynb` |
| Lightweight TCGA/GEO teaching workflow | `templates/TCGA_GEO/run_analysis.R` | `notebooks/RNAseq_TCGA_GEO_Template.ipynb` |

Each `run_analysis.R` shares the same bootstrap, numbered `0-Config/1-DEG/...`
output layout, and `0-Config/analysis_config_used.R` snapshot, and accepts a
config path as its first trailing argument (defaulting to the template's own
`config.R`).

The runner preserves its invocation directory. It resolves a relative config
argument before loading, then interprets relative input paths and `OUTDIR` from
the explicit run root. In production, enter a fresh
`analysis/runs/<run_id>/` first or use absolute project paths; never let the
template repository become the output root.

For advanced TCGA/TARGET/GTEx analysis, route to the TCGA toolkit instead of
expanding the lightweight teaching notebook.

## Standard workflow

1. Identify raw counts versus normalized expression and inspect metadata.
2. Confirm sample identifiers match exactly and groups have adequate size.
   Per-sample config vectors (SAMPLE_NAMES, GROUPS, BATCH_VECTOR, PAIR_ID) are
   matched to count columns positionally; **prefer named vectors**
   (`SAMPLE_NAMES <- c(raw_col = "clean_name", ...)`, `GROUPS <- c(Ctrl_1 =
   "Ctrl", ...)`). Named vectors are aligned by name, so ordering mistakes
   become explicit errors instead of silent sample/annotation swaps. When
   SAMPLE_NAMES reuse the count column names, an order mismatch stops the run.
3. Choose the requested notebook or CLI entry. In a v2 project, place
   configuration and source notebooks under
   `workflows/bulk-rnaseq/`; keep `RNAseq_lib/` resolvable through the verified
   external backend lock.
4. Edit the parameter block/configuration before changing analysis code.
5. Run input validation before fitting a model.
6. Create a new
   `analysis/runs/bulk-rnaseq__<run_label>/` and execute from that explicit root.
   Never execute a notebook with `notebooks/` as the output root: its relative
   `1-DEG/`, `2-GSEA/`, and `3-Visualization/` paths will otherwise mix code
   and hundreds of generated artifacts.
7. Retain the complete native run bundle, then export reviewed modules and a
   report to a portable `results/` tree. Follow the output contract below.
8. Record `sessionInfo.txt`, parameters, comparisons, warnings, input/config
   checksums, backend revision, and the source run for each curated artifact.

For any template's CLI runner:

```bash
Rscript templates/<Topic>/run_analysis.R path/to/config.R
```

Keep project configuration and any project-specific wrapper under
`workflows/bulk-rnaseq/`. Invoke the runner from the verified external backend;
do not copy the backend repository or create a worktree inside the project.

For TME, distinguish the deterministic offline base path from optional IOBR
integration. Native ESTIMATE and ssGSEA can be used for the offline smoke path;
IOBR methods may require reference bundles populated on first use. Verify the
requested method cache before declaring an offline run ready.

## General shared stages

Use the locked backend's General notebook or runner to load the public API:

```r
workflow <- create_general_workflow(config_file, run_dir, lib_dir)
run_general_stage(workflow, "input")
# Run subsequent stages in notebook cells, or all stages sequentially:
run_general_workflow(workflow)
```

The ordered stages are `input`, `qc`, `model`, `thresholds`, `deg_plots`, `ora`,
`gsea`, `gsva`, `single_genes`, `overlap`, `tf`, `tme`, `report`, `finalize`.
Notebook cells display stage results; they do not contain a second model or
statistical implementation. `workflow_status.csv` records outcomes, and
`finalize` must complete. RunReview remains an optional compatibility tool,
not a second notebook required in each project. Use the converter only when
developing a genuinely new pipeline, not to authorize routine notebook output.

`THRESHOLD_GRID` expands every DEG-dependent module over each declared threshold.
`DEFAULT_THRESHOLD` selects the headline view, not execution scope. Cover DEG
tables, volcano/topDEG plots, GO/KEGG all/up/down ORA, ORA themes/comparison plots,
overlap/UpSet/Jaccard and report navigation where applicable. Empty or
not-applicable outcomes need recorded reasons; failures require repair or an
explicitly scoped incomplete handoff. Nominal-P layers remain exploratory.
QC, model fitting, full-ranking GSEA and fixed-set GSVA are shared once.

Read the saved all-gene results for new threshold selection; do not mistake
them for filtered DEG lists. Secondary tests inherit configured comparisons,
pairing, test and adjustment. Frozen `GO_REFERENCE`/`KEGG_REFERENCE` resources
use the backend's documented Entrez TERM2GENE format and are recorded inputs.

For validated General runs:

```bash
Rscript tools/export_results.R <run_dir> <delivery_dir>
```

For a delivery that combines an immutable parent with its derivative, pass the
derivative directory as the third argument; the manifest retains each file's
actual source run.

The exporter requires completed stage accounting and a new, empty, or README-only
output directory. It preserves an existing regular `README.md` and includes
physical files, relative report resources and a source
manifest. It does not confer scientific approval. Review claims separately.

## Historical result review after a backend fix

Read the selected backend's changelog and, when available,
`references/HISTORICAL_RESULT_REVIEW.md` and its linked defect evidence. Keep
the defect catalog in the backend rather than copying version-specific claims
into the skill.

1. Identify the exact old source revision or saved source hashes, actual entry
   point, configuration, input/sample mapping, model formula, environment and
   reference snapshots. A current README version or today's checkout is not
   evidence of which code produced an old result. Record unknown provenance.
2. Match each documented defect's trigger to that run. Distinguish numerical
   errors, test/model changes, incomplete or misleading exports, and layout-only
   issues. Do not declare every old result wrong, or assure correctness because
   an established statistical package was called.
3. Determine the earliest affected stage and its downstream consumers. A wrong
   sample map or model requires a new fit; a plotting-only statistic may need
   secondary tests and report updates; a layout-only change needs verified
   repackaging. Do not feed an unfiltered legacy marked table to ORA as a DEG set.
4. Preserve the old run. Compare affected outputs in a new scoped run under
   matched parameters/references when isolating a code fix. Record deliberate
   parameter changes separately: independent-filtering alpha changes are not
   equivalent to a display cutoff change. Never tune parameters to recover an
   old positive finding.
5. Update affected claims, figures and delivery pointers after verification,
   with the parent run and reason. Keep unknown or untested effects explicit;
   test-suite success does not retrospectively certify a real project.

Use saved-state derivatives only if the actual locked backend and original run
support them and the preserved model is unaffected. An old run without verified
state cannot gain that support by fabricating a checkpoint or status manifest.

## Project layout v2

```text
workflows/bulk-rnaseq/
  config/ scripts/ notebooks/ backend.lock.json
analysis/
  specs/ readiness/
  runs/bulk-rnaseq__<run_label>/      # complete backend-native bundle
  notebook_output/bulk-rnaseq/        # optional scratch, legacy-compatible
results/
  README.html MANIFEST.tsv
  00_report/
  01_qc/ 02_degs/ 03_ORA/ 04_GSEA/ 05_custom_genes/
```

Each native artifact has one canonical owner; intentional delivery copies
record that source. Use matching threshold subdirectories in DEG and ORA
modules. Question-oriented delivery remains valid when preferred. Treat
PDF/SVG as figure masters and report preview PNG files as derived cache. Keep
intentional gene-set versions only with registry checksums and rationale.

Reuse saved stages according to the change dependencies in
[output-contract.md](output-contract.md). Avoid new project scripts for standard
plots, reference handling, packaging or registration; use public backend/skill
helpers. Project scripts should implement only the study's distinct logic.

## Input-scale rules

- DESeq2: integer-like raw counts.
- limma-voom: raw counts with library-size modelling.
- WGCNA/time-course clustering: variance-stabilized or otherwise appropriate
  normalized expression.
- TME: TPM, `log2(TPM + 1)`, or raw counts plus gene lengths as documented.
- GEO: inspect platform annotation and preprocessing; do not assume downloaded
  values are raw counts.

## Validation

Run focused unit tests after helper-library changes:

```bash
Rscript tests/testthat.R
```

Validate notebook structure:

```bash
Rscript tests/validate_notebooks.R
```

Run the bundled smoke workflow when dependencies and network/cache conditions
allow:

```bash
Rscript examples/run_demo_smoke_test.R
```
