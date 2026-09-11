# Record a scoped project checkpoint

Read [the document contract](document-contract.md) for the affected record's
owner, completion evidence and update trigger. Change only the owning record;
external-master fields remain source-linked locally. An administrative update
needs neither an external integration nor a new readiness package.

## Phase 4 — Checkpoint after meaningful work

Treat changed project facts as part of the task's definition of done. Update
only the documents whose trigger fired; reuse unchanged records and existing
evidence. Do not initialize missing governance infrastructure merely to record
a small change. In exploratory mode, update the matching note
sections instead of creating all documents below. Link existing inputs, commands,
outputs and limitations; never invent run IDs or infer validation from a plot.

1. Update the owning task/status record when completed work, blockers or next
   task changed. Reflect only verified owner changes in local derived views.
2. Update `SESSION_HANDOFF.md` when the resumable state or next action changed,
   or a handoff is requested; leave an already-current handoff unchanged.
3. Append to `DECISION_LOG.md` when a threshold, model, exclusion, annotation,
   reference, interpretation or deliverable choice was made.
4. Update `DATA_DICTIONARY.md` when data, fields, IDs, missing encodings or
   transformation state changed.
5. Update `ANALYSIS_PLAN.md` and `docs/PIPELINE.md` when planned or actual logic
   changed.
6. Add current findings to `RESULTS_SUMMARY.md` with quantitative support,
   artifact/run IDs, scope and intended use, requested and authorized claim
   classes, target and achieved validation levels, a hash-bound readiness
   report, claim authorization and boundary—including important null or
   conflicting results.
7. Update artifact/run/figure/source records when an input, execution or
   deliverable is created, selected, superseded or archived. Readiness evidence
   that cites an artifact, run or decision must include the canonical record
   SHA-256; do not treat a recomputed digest as a substitute for required row
   content or lineage closure. Run evidence additionally binds its log SHA-256
   and the exact record digest of every input, output and validation artifact.
8. Add unresolvable experimental or reporting facts to `AUTHOR_QUERIES.md`.

When a known backend defect may affect existing results, follow the correction
procedure in [retrofit-and-archive.md](retrofit-and-archive.md).
Ask the domain workflow to establish the affected scope; preserve old bytes,
record the correction and parent lineage, and update only dependent claims and
delivery selections. Directory compliance cannot clear a numerical concern.
9. Mark affected declarations `currency_status=stale` when any bound input,
   analysis spec, gate policy, code manifest, environment snapshot, backend or
   dependency changes. Do not rewrite their historical `readiness_status`.

Do not rewrite append-only history. Mark replaced conclusions `superseded` and
link the decision/artifact that replaced them. Do not automatically translate a
legacy `confirmed` or `supported` label into a stronger current claim.
