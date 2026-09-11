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

## Task and decision ownership

Preserve established ownership. In a local-first project, the mapped/local
`TODO.md`, `PROJECT_STATUS.md` and `DECISION_LOG.md` own their respective task,
status and decision facts by default. If an already-confirmed external system
owns particular fields, use its verified schema and object IDs. Do not assume
a named vendor or the most recently edited copy is authoritative.

When ownership needs to be established or clarified, record the field group,
authoritative location/object, permitted writer and any derived view in the
existing project brief or equivalent record. Do not create another database
or require an ownership table for a routine checkpoint whose ownership is clear.
Changing the owner is a migration decision, not an incidental status update.

External ownership makes local task/status views source-linked pointers or
derived snapshots with version and last-verification time. Do not independently
edit their mirrored state or use them to overwrite the owner. If the owner is
unavailable, preserve last-known state with an explicit freshness limitation;
do not promote the snapshot to master or claim a successful remote write.
Local analysis manifests and run/artifact ledgers keep ownership of actual
computation evidence even when a remote system owns task progress.

`PROJECT_MAP.json` maps local file responsibilities only; it does not accept
remote URLs or configure synchronization. For formal local records, retain an
appropriate local pointer/snapshot where needed; audits inspect those local
files, not the external service's contents or synchronization correctness.

Before an authorized state change, read the owning value/version, match stable
task/decision/event IDs, compare proposed changes and reread at write time.
Reuse an existing record for repeated input. On conflicting edits, preserve
both versions and resolve the affected field instead of overwriting blindly.
Use a conditional-write API when available; rereading alone does not provide
atomicity. Record partial success per target and do not replay a successful
non-idempotent write. These are operating requirements, not implemented remote
adapters or a durable event-processing service.

## Management state and acceptance

Reuse existing milestone/task fields. For a substantive plan, link task ID,
milestone/deliverable, purpose, inputs, dependencies, owner if known, output,
acceptance criteria and next action. Unknown dates, owners and effort stay
unknown; do not add every field to a small administrative task.

Task states may distinguish `proposed`, `ready`, `in_progress`, `review`,
`done`, `waiting`, `blocked`, `paused` and `cancelled` when useful. Preserve
existing vocabularies and record mappings rather than bulk-converting history.
`ready` means the task has enough scope, inputs and authorization to proceed;
it is not scientific readiness. `waiting` describes pending input; `blocked`
requires an identified dependency that prevents the task. Neither automatically
pauses or cancels the whole project.

Milestone acceptance is separately `not_assessed`, `passed`, `conditional` or
`failed`, supported by agreed criteria and evidence. Record user-reported
completion as a user report. It can support administrative status when that
matches the agreed task, but cannot stand in for missing deliverables, required
checks or scientific acceptance. A task may be done while a scientific claim
remains exploratory or unauthorized. A valid negative result can satisfy the
task. Keep project lifecycle, task status, acceptance and the scientific axes
below distinct; stale information is a freshness property, not a lifecycle.

Execution assignments specify approved work and expected return evidence;
session handoffs preserve resumable state. Both link the same owning task and
evidence records, without creating a second editable backlog.

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

## Legacy scientific-state migration

This mapping applies only to historical scientific-evidence/readiness labels,
after identifying which object and state axis they described. Task status,
milestone acceptance and project lifecycle must not be converted through this
table. An old task marked `blocked` by a missing collaborator input does not
therefore have `readiness_status=blocked`.

Do not rewrite historical records or automatically upgrade legacy scientific labels:

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
| `SESSION_HANDOFF.md` | Exact resumable state | Resumable state/next action changes or a handoff is requested |
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

When the local project owns tasks, `TODO.md` (or its mapped equivalent) is the
canonical backlog. An external owner instead uses the pointer/derived-view
rules above; the format below is not an implemented synchronization protocol.
Use one checkbox line per local task:

- Status markers: `- [ ]` Backlog · `- [>]` In progress · `- [~]` Paused ·
  `- [x]` Done · `- [-]` Canceled.
- Optional suffixes: `#T01` stable task ID (assign once, never reuse) · `#high`
  / `#low` priority · `@YYYY-MM-DD` due date.
- A section carrying `P0`/`P1`/`P2` implies High/Medium/Low priority.
- A `NEXT` or `QUEUED` label alone does not prove execution started. Retain the
  actual task state; annotate `waiting`, `blocked` or `review` when the coarse
  checkbox cannot express it. Do not convert a blocked dependency into a
  deliberate pause or a proposed next task into in-progress work.

Update the owning task marker in place when supported; preserve IDs and dated
evidence, and do not invent completion. Bump `Last updated` on actual edits;
repeated unchanged input needs no new task, decision or timestamp churn.

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

For any records-only checkpoint, leave unchanged records untouched. Reading,
explanation or cosmetic edits alone do not justify a new handoff or decision
entry unless they change project state, decisions, artifact records or the next
action. A failed run or newly discovered limitation can change that state even
when no scientific result was produced.

For a narrow exploratory checkpoint, update only triggered records and expose
question, actual inputs/run, observation, uncertainty and next action. Preserve
the distinct scientific axes without forcing a full new readiness package for
every exploratory plot. A formal claim or delivery relying on readiness still
requires its scoped domain assessment and bindings; sparse notes never promote
an exploratory result into an authorized claim.
