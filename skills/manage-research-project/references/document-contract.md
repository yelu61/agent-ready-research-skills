# Project document contract

## Scale the records to the work

The document and machine-state tables below describe formal responsibilities.
For a small pilot, [exploratory-profile.md](exploratory-profile.md) keeps the
working history in `PROJECT_NOTES.md` without requiring separate documents or
every state field. Still distinguish what ran, what was observed, what remains
unverified and what should happen next. Formal reporting or readiness-dependent
delivery requires the applicable evidence contracts.

Document names denote roles. Resolve actual formal document paths through
`PROJECT_MAP.json` when present; see [project-map.md](project-map.md). A path
mapping does not validate contents or authorize duplicating a source of truth.

## Responsibility-specific sources of truth

There is no universal source-of-truth ranking for every scientific question.
Resolve each fact from the record that owns that responsibility:

| Question | Primary record |
|---|---|
| Which source bytes and identifiers were acquired? | source snapshot/manifest plus repository or instrument metadata |
| What was prespecified? | protocol, SAP or immutable analysis specification |
| What command actually ran? | run record, config snapshot and log |
| Which bytes did the run consume/produce? | artifact and run registries with hashes |
| What is currently ready for a named use? | current domain readiness report and bound gate policy |
| What is the current interpretation? | current finding linked to source, run, readiness and decision records |

When records conflict, do not silently select the most convenient one. Record
the conflict, its effect and the supported resolution in `DECISION_LOG.md`.
Raw-byte integrity does not prove provenance authenticity; execution success
does not prove design validity; statistical significance does not prove
causality or truth.

## Orthogonal scientific state model

Never compress these dimensions into a single evidence label:

| Axis | Values |
|---|---|
| `source_provenance_status` | `verified`, `unverified`, `conflicting`, `not_applicable` |
| `source_integrity_status` | `not_assessed`, `pass`, `review`, `fail` |
| `implementation_status` | `planned`, `implemented`, `unavailable`, `superseded` |
| `execution_status` | `not_run`, `running`, `completed`, `partial`, `failed` |
| `technical_validation_status` | `not_assessed`, `passed`, `review`, `failed` |
| `readiness_status` | `not_assessed`, `ready`, `review`, `blocked` |
| `contract_status` | `not_assessed`, `valid`, `invalid` |
| `currency_status` | `not_assessed`, `current`, `unknown`, `stale` |
| `policy_status` | `not_assessed`, `conformant`, `nonconformant` |
| `analysis_mode` | `descriptive`, `exploratory`, `confirmatory`, `predictive`, `causal` |
| `requested_claim_class` | `observation`, `association`, `prediction`, `causal_effect`, `mechanism`, `translational`, `clinical_utility` |
| `claim_authorization` | `authorized`, `conditional`, `not_authorized` |
| `target_validation_level` | `none`, `sensitivity`, `orthogonal_same_material`, `independent_external`, `prospective` |
| `achieved_validation_level` | `none`, `sensitivity`, `orthogonal_same_material`, `independent_external`, `prospective` |
| `lifecycle_status` | `current`, `superseded`, `invalidated`, `archived` |
| `reproduction_status` | `not_tested`, `reproduced`, `failed`, `environment_mismatch` |

`technical_validation_status=passed` must name its validation kind, scope,
criterion and evidence IDs. It cannot silently mean technical QA, model
diagnostics, biological confirmation and external replication at once. Target
validation is a plan; achieved validation is evidence-backed history. `ready`
is scoped to an intended use and does not mean a claim is true. Staleness is a
`currency_status`, never a fourth readiness result.

## Legacy-state migration

Do not rewrite historical records or automatically upgrade legacy labels:

- `confirmed` or `supported`: preserve the original wording, set current
  readiness to `review`, and split the record across the new axes after review;
- `exploratory`: may map only to `analysis_mode=exploratory`; assess every other
  axis independently;
- `blocked`: map to `readiness_status=blocked` and record the gate/blocker;
- `stale`: map only to `currency_status=stale`; retain the last declared
  readiness as historical assessor output and prevent current authorization;
- `superseded`: map to `lifecycle_status=superseded` and name `superseded_by`.

Log any migration decision and, when paths or many records change, use
`provenance/MIGRATION_MAP.tsv`.

## Document ownership

| Document | Owns | Update trigger |
|---|---|---|
| `README.md` | Human entry point and navigation | Layout or canonical entry points change |
| `AGENTS.md` | Stable cross-agent behavior | Rare policy change |
| `CLAUDE.md` | Compact operational entry | Tool/runtime instructions change |
| `PROJECT_BRIEF.md` | Stable question, design and constraints | Scientific scope/design confirmed or changed |
| `PROJECT_STATUS.md` | Current stage, structural status, blockers and next task | Meaningful task changes state |
| `SESSION_HANDOFF.md` | Exact resumable state | End of meaningful session |
| `DECISION_LOG.md` | Append-only decisions and supersessions | Analysis or interpretation decision |
| `DATA_DICTIONARY.md` | Data/artifact identity, IDs, fields and transformations | New/changed data or semantics |
| `DATA_GOVERNANCE.md` | Sensitive-data authority and use boundaries | Access, agreement or disclosure rule changes |
| `ANALYSIS_PLAN.md` | Intended questions, estimands and validation | Planned methods change |
| `docs/PIPELINE.md` | Actual runnable flow and separated implementation/execution/validation state | Entry point/dependency/output changes |
| `READINESS.md` | Index of domain readiness declarations | Assessment, binding or freshness changes |
| `RESULTS_SUMMARY.md` | Current evidence-linked findings and claim boundaries | Verified observation or interpretation changes |
| `REPRODUCIBILITY.md` | Environment, reproduction scope and commands | Runtime or reproduction information changes |
| `TODO.md` | Actionable backlog | Task opened, closed or reprioritized |
| `ARTIFACTS.tsv` | Artifact identity and lineage | Artifact registered, changed or retired |
| `RUNS.tsv` | Actual execution history | Run starts or terminates |
| `AUTHOR_QUERIES.md` | Facts no analysis can determine | Unresolved experiment/reporting fact found |
| figure/deliverable manifests | Deliverable identity and provenance | Artifact created, selected, replaced or archived |

## Task backlog format (`TODO.md`)

`TODO.md` is the canonical task list and sync contract with external tools. One
checkbox line per task:

- Status markers: `- [ ]` Backlog · `- [>]` In progress · `- [~]` Paused ·
  `- [x]` Done · `- [-]` Canceled.
- Optional suffixes: `#T01` stable task ID (assign once, never reuse) · `#high`
  / `#low` priority · `@YYYY-MM-DD` due date.
- A section carrying `P0`/`P1`/`P2` implies High/Medium/Low priority.
- Table statuses `NEXT`, `QUEUED`, `OPTIONAL`, `BLOCKED`, `DONE` map to In
  progress, Backlog, Backlog + Low, Paused and Done.

Update a task marker in place; do not turn completed work into unsupported prose
history. Bump `Last updated` on every edit.

## Update discipline

- Keep stable facts separate from temporary state.
- Keep intended methods separate from implemented and executed methods.
- Use ISO dates, stable analysis/claim/artifact/run IDs and append-only decision
  IDs such as `D-20260730-01`.
- Never delete an old decision; append a superseding entry.
- Store detailed provenance in manifests/registries, not agent instructions.
- For v2 projects, preserve the single ownership chain
  `workflows → analysis/runs → results`. Let the domain/user select question
  or module navigation within results. Treat backend-native
  subdirectories as run internals rather than project-level categories.
- Keep one canonical document per responsibility.
- Mark input, spec, gate policy, code, environment or backend changes as
  readiness-currency-staling events until reassessed.
- Never put direct identifiers, linkage keys or credentials in project memory.

For a narrow exploratory checkpoint, update only triggered records and expose
question, actual inputs/run, observation, uncertainty and next action. Preserve
the distinct scientific axes without forcing a full new readiness package for
every exploratory plot. A formal claim or delivery relying on readiness still
requires its scoped domain assessment and bindings; sparse notes never promote
an exploratory result into an authorized claim.
