# BulkAnalysisSpec and preflight

The router selects a backend. Preflight checks supplied contracts and capability
compatibility. Neither certifies the design, observed results, predictive
performance or clinical utility.

## Independent modes and schema

The v1 field `claim_class` remains compatible, but its values are an explicit
set, not an ordered ladder. `descriptive` describes patterns;
`exploratory` and `confirmatory` describe inferential intent; `predictive`,
`causal` and `clinical` name distinct targets. The capability catalog lists
`allowed_claim_modes` per task. There is no automatic implication from one
mode to another. Causal/clinical modes currently have no available gate.

The complete bundled schema is enforced, including nested types, unknown
fields and enums. Count-engine tasks also require an explicit `design.formula`.
For additive-only time-course work, `*`, `:`, `/`, `^`, `%in%` and `interaction()` syntax is
blocked even if `interaction` is absent or false. This is a conservative
supported-formula check, not an R formula parser or rank/estimability test.
Do not conceal an interaction inside derived variables or functions; inspect
the actual backend config/model matrix before execution.

`scripts/analysis_contract.py` is the shared input-scale authority for router
and preflight. DESeq2/deg, limma-voom and time-course accept `raw-counts` only.
TME accepts `tpm` or `raw-counts` with method-specific preparation/gene lengths.
`other`, `unknown` and transformed scales cannot evade these whitelists.
This does not claim that all legitimate RNA-seq methods require raw counts.

## Audit without a backend

Run from the installed skill directory, or use absolute helper paths:

```bash
python3 scripts/preflight.py check --spec /path/to/spec.json --mode audit
python3 scripts/preflight.py verify \
  --spec /path/to/spec.json --readiness /path/to/spec.readiness.json
```

An audit can finish without either backend installed. Compatible input returns
`verdict=plan-only`, `execution_ready=false`, exit 0. Existing named input files
are hashed; an empty `inputs` object is allowed only for planning and blocks
execution. Missing files named in a spec are errors, not invented evidence.
A blocked capability returns exit 3, including its reason and minimum remedy.
Exit 0 alone must never be treated as permission to execute.

## One reusable capability review per exact backend revision

The shipped catalog states required behavior but contains no verified revision
bindings. Discovery sentinels and a recent version label are insufficient.

1. Obtain a backend checkout from a source the user can access, or materialize
   an existing lock. Verify a clean full revision. Do not guess a canonical
   repository URL or silently commit a user's dirty backend.
2. Reuse a review/bound catalog already covering the same source, revision and
   exact capability declarations. Otherwise create a scoped template:
3. Inspect the selected gate's implementation and existing tests at that
   revision. Reuse verifiable existing evidence or run the backend's documented
   relevant contract tests when dependencies are available. Save the output or
   source-review findings, including paths/functions, assumptions and limits.
   Do not mark a template as passed, use synthetic helper tests as evidence of
   real R behavior, or claim unrun numerical validation.
4. Populate the template's assessor, actual review date, scope and checks.
   Each check names a gate, `kind=contract-test` or `source-review`,
   `result=pass` only when justified, and a nonempty evidence artifact with its
   actual SHA-256. Artifact paths are relative to the review JSON or absolute.
   Multiple gate checks can refer to one properly scoped report.
5. Bind once and reuse while all evidence remains unchanged:

```bash
python3 scripts/backend_lock.py create \
  --backend rnaseq-templates --root /path/to/clean-backend \
  --output /path/to/project/workflows/bulk-rnaseq/backend.lock.json
python3 scripts/preflight.py prepare-review \
  --backend-lock /path/to/project/workflows/bulk-rnaseq/backend.lock.json \
  --gate-id rnaseq.deg \
  --output /path/to/capability-reviews/review.json
# Inspect real backend evidence and complete this unassessed template.
# Compute the artifact digest without reading sensitive contents to the console:
python3 -c 'import hashlib,pathlib; print(hashlib.sha256(pathlib.Path("/path/to/capability-reviews/evidence.txt").read_bytes()).hexdigest())'
python3 scripts/preflight.py bind-capabilities \
  --backend-lock /path/to/project/workflows/bulk-rnaseq/backend.lock.json \
  --backend-root /path/to/clean-backend \
  --review-evidence /path/to/capability-reviews/review.json \
  --output /path/to/capability-reviews/bound-capabilities.json
```

`prepare-review` fills exact lock and catalog identities; it deliberately
records `not-assessed`. `bind-capabilities` refuses that unfinished state,
missing/mismatched artifacts, another revision, or altered capability
declarations. It saves a separate non-overwriting catalog, leaving the bundled
catalog unchanged. It is evidence bookkeeping, not a human approval prompt or
a requirement to review every run. An agent may perform this already-authorized
read-only review and record its actual evidence. A new revision, a new gate or
a changed declaration needs evidence for the changed contract.

These local review records may contain project paths; do not copy them into
the distributable skill. Relative evidence paths can be used in a portable
copy, after rechecking and reissuing the local readiness record.

## Execution and revalidation

```bash
python3 scripts/preflight.py check --spec /path/to/spec.json --mode execute \
  --capabilities /path/to/capability-reviews/bound-capabilities.json \
  --backend-lock /path/to/project/workflows/bulk-rnaseq/backend.lock.json \
  --backend-root /path/to/clean-backend
python3 scripts/preflight.py verify \
  --spec /path/to/spec.json --readiness /path/to/spec.readiness.json
```

`execution_ready=true` requires compatible inputs and supported mode, a
matching backend/source/full commit, a clean actual checkout, and covered
revision-specific evidence. Both notebook and CLI continue using their formal
backend runners and existing result-registration contract.

Readiness v2 hashes spec/input files, capability catalog, both bundled schemas,
the evaluator and helper code, lock bytes, actual checkout identity and review
artifacts. `verify` reads the recorded paths, rechecks actual checkout state and
re-evaluates the verdict. It does not rely on a caller-supplied revision string.
The obsolete `--backend-revision` option is rejected; migrate to a real lock.
Legacy records require a new check.

| Result | Exit | Meaning |
|---|---:|---|
| audit compatible, plan-only | 0 | Complete audit; execution remains false |
| execute ready | 0 | Supplied execution contracts satisfied, not scientific certification |
| current blocked record | 3 | Freshness cannot turn a blocked request into ready |
| any dependency/verdict drift | 4 | Re-run check with current evidence |
| malformed spec/evidence | 2 | Correct the described input error |

## Predictive external-validation evidence

The existing TCGA external validator is a limited linear weighted-score route.
Three `locked_*` booleans remain valid legacy schema fields but never elevate
a claim. For predictive mode, use `experimental_unit=patient` and
`split_policy.level=patient`; provide all six named `inputs`:

- `model_meta_file`: the actual exported JSON with unique features, finite
  named coefficients, finite training cutoff, `method=lasso_cox` and
  `transform=log2p1`. Model clinical covariates are blocked because this external
  weighted sum does not reproduce them.
- `backend_config`: actual `task=external_validate` configuration. Its
  `model_meta_file`, `expression_file` and `clinical_file` must be absolute
  paths matching the hashed inputs. Remove weight/signature/feature/cutoff
  overrides that would silently replace the locked model.
- `expression_file` and `clinical_file`: inspectable CSV/TSV inputs. All locked
  features must exist; sample IDs must be unique and match membership exactly.
  Supply positive follow-up and explicit 0/1 events. The backend's 20-complete-
  patient minimum is checked; this is an implementation limit, not sufficient
  power or precision.
- `training_units` and `validation_units`: JSON evidence from actual training
  sample provenance and reconciled external patient identities. Each has
  `unit:"patient"`, the same `unit_namespace`, and `samples` rows with
  `sample_id` and `patient_id`. The training document includes
  `model_meta_sha256`; the validation document includes `expression_sha256` and
  `clinical_sha256`. Derive these digests from the actual files. Patient and
  sample sets must be disjoint; multiple validation samples per patient are
  blocked until handled by a supported patient-level design.

Example membership row structure (IDs below are illustrative only):

```json
{"unit":"patient","unit_namespace":"study-reconciled-patient-ids",
 "samples":[{"sample_id":"sample-A","patient_id":"patient-A"}],
 "model_meta_sha256":"<actual exported model SHA-256>"}
```

The inspected external backend still decides whether to log-transform via
`max(expression)>100` even with metadata. Predictive gating therefore accepts
only explicitly documented `log-tpm` (log2(TPM+1)) input whose finite,
nonnegative values stay in its no-transform branch (`<=100`). This numeric
branch check cannot prove normalization provenance: retain the actual training
and external preprocessing records and review their compatibility. Other
scales remain available for exploratory work or need a separately verified
backend contract; this skill does not add a new transformation implementation.

Hashes and matching IDs cannot prove that an identity map is truthful, that
an external cohort was never used for model selection, or that predictions
are calibrated. Review development/selection provenance, ascertainment,
follow-up, missingness, censoring, event counts, discrimination and calibration
separately. No predictive compatibility result establishes mechanism or
clinical utility. See [sources and runtime](runtime-and-sources.md).
