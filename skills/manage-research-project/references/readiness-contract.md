# Scientific-readiness contract

Scientific readiness is scoped to one intended use. It is never a property of
the whole project, and it is not inferred from folder completeness or a
successful command.

## Supported interface and prototype boundary

`validate_readiness.py` and `research-readiness/v1` are the current supported
readiness path. `validate_scientific_readiness.py` and the v2 readiness/policy/spec
schemas are an experimental library with incomplete integration and validation;
they are not advertised as an execution, publication or scientific approval gate.
Direct CLI use exits with an explicit error instead of silently returning zero.
Do not relabel v2 JSON as v1. A future migration requires an explicit adapter,
positive and negative semantic fixtures, and a documented compatibility release.

`research-project-layout/v2` is already supported and does not imply readiness
v2 support. Keep the two version families distinct.

## Composing optional scientific reviews

Other skills are not installation dependencies. A supplied `ReasoningBrief` or
`WorkflowReview` may inform the question and design, but its draft version and
stage `READY` do not conform automatically to this readiness contract. Preserve
question/evidence IDs as provenance and record an explicit mapping to analysis,
source, artifact and run IDs. Missing bindings remain missing evidence. Only a
domain assessment with the required policy and evidence can authorize a claim.
The project manager can finish structure/integrity work while that assessment is
unavailable; do not invent one or force installation of a named assessor skill.

## Responsibility boundary

- A domain skill or named expert assessor owns the scientific gate policy and
  performs the domain assessment.
- `validate_readiness.py` checks schema, policy conformance, evidence
  references, source-ID closure and whether bound files are still current.
- The validator does **not** establish that a gate policy is scientifically
  sufficient, repeat the analysis, verify the truth of evidence, or certify a
  conclusion.
- `audit_project.py` is a structure/integrity audit and always reports
  `scientific_readiness: not_assessed`.

Review the gate policy itself when scientific stakes are high. A weak policy
can be internally conformant and still be scientifically inadequate.

Machine contracts require concrete scientific and identity strings. Human
project notes may carry `TODO:` while facts are unresolved, but a JSON policy,
specification or readiness report containing `TODO`, `TBD`, `UNKNOWN`, `N/A`,
`NA` or `NONE` placeholders is not a valid declaration.

## Orthogonal statuses

| Dimension | Values | Meaning |
|---|---|---|
| Contract | `valid`, `invalid` | The report, policy and references satisfy the machine contract |
| Currency | `current`, `unknown`, `stale` | Bound inputs/spec/code/environment/backend still match |
| Policy | `conformant`, `nonconformant`, `not_assessed` | Submitted gates, domain, study type and claim tuple match the bound policy |
| Declared readiness | `ready`, `review`, `blocked` | The domain assessor's result for the named intended use |
| Claim authorization | `authorized`, `conditional`, `not_authorized` | Whether any class may be stated as an authorized current claim |

`declared_ready_and_current=true` means only that a `ready` declaration is
contract-valid, policy-conformant and current. It is not a truth, efficacy,
causality, regulatory, ethical or reproducibility certificate.

## Gate aggregation

- A required gate with `FAIL` or `UNKNOWN` computes `blocked`.
- If all required gates pass or are justified `NA`, but an advisory gate is
  `FAIL` or `UNKNOWN`, readiness computes `review`.
- Otherwise readiness computes `ready`.
- Every `PASS` or `NA` must cite at least one typed evidence reference. A
  `file` reference is a safe project-relative path bound by SHA-256;
  `artifact`, `run` and `decision` references must close uniquely against the
  project registries or decision log and carry a `record_sha256` of that exact
  row or section. Artifact evidence additionally binds its registered path and
  content SHA-256; its row must identify the analysis, role, provenance state,
  propagated source IDs, byte size, time, access and lifecycle. For `PASS`/`NA`,
  registered artifacts must remain `current`; registered run evidence must
  close all input, output and validation artifact IDs, bind their exact row
  digests and collectively cover the assessed source IDs, bind its output rows,
  match the assessed execution context, and bind the bytes of a non-empty log
  inside its native run directory. It must retain completed/passed status.
  Later row, byte, log or run-state changes invalidate a record binding or make
  currency stale. Decision evidence must contain scoped decision,
  evidence/source, reason and date fields. An `external` reference must be a
  canonical DOI URL (`https://doi.org/...`, without query, fragment, credentials
  or port) or the assigned-name portion of an RFC 8141 URN. URI components must
  use RFC-style characters or valid percent encodings; encoded control bytes
  are rejected. Optional URN r-, q- and fragment components are deliberately
  outside this evidence-identity profile. An ordinary mutable HTTPS page is not
  enough to close current evidence; capture it as a hash-bound file/artifact or
  use a future digest-bound external-reference contract.
  Closure establishes identity and current bytes where available, not the truth
  or scientific sufficiency of the evidence.
- `NA` is accepted only when that gate's bound policy explicitly sets
  `allow_na=true`; a free-text assertion cannot bypass a mandatory gate.
- Every `FAIL` or `UNKNOWN` must state remediation.
- Submitted gate IDs, requiredness and requirements must exactly match the
  bound, versioned gate policy.

The gate policy declares its scientific `domain`, applicable study types and
data requirements, methodological basis, named assessor and assessor version,
and structured gate semantics: applicability, evaluation method, pass
condition, required evidence kinds and failure effect. A required gate must use
`failure_effect=block`; an advisory gate must use `failure_effect=review`. It
also authorizes explicit combinations of `analysis_mode`, claim class and
achieved validation level. Unsupported combinations are invalid; they are never
silently downgraded.

Machine claim authorization applies only to the structured
`claim_authorization`, `authorized_claim_classes` and
`prohibited_claim_classes`. A `ready` report must set authorization to
`authorized` and include its `requested_claim_class`; `review` is
`conditional`, and `blocked` is `not_authorized`, both with an empty authorized
list. Every authorized class must be permitted by the bound policy for the
declared mode and achieved validation level. Natural-language
`claim_boundary_notes` are explanatory and are not semantically validated; do
not treat their wording as machine-authorized merely because the contract is
valid.

## Required freshness bindings

A `research-readiness/v1` report binds, by project-relative path and SHA-256:

- the versioned gate policy;
- the analysis specification;
- the input source manifest and the exact source IDs used;
- a code integrity manifest covering the actual executable code;
- an environment lock or snapshot;
- any additional dependencies that could change the result.

The bound analysis specification must follow
`research-analysis-spec/v1`. Its analysis/scope IDs, intended use, source IDs,
mode, requested claim class and backend revision must match the readiness
report. The spec records a target validation level while the report records the
achieved level. The policy domain, assessor name/version, study type and data
requirement must all close against policy applicability. Every spec entry point
must occur in the verified code manifest. See
[analysis-spec-contract.md](analysis-spec-contract.md).

It also records code dirty state and code/backend revisions. Supply current
revision and dirty-state values to the validator; omitted values make currency
`unknown`. The code manifest is recursively verified, so changing or adding a
file inside its declared scope makes readiness currency stale even if a
revision label is unchanged.

Currency becomes stale after any relevant input, spec, gate policy, code,
environment, reference database, model, backend or dependency changes. Do not
edit the old report to hide drift; create a new assessment and supersede the old
record.

## Source requirements

For data-bearing analyses, `source_provenance_status` must be `verified` before
a ready declaration is usable for workflow gating. Every `input_source_id` must
exist in the bound source manifest, and the current source bytes must pass
manifest verification. Verified provenance additionally requires concrete
source system, source reference, acquisition time, data-freeze identity and
access/identifier context; checksums alone establish integrity, not provenance.
`unverified` or `conflicting` sources compute blocked.

Use `not_applicable` only when the intended use genuinely has no data source;
then `input_manifest` must be null and `input_source_ids` empty.

The generic validator checks internal semantic closure, not biological or
clinical truth. It cannot infer from free prose that a falsely declared
data-free analysis is actually observational, decide whether a gate policy
contains the right domain tests, verify that a DOI resolves, or judge whether
the cited evidence supports the claim. Propagated source IDs likewise state and
freeze lineage but do not prove that code truly used those inputs. Those remain
explicit domain-assessor responsibilities.

## Commands

```bash
python scripts/validate_readiness.py /path/to/project \
  analysis/readiness/A-001.json --json

python scripts/validate_readiness.py /path/to/project \
  analysis/readiness/A-001.json --require-ready \
  --current-code-revision COMMIT_OR_SNAPSHOT \
  --current-code-dirty false \
  --current-backend-revision BACKEND_VERSION
```

Use `--max-age-days` only as an additional governance limit. Age alone cannot
make an otherwise inadequate assessment valid.
