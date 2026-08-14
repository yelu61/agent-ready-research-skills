---
name: bulk-rnaseq-analysis
description: Orchestrate reproducible bulk RNA-seq downstream analysis across local expression matrices, GEO datasets, and TCGA/TARGET/GTEx cancer cohorts. Use for raw-count, TPM, VST/rlog, clinical, MAF, CNV, or methylation inputs; template selection; QC; DESeq2 or limma-voom differential expression; ORA/GSEA/GSVA; time-course analysis; TME deconvolution; WGCNA; survival and clinical association; pan-cancer, mutation, multi-omics, prognostic, external-validation, drug-response, and report workflows. Route generic matrix-based work to RNAseq-Templates and cancer-cohort or multi-omic work to the TCGA toolkit.
---

# Bulk RNA-seq Analysis

Use this skill as the single user-facing entry point for bulk RNA-seq
downstream analysis. Keep durable analysis logic in the selected repository;
perform discovery, routing, configuration, validation, execution, and result
handoff here.

## Workflow

1. Discover and validate both backends:

   ```bash
   python3 scripts/backend_router.py discover --json
   ```

   Prefer `RNASEQ_TEMPLATES_ROOT` and `TCGA_TOOLKIT_ROOT` when set. Otherwise
   use the discovered repositories. Do not assume a user-specific absolute
   path.

2. Inspect the request and available inputs before choosing an analysis:
   identify data source, assay scale, species, sample metadata, experimental
   design, primary comparison, and requested deliverables.

3. Route the request:

   ```bash
   python3 scripts/backend_router.py route \
     --source local \
     --input-type raw-counts \
     --analyses deg,enrichment \
     --json
   ```

   Use the script for deterministic routing and data-scale warnings. Apply
   scientific judgment when the user's request spans backends.

4. Read only the relevant backend reference:

   - Generic local/GEO matrix workflows: [references/rnaseq-templates.md](references/rnaseq-templates.md)
   - TCGA/TARGET/GTEx or cancer multi-omics: [references/tcga-toolkit.md](references/tcga-toolkit.md)
   - Mixed or ambiguous requests: [references/routing.md](references/routing.md)
   - Final delivery and provenance: [references/output-contract.md](references/output-contract.md)

5. Inspect real column names, group sizes, identifiers, and repository state
   before writing configuration. Reuse existing templates and task runners.
   For routine local group comparisons, prefer the General CLI runner as the
   production entry point; the five topic templates (limma-voom, TimeCourse,
   TME, WGCNA, TCGA/GEO) each ship an equivalent `templates/<Topic>/run_analysis.R`
   runner for their pipeline. Use a notebook only when interactive exploration
   is a stated requirement.

6. Declare a new run ID and separate the complete backend-native run bundle
   from curated deliverables before execution. Never use `notebooks/` as an
   implicit output root and never overwrite an existing run directory unless
   the user explicitly requests it.

   Pick one execution path per dataset+design and stick to it: the CLI bundle
   for batch/production, or a notebook (output to `analysis/notebook_output/`,
   exploratory only) for interactive exploration. Do not run a full CLI bundle
   and a full notebook over the same inputs — that duplicates the entire
   pipeline output. See the "Single execution path" section of
   [references/output-contract.md](references/output-contract.md).

   For an RNAseq-Templates CLI run, make the run root explicit: either enter
   `analysis/runs/<run_id>/` before invoking the central runner or copy the
   runner trio there. Resolve the config argument before execution, and make
   every relative input/output path relative to that run root. Never rely on a
   template source directory as an implicit working directory.

7. Validate before execution. Prefer dry-runs, dependency checks, and bundled
   smoke tests.

8. Execute only the requested scope, then summarize methods, parameters,
   warnings, result locations, and reproducibility metadata.

## Routing rules

- Route local raw-count, TPM, VST/rlog, and ordinary GEO expression-matrix
  workflows to **RNAseq-Templates**.
- Route TCGA, TARGET, GTEx, pan-cancer, MAF/TMB, CNV/GISTIC, methylation,
  molecular-subtype, stage, prognostic-model, TCGA-trained external
  validation, and drug-response workflows to the **TCGA toolkit**.
- Route a mixed study to both backends only when each has a distinct role.
  Define the handoff artifact explicitly, such as a DEG table, signature file,
  risk-model coefficients, or expression matrix.
- Treat the TCGA toolkit as authoritative for its supported tasks. Do not
  recreate a toolkit task in a notebook or inline script.
- Treat RNAseq-Templates notebooks, `RNAseq_lib/`, and the template CLI runners
  (`templates/<Topic>/run_analysis.R`) as authoritative for generic downstream
  workflows.

## Scientific guardrails

- Require integer-like raw counts for DESeq2. Do not silently run DESeq2 on
  TPM, FPKM, VST, rlog, or arbitrary normalized values.
- Never treat VST/rlog as TPM or attempt to invert it. TME workflows requiring
  abundance-scale input must use TPM or raw counts plus gene lengths.
- Match species, gene identifier type, genome annotation, and gene-set
  collection before enrichment or deconvolution.
- Model batch, pairing, repeated measures, and time as design variables when
  supported; do not substitute post-hoc batch correction for an appropriate
  statistical design.
- Inspect event coding, time units, missingness, and sample overlap before
  survival modelling.
- Report sample sizes and filtering losses. Flag underpowered comparisons and
  do not present exploratory thresholds as confirmatory findings.
- Keep counts, normalized matrices, metadata, and feature annotations as
  separate typed artifacts.
- Treat IOBR availability as a package-plus-data contract. Before enabling an
  offline TME run, verify that every requested method's reference bundle is
  cached; otherwise run the deterministic native ESTIMATE/ssGSEA path or report
  the network/cache requirement. Do not silently label an all-method failure as
  a completed deconvolution.
- Treat every online lookup as a network dependency, not just IOBR reference
  bundles: biomaRt/Ensembl ortholog conversion, annotation-DB queries, xCell,
  KEGG over the API, and public-cohort downloads can all fail mid-run (archive
  hosts time out; endpoints return 404/500). Prefer cached or offline paths —
  e.g. the RNAseq-Templates ortholog cache — and never report a network-failed
  step as complete.
- Invalidate cached intermediates when their inputs change. Recompute (do not
  reuse) a `deseq2_core_cache`, `tme_cache`, TPM matrix, or similar whenever the
  input table, sample set, filtering, gene universe, or a relevant parameter
  changes — a stale cache silently yields results from the wrong gene set.
- After a batch/headless run, confirm key figures are actually rendered
  (non-empty, plausible size). Grid-composite plots (UpSet, multi-panel GSEA)
  can silently produce blank PDFs from non-interactive `Rscript`.

## Scope boundaries

- This skill starts from expression matrices or prepared public-cohort data.
  FASTQ QC, alignment, transcript quantification, and MultiQC are upstream and
  are not implemented by these backends.
- Single-cell clustering, integration, trajectory, and cell-level modelling
  are out of scope. A single-cell-derived gene signature may be validated
  against bulk cohorts through the TCGA toolkit.
- Do not merge the RNAseq-Templates and TCGA repositories. Bridge them through
  routing, shared contracts, and explicit handoff files.
