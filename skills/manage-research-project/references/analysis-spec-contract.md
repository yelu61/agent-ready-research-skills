# Generic analysis-spec contract

`research-analysis-spec/v1` is a small, domain-neutral envelope. It gives one
analysis and readiness assessment a stable identity; it does not replace a
bulk RNA-seq, single-cell, survival, imaging or other domain specification.

## Required identity and intent

The JSON object records:

- `analysis_id` and the narrower `scope_id` assessed;
- the question, intended use, estimand/target quantity;
- independent and observation units;
- study type, explicit `data_requirement`, analysis mode, requested claim class
  and target validation level;
- exact source IDs from `provenance/SOURCE_MANIFEST.json`;
- preregistration/prespecification versus post-hoc status;
- domain and hash-bound `domain_spec` for data-bearing analyses;
- backend revision, one or more project-relative executable `entry_points`,
  domain parameters and creation time.

Put detailed domain fields in the domain spec or `domain_parameters`; do not
weaken a domain contract to fit this envelope. If a domain spec is bound, its
path and SHA-256 become part of readiness currency.

List `design.unit_hierarchy` from the independent level toward the nested
observation level (for example donor → specimen → cell). Both
`independent_unit` and `observation_unit` must occur in that list, as its first
and last elements respectively; they may be the same when each observation is
independent. This machine check exposes an internally inconsistent declaration
but does not decide whether the declared independence assumption is
scientifically defensible.

## Closure rules

The readiness report must exactly match the envelope's analysis ID, scope,
intended use, input source-ID set, analysis mode, requested claim class and
backend revision. The report records `achieved_validation_level` separately
from the spec's `target_validation_level`; progress short of the target is not
contract drift. The gate policy's `domain` must equal the spec domain, and the
spec `study_type` and `data_requirement` must occur in the policy's declared
applicability. A matching hash for a semantically different spec is therefore
insufficient.

Every source ID must also occur in the bound source manifest. The execution run
then records the analysis-spec and readiness paths/hashes plus actual input and
output artifact IDs. Every declared entry point must be covered by the bound
code manifest, and a cited run must name one of those entry points. This forms
the minimum spec → readiness → run lineage.

For `data_requirement=data_bearing`, source IDs, a hash-bound domain spec and
non-empty domain parameters are mandatory. For `data_requirement=none`, source
IDs must be empty and `domain_spec` null. This explicit switch prevents a
data-bearing study from bypassing provenance merely by calling its inputs “not
applicable.” It does not infer data needs from prose; the domain assessor must
reject a semantically false declaration.

## Change discipline

Treat an assessed spec as immutable. If the question, cohort, unit, contrast,
estimand, study type, data requirement, source set, entry point, model intent,
validation target or backend changes, create a new spec/version and readiness
assessment. Record post-hoc changes honestly; do not relabel them as
prespecified. A confirmatory analysis cannot use `post_hoc` or
`not_applicable`; an unresolved protocol deviation blocks readiness.

A complete envelope makes intent auditable. It does not establish that the
estimand, design or method is scientifically appropriate; that judgment belongs
to the bound domain gate policy and its reviewer.
