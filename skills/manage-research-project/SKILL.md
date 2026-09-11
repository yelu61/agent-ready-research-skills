---
name: manage-research-project
description: Plan research priorities, diagnose project blockers, assess milestones, and maintain workspaces or changed records. Use for 项目规划、卡点诊断、里程碑验收、跨项目优先级、项目初始化、状态更新、来源追踪、交接 and 归档. Skip isolated coding, plotting, factual lookup and unchanged records; select only the relevant management mode.
---

# Manage Research Projects

Connect goals, evidence, decisions, tasks and deliverables while preserving
existing work. Manage one project or a supplied portfolio through the same
entry point; load only the module needed for the current request.

A management request does not automatically start an analysis, literature
search, project audit, external write or recurring service. A focused code,
display or explanatory task remains focused even when this skill is named.

## Select the requested mode

| Mode | Request | Read on demand | Outcome |
| --- | --- | --- | --- |
| `review` | Diagnose a project-level blocker or review progress | [Project decisions](references/project-decisions.md) | Evidence-backed diagnosis and smallest useful next action |
| `plan` | Plan a stage or prepare an execution assignment | [Project decisions](references/project-decisions.md) | Bounded tasks, dependencies, deliverables and acceptance criteria |
| `accept` | Decide whether a milestone can close | [Project decisions](references/project-decisions.md) | Criterion-by-criterion assessment, with unresolved evidence visible |
| `portfolio` | Prioritize across named projects | [Portfolio review](references/portfolio-review.md) | Feasible priority recommendation and resource tradeoffs |
| `init` / `retrofit` | Initialize or organize a workspace | [Workspace setup](references/workspace-setup.md) | Proportionate structure and preserved paths |
| `checkpoint` | State, decisions, artifact records or next action changed | [Checkpoint](references/checkpoint.md) | Only triggered records updated and checked |
| `audit` | Inspect structure, provenance or record integrity | [Audit and handoff](references/audit-and-handoff.md) | Scoped audit findings and supported repairs |
| `handoff` / `archive` | Prepare resumption or freeze a declared delivery | [Audit and handoff](references/audit-and-handoff.md) | Resumable handoff or verified snapshot |

Choose from the requested outcome. A populated directory alone does not imply
retrofit; a project-level blocker does not imply a code refactor. An ordinary
debugging question does not require project management. Combine modes only
when the request needs distinct outputs: for example, plan a stage and then
record the accepted plan. Updating T1 to T2 does not require a new project review.

A restart handoff preserves current state; an execution assignment specifies
work to be done. Do not turn either into an archive or run it as a new task
unless the user requested that action. Mode names describe instructions, not
new CLI flags or implemented service endpoints.

## Establish scope from current evidence

1. Resolve the named project, actual paths or supplied portfolio. Read relevant
   project instructions, current goal, status and next milestone first.
2. Follow current record ownership and task/decision IDs. Use chat history only
   as dated context; newer text is not automatically more authoritative.
3. Inspect the inputs that can change the requested decision. Add methods,
   results, manifests or full texts only when a concrete uncertainty needs them.
4. State material access gaps and source age. Unreadable is not absent, a
   recorded claim is not an independently checked result, and an old suggestion
   is not a current decision.
5. Resolve routine choices from evidence and existing authorization. Ask only
   when an unresolved choice changes correctness, scope, authorization or an
   irreversible outcome; continue independent work meanwhile.

For a review, report a recommendation without silently changing goals, owners,
deadlines or project lifecycle. When the user has authorized a bounded local
update, complete it and verify it; no separate approval ceremony is required.

## One record owner per responsibility

Use [the document contract](references/document-contract.md) when establishing
ownership or changing task, state, decision, result or handoff records.
Preserve the project's existing authority. Local `TODO.md` is the default for
a local task list; a confirmed external task owner is represented locally by a
source-linked pointer or derived snapshot, not a second editable master.

An ordinary checkpoint does not migrate ownership. An unavailable authoritative
source leaves its current state unknown; do not promote a cache or stale local
copy to master. Keep project facts in project records, not in this skill.

Record observed facts, user reports, inferences, proposals and approved
decisions distinctly. Preserve stable IDs and superseded history. Before an
authorized write, compare the current value/version, apply only supported
changes, then reread. Repeated input should reuse existing tasks or decisions;
read-before-write alone is not an atomic concurrency guarantee.

Task status, milestone acceptance, execution, scientific readiness and claim
authorization are separate. A user-reported completion can be recorded as such;
it does not manufacture missing deliverables, acceptance evidence or scientific
approval. A negative result can satisfy a well-designed task's acceptance.

## Preserve scientific and execution boundaries

For analysis/result curation or readiness-dependent work, read
[Scientific integrity](references/scientific-integrity.md) and the relevant
contracts below. A structure audit, successful command or completed task never
proves biological validity, causality or clinical utility.

- [Readiness contract](references/readiness-contract.md): when reading, creating,
  validating or staling a domain readiness declaration. Supported interface:
  `validate_readiness.py`, `research-readiness/v1`; v2 remains experimental.
- [Analysis specification](references/analysis-spec-contract.md): when binding
  an intended analysis to its inputs, parameters and evidence requirements.
- [Provenance](references/provenance-contract.md): when inputs, runs,
  deliverables or source baselines change. Use the existing registration helpers.
- [Project map](references/project-map.md) and [layout](references/layout-contract.md):
  when paths or workspaces are being established, mapped or structurally audited.
- [Multimodal identity](references/multimodal-identity.md): when donor, specimen,
  section, library or cell relationships affect the requested task.
- [Human data and access](references/human-data-and-access.md): when handling
  human, clinical, restricted or otherwise sensitive material.

Keep domain analysis and scientific reasoning in available specialist tools
when their distinct work is needed. Do not load every specialist, rerun an
adequate review or summon named researcher perspectives by default. Missing
optional skills must not block project planning, organization or handoff;
explain unresolved domain evidence instead of inventing it.

## Complete and verify the selected work

For a records-only checkpoint, verify changed facts, affected links and
status/handoff consistency; no full structural audit or new governance scaffold
is required. Reading, explaining or styling with no changed facts needs no
memory rewrite.

For a review, plan, portfolio or acceptance assessment, verify that conclusions
and proposed actions follow the inspected evidence and resource constraints.
Do not run a structural audit solely to generate a management recommendation.
Only claim a record was updated after a successful write and reread.

Initialization, retrofit, a requested audit and archives use the applicable
helpers in [Audit and handoff](references/audit-and-handoff.md). Source, spec,
code, environment or backend changes and readiness-dependent delivery still
require the relevant integrity, freshness and domain checks.

Report the requested result first, then the evidence, changes, checks, limits
and next action that matter to it. A short answer may be the complete output;
do not generate every template or a restart prompt for every mode.

## Runtime and evaluation

[Runtime and sources](references/runtime-and-sources.md) covers standalone
installation and helper limits. Resolve bundled script paths from this skill's
directory, not the project's working directory. Planning needs neither an analysis backend
nor a connected project service. External schemas, write adapters, durable
event deduplication, transaction recovery and scheduling are not implemented
by these instructions.

[Evaluation requests](test-prompts.json) cover management, lightweight-task
and scientific boundaries. Their expected outcomes are review criteria, not
claims of executed tests or permanent reliability.
