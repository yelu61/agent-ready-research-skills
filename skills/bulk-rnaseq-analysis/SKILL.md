---
name: bulk-rnaseq-analysis
description: Orchestrate reproducible bulk RNA-seq downstream analysis across local expression matrices, GEO datasets, and TCGA/TARGET/GTEx cancer cohorts. Use for raw-count, TPM, VST/rlog, clinical, MAF, CNV, or methylation inputs; template selection; QC; DESeq2 or limma-voom differential expression; ORA/GSEA/GSVA; time-course analysis; TME deconvolution; WGCNA; survival and clinical association; pan-cancer, mutation, multi-omics, prognostic, external-validation, drug-response, and report workflows. Route generic matrix-based work to RNAseq-Templates and cancer-cohort or multi-omic work to the TCGA toolkit.
---

# Bulk RNA-seq Analysis

Use this skill as the single user-facing entry point for bulk RNA-seq
downstream analysis. Keep project-authored analysis logic in one
`workflows/bulk-rnaseq/` source root and keep the selected backend external;
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
   - Analysis spec and claim gating: [references/analysis-spec.md](references/analysis-spec.md)
   - Final delivery and provenance: [references/output-contract.md](references/output-contract.md)

5. Gate the claim, not just the route. The router only selects a backend and
   blocks scale-incompatible requests (e.g. TPM→DESeq2, exit code 3). Before
   any confirmatory/predictive claim, write a BulkAnalysisSpec v1 (see
   [references/analysis-spec.md](references/analysis-spec.md)) and run:

   ```bash
   python3 scripts/preflight.py check --spec spec.json --backend-revision <rev>
   ```

   Preflight compares the requested `claim_class` against
   `assets/backend-capabilities.json`; exit 3 means the claim is blocked and
   the gate's `min_fix` says what is missing. Readiness records are
   hash-stamped: re-run `preflight.py verify` after any spec/input/backend
   change — a stale record invalidates the previous verdict. This is a backend
   capability preflight, not the project's scientific assessment or approval
   of the observed results. Keep execution checks and domain review separate.

6. Inspect real column names, group sizes, identifiers, and repository state
   before writing configuration. Reuse existing templates and task runners.
   For General, use `RNAseq_General` for interactive work and the CLI for batch
   execution; honor the user's preferred entry. Both call the same public
   stages and may produce a formal run after validation. Do not create a
   RunReview notebook or copy backend logic into project scripts by default.
   The five topic templates retain their existing runners; verify their
   individual notebook parity before treating them as interchangeable.

   Read `provenance/PROJECT_LAYOUT.json` when present. In a v2 project, place
   config, scripts and source notebooks only under
   `workflows/bulk-rnaseq/`. Do not create top-level `scripts/` or
   `notebooks/`, `analysis/config/`, `analysis/scripts/` or an
   `analysis/backend/` checkout. A project without the layout manifest is
   legacy: preserve its established canonical source paths unless migration is
   separately requested.

7. Lock the selected backend before execution. A v2 workflow records only its
   cloneable source and full commit, never a local absolute path:

   ```bash
   python3 scripts/backend_lock.py create \
     --backend rnaseq-templates --root <discovered-backend-root> \
     --output workflows/bulk-rnaseq/backend.lock.json
   python3 scripts/backend_lock.py verify \
     --lock workflows/bulk-rnaseq/backend.lock.json \
     --root <discovered-backend-root>
   ```

   Use backend ID `tcga-toolkit` instead when routing to that backend.
   Use `materialize` when the locked revision is not installed. It clones into
   an external user cache and refuses a cache inside the project. Lock creation
   refuses a dirty checkout, a non-cloneable/local-only origin, or overwrite.

8. Declare a namespaced run ID
   (`bulk-rnaseq__<run_label>`) and separate the complete backend-native bundle
   from reviewed deliverables before execution. Never use `notebooks/` as an
   implicit output root and never overwrite an existing run directory; use a
   new run label.

   Use one native bundle per actual execution, whether driven by notebook or
   CLI, under `analysis/runs/`. Reuse saved model/results for downstream changes
   with matching input and model parameters; do not rerun the whole pipeline
   just to change entry point, threshold, plot or delivery layout. See the
   "Execution and change scope" section of
   [references/output-contract.md](references/output-contract.md).

   For an RNAseq-Templates CLI run, make the run root explicit: enter
   `analysis/runs/bulk-rnaseq__<run_label>/` before invoking the locked central
   runner. Resolve the config argument before execution, and make
   every relative input/output path relative to that run root. Never rely on a
   template source directory as an implicit working directory.

9. Validate before execution. Prefer dry-runs, dependency checks, and bundled
   smoke tests.

   When reviewing historical results after a backend fix, use the historical
   result review procedure in [references/rnaseq-templates.md](references/rnaseq-templates.md).
   Match the actual old revision, entry point and configuration to a documented
   defect before deciding which outputs need recomputation. Verify capabilities
   at the locked revision; current skill instructions do not add new APIs to an
   older backend.

10. Execute the declared modules, comparisons and every threshold's dependent
    tasks. Check explicit completed, empty, not-applicable, disabled or failed
    states; a missing plot or an ORA failure is not a zero-result finding.
    Export the complete reviewed modules and a concise scientific report to a
    portable `results/` tree using the backend exporter. Summarize methods,
    parameters, warnings, result locations and provenance. Keep scientific
    questions in the report/index; module folders are valid delivery navigation.

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
  statistical design. Secondary tests (GSVA scores, single-gene plots) must
  inherit the pairing structure too — under a paired design an unpaired
  t-test is the wrong model, not a simpler one.
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
