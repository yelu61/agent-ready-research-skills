# Project document contract

## Source-of-truth order

When sources disagree, do not silently choose one. Reconcile in this order:

1. immutable raw data or source-system export plus verified metadata;
2. current generated result with its exact generating code, parameters and
   successful execution evidence;
3. frozen source-data/manifests and current analysis documentation;
4. historical notebooks, reports and archived files;
5. conversation memory or an unsupported narrative claim.

Record the conflict and resolution in `DECISION_LOG.md`.

## Evidence states

| State | Meaning | Permitted wording |
|---|---|---|
| `confirmed` | Directly verified from design, data or formal analysis | demonstrates; significant; confirmed |
| `supported` | Multiple consistent analyses, but not direct causal proof | supports; is consistent with |
| `exploratory` | Hypothesis-generating threshold, selected panel or weak design | suggests; candidate; exploratory |
| `superseded` | Replaced by a later decision or corrected analysis | do not use as current conclusion |
| `blocked` | Required information or execution is missing | unresolved; cannot yet conclude |

Each quantitative conclusion in `RESULTS_SUMMARY.md` should name its evidence
state and source file.

## Document ownership

| Document | Owns | Update trigger |
|---|---|---|
| `README.md` | Human entry point and navigation | Layout or canonical entry points change |
| `AGENTS.md` | Stable cross-agent behavior | Rare policy change |
| `CLAUDE.md` | Compact Claude operational entry | Tool/runtime instructions change |
| `PROJECT_BRIEF.md` | Stable question, design, constraints | Scientific scope/design confirmed or changed |
| `PROJECT_STATUS.md` | Current stage, blockers, next task | Meaningful task changes state |
| `SESSION_HANDOFF.md` | Exact resumable state | End of meaningful session |
| `DECISION_LOG.md` | Append-only decisions and supersessions | Analysis or interpretation decision |
| `DATA_DICTIONARY.md` | Files, IDs, fields, transformations | New/changed data or semantics |
| `ANALYSIS_PLAN.md` | Intended analysis and validation | Planned methods change |
| `PIPELINE.md` | Actual runnable flow and execution state | Entry point/dependency/output changes |
| `RESULTS_SUMMARY.md` | Current evidence-backed findings | Verified result or interpretation changes |
| `REPRODUCIBILITY.md` | Environment, commands, versions, seeds | Runtime or reproduction information changes |
| `TODO.md` | Actionable backlog | Task opened, closed or reprioritized |
| `AUTHOR_QUERIES.md` | Facts no analysis can determine | Unresolved experiment/reporting fact found |
| figure/source manifests | Deliverable identity and provenance | Artifact created, selected, replaced or archived |

## Task backlog format (`TODO.md`)

`TODO.md` is the canonical task list and the sync contract with external
project-management tools (e.g. Notion Tasks). One checkbox line per task:

- Status markers: `- [ ]` Backlog · `- [>]` In progress · `- [~]` Paused ·
  `- [x]` Done · `- [-]` Canceled.
- Optional suffixes: `#T01` stable task ID (assign once, never reuse, keep
  across renames) · `#high` / `#low` priority (omit = unset) · `@YYYY-MM-DD`
  due date.
- Section headers group tasks; a header carrying `P0`/`P1`/`P2` implies
  High/Medium/Low priority for every task in that group.
- Table-format backlogs may use the status vocabulary `NEXT`, `QUEUED`,
  `OPTIONAL`, `BLOCKED`, `DONE`, mapping to In progress, Backlog,
  Backlog + Low priority, Paused, Done.

Update a task's marker in place when its state changes; do not move completed
tasks into prose history. Bump `Last updated` on every edit.

## Update discipline

- Keep stable facts separate from temporary state.
- Keep intended methods separate from actually executed methods.
- Use ISO dates.
- Link decisions using stable IDs such as `D-20260730-01`.
- Never delete an old decision; append a superseding entry.
- Store detailed raw provenance in manifests or dictionaries, not agent
  instruction files.
- Keep one canonical document per responsibility. Archive duplicates after
  confirming the canonical version.
