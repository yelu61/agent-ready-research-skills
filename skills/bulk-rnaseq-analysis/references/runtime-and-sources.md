# Runtime, backend dependencies and methodological sources

Last source check: 2026-09-08. A documentation version is not a tested runtime.

## Dependency and acquisition boundary

- Routing, preflight, capability records, backend locks and registration use
  Python 3.11+ standard library; no scientific packages or network are needed
  to plan/audit supplied information. Backend lock verification also uses Git.
- Numerical execution requires a separately obtained RNAseq-Templates or TCGA
  toolkit checkout plus its own R/package environment. The skill does not
  bundle either backend, R packages, controlled datasets or reference data.
- Candidate discovery uses explicit environment roots or documented local
  locations. A sentinel match, version label, or `found=true` never implies
  readiness. `found=false` is a completed discovery result with execution false.
- No canonical public backend URL or publicly tested revision is asserted by
  this package. Use the user's authorized checkout or an existing cloneable
  source/full-commit lock. Inspect an origin without exposing URL credentials;
  the lock rejects credential/query-bearing URLs. Do not invent an address or
  install a substitute pipeline because a backend is missing.
- An existing lock can be obtained from a project and materialized with
  `scripts/backend_lock.py materialize --lock /path/to/backend.lock.json`.
  The cache stays outside the project. Obtain user-authorized network access
  when needed; planning/audit do not depend on acquisition succeeding.
- Source-review/contract-test capability records bind an exact source and
  revision once and are reusable. Follow
  [analysis-spec.md](analysis-spec.md) to prepare, complete and bind them.
  The bundled catalog has no fabricated tested-commit entry. A dirty checkout
  cannot be declared equivalent to a reviewed revision.
- Notebook/CLI entry points, parameter validation and native outputs stay as
  documented in [rnaseq-templates.md](rnaseq-templates.md),
  [tcga-toolkit.md](tcga-toolkit.md) and [output-contract.md](output-contract.md).

## Method/source map

| Source checked | Supported rule | Applicability and limits |
|---|---|---|
| [DESeq2 official vignette](https://bioconductor.org/packages/release/bioc/vignettes/DESeq2/inst/doc/DESeq2.html), page reports DESeq2 1.52.0, 2026-04-28 | Count-model routes must receive unnormalized counts; transformed/normalized matrices do not preserve the required measurement model | Official tximport/tximeta routes support estimated counts with their provenance/length handling. These are valid separate routes, not permission to round TPM or a capability implemented by this skill |
| [limma official manual](https://bioconductor.org/packages/release/bioc/manuals/limma/man/limma.pdf), version 3.68.5, manual retrieved 2026-09-08, voom notes | Do not feed TPM/RPKM/CPM directly to voom; its weights depend on original library-size information | This restriction concerns voom, not every valid limma model. Current manual discusses voomLmFit, but this release does not add or numerically test that backend method |
| [R stats formula documentation](https://stat.ethz.ch/R-manual/R-devel/library/stats/html/formula.html) | Interaction, nesting and expansion syntax differs from an additive model | Preflight conservatively recognizes ordinary operators, not arbitrary executable R formulas. Backend model matrix, estimability and sample units still require review |

All three official pages above were actually retrieved for this change. The R
formula page reported stats 4.6.0 (R-devel); recheck the relevant installed R
version when extending the supported formula grammar. Do not infer that the reported
package versions have been installed or run in the user's environment.

## Exact backend evidence and changing interfaces

Before binding a gate, inspect the functions and configuration schema in the
actual checkout and retain a scoped source-review or existing test artifact.
For TCGA external validation the relevant paths are
`tcga_toolkit/scripts/task_external_validate.R` and
`tcga_toolkit/scripts/task_prognostic_model.R`; inspect model metadata export,
transform selection, coefficient/feature coverage, covariates, cutoff and the
actual matching of clinical records. Do not infer these from three booleans.

Source review during this change found that one available checkout still used
a magnitude heuristic for transform selection and a weighted sum that omits
clinical covariates. The conservative predictive gate documents its supported
branch and rejects unsupported model shapes. This inspection did not establish
a clean, numerically tested release revision; no binding was shipped for it.

When package versions, backend revision or input formats change, recheck the
affected official documentation and backend contract. Keep source URL, actual
check date, version observed, relevant function/section, artifact digest and
negative cases distinct from a numerical validation claim.

## What the bundled checks establish

Regression tests exercise synthetic scale/task combinations, nested schema
types, interactions, independent mode sets, exact Git lock/revision binding,
capability/schema/evaluator/evidence drift, blocked versus plan-only state and
actual-file prediction evidence with patient-overlap/configuration counterexamples.
They also retain router/lock/registration behavior. Synthetic Git and matrix
fixtures do not validate DESeq2, limma, survival estimates or real backend runs.

The authored instructions and helpers are distributed under this package's
license. Linked documentation and external backend code retain their own
licenses; no external publication, dataset or backend code is redistributed.
