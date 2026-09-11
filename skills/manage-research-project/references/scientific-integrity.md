# Scientific state and provenance boundaries

## Scientific integrity rules

- State the experimental unit before statistical testing.
- Separate technical replicates, biological replicates, samples, cells and
  features. List the declared unit hierarchy from the independent level toward
  nested observations and require the named independent and observation units
  to occur in it; domain review must still test whether independence is true.
- Record comparisons, models, covariates, thresholds and multiple-testing rules.
- Separate source provenance, source integrity, implementation, execution,
  technical validation, readiness, contract, currency, policy, analysis mode,
  claim authorization, target/achieved validation, lifecycle and reproduction
  states.
- Do not infer causality from association, enrichment, co-purification,
  correlation or cross-omics concordance alone.
- Keep exploratory and confirmatory outputs visibly distinct.
- Bind each readiness assessment to one intended use, exact source IDs,
  analysis spec, gate policy, code manifest, environment snapshot and relevant
  backend. Require policy assessor name/version and domain to match, and policy
  applicability to include the spec study type and explicit data requirement.
- Require data-bearing specs to bind source IDs, a domain spec and domain
  parameters; a data-free declaration is valid only with no source IDs and a
  null domain spec. The generic validator cannot infer a false declaration
  from prose, so the domain assessor must check semantic truth.
- Require evidence runs to match the assessed spec, declared entry point, code
  state, backend and environment; close their artifact IDs and logs before
  using them for `PASS` or `NA`.
- Require a domain-specific gate policy; do not invent generic statistical
  approval rules inside this project-management skill.
- Domain-assessor skills, scLucid and external project tools are optional.
  Without them, complete project structure, integrity, provenance and handoff
  work directly, leaving scientific readiness `not_assessed`. Record missing
  domain evidence rather than requiring another skill merely to organize files.
- Report limitations that could change the conclusion near that conclusion.
- Preserve raw identifiers and explicit mappings to public/display labels.
- For human data, preserve subject → specimen → library/capture → observation
  hierarchy without recording direct identifiers or re-identification keys.
