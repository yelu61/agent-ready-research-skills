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

Every template ships a production CLI runner trio (`config.R` + `run_analysis.R`
+ `visualize_results.R`) under `templates/`, alongside its interactive notebook.
Prefer the runner for routine production and the notebook for interactive
exploration.

| Question | Production runner | Interactive notebook |
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
3. Prefer the template's CLI runner for a routine production project. Copy a
   notebook only for interactive exploration; keep `RNAseq_lib/` resolvable.
4. Edit the parameter block/configuration before changing analysis code.
5. Run input validation before fitting a model.
6. Create a new `analysis/runs/<run_id>/` and execute from that explicit root.
   Never execute a notebook with `notebooks/` as the output root: its relative
   `1-DEG/`, `2-GSEA/`, and `3-Visualization/` paths will otherwise mix code
   and hundreds of generated artifacts.
7. Retain the complete native run bundle, then curate reviewed deliverables
   into `results/tables`, `results/figures`, and `results/reports`.
8. Record `sessionInfo.txt`, parameters, comparisons, warnings, input/config
   checksums, backend revision, and the source run for each curated artifact.

For any template's CLI runner:

```bash
Rscript templates/<Topic>/run_analysis.R path/to/config.R
```

Use a project-local copy of `config.R`, `run_analysis.R`, and
`visualize_results.R` when the analysis must not write into the template
repository.

For TME, distinguish the deterministic offline base path from optional IOBR
integration. Native ESTIMATE and ssGSEA can be used for the offline smoke path;
IOBR methods may require reference bundles populated on first use. Verify the
requested method cache before declaring an offline run ready.

To turn a notebook's parameter cell into a `config.R` + `run_analysis.R` draft
for a new or customized pipeline, use the bundled converter:

```bash
Rscript tools/notebook_to_runner.R notebooks/<Notebook>.ipynb <out_dir> --topic <Name>
```

It extracts the `## 1. Parameter Configuration` cell into `config.R`, flattens
the remaining code cells into a runner, and writes a `conversion_report.txt`
flagging patterns that need manual refinement. Treat its output as a draft to
review, not a finished runner.

## Production output layout

```text
analysis/
  config/
  scripts/
  notebooks/                  # source only
  runs/<run_id>/              # complete backend-native bundle
results/
  tables/ figures/ reports/
  report_assets/              # rebuildable HTML previews
```

There must be one canonical owner for each artifact. Treat PDF/SVG as figure
masters and `report_assets/` PNG files as derived cache. Keep intentional gene
set versions only with registry checksums and rationale; use manifest aliases
instead of byte-for-byte compatibility copies.

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
