# Agent-Ready Research Skills

Reusable, self-contained scientific agent skills created and maintained by Lu
Ye. This public repository is the canonical source for publishable authored
skills; it does not vendor third-party, package-managed, plugin-managed, or
client-specific installations.

[中文使用指南](USAGE.zh-CN.md) · [Dependencies and validation](DEPENDENCIES.md) ·
[Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

## Included skills

| Skill | Purpose | Status |
|---|---|---|
| [`manage-research-project`](skills/manage-research-project/) | Plan projects and portfolio priorities, diagnose blockers, assess milestones, and maintain scoped records, workspaces, provenance and handoffs | Core |
| [`bulk-rnaseq-upstream`](skills/bulk-rnaseq-upstream/) | Validate shared references and run paired-end FASTQ through HISAT2, featureCounts, and optional human-mouse read classification | Core |
| [`bulk-rnaseq-analysis`](skills/bulk-rnaseq-analysis/) | Route reproducible bulk RNA-seq work between the RNAseq-Templates and TCGA analysis backends | Core |
| [`critical-paper-reading`](skills/critical-paper-reading/) | Map scientific claims to evidence, calibrate causal strength, audit validity, and design actionable follow-up work | Core |
| [`scientific-reasoning`](skills/scientific-reasoning/) | Frame biomedical questions, estimands, alternative explanations, falsification and validation plans | Core |
| [`scrna-analysis-core`](skills/scrna-analysis-core/) | Review single-cell workflows and inspect AnnData, count representations and sample-level design | Core |

Each directory under `skills/` is independently installable. Runtime
instructions, authored scripts, references, and assets remain inside that skill
directory. External software and data requirements are declared separately in
[DEPENDENCIES.md](DEPENDENCIES.md) and in each package's references. Installation
of a skill does not install analysis software or certify an analysis environment.

scLucid, named researcher perspectives and other skills are optional adapters.
The two reasoning/review skills complete their core work from supplied materials
without them. The bulk downstream skill can plan and audit without its execution
backends; executing an analysis still requires an explicitly resolved backend.

## Quick start

Project management is proportional to the work: use the four-file
[exploratory profile](skills/manage-research-project/references/exploratory-profile.md)
for a small pilot, a formal profile for sustained research, and an explicit
[project map](skills/manage-research-project/references/project-map.md) to retain
an established directory layout. No folder convention establishes scientific
validity. The optional [sample-relation check](skills/manage-research-project/references/multimodal-identity.md)
helps document partial multi-omics matching without inferring biological identity.

The same `manage-research-project` entry also supports project review, stage
planning, milestone acceptance and portfolio prioritization. These modules load
only for the relevant request; a record update does not run a strategy review
or full audit. Task completion, milestone acceptance and scientific readiness
remain separate. Existing record ownership is preserved; external task owners
use source-linked local views, not a second editable backlog.

The former `research-program-manager` instruction draft is incorporated into
this entry rather than distributed as a second skill. Its deployment sketches
do not establish working synchronization, scheduling or transaction adapters.

| Management mode | Requested outcome | On-demand module |
|---|---|---|
| `review` / `plan` / `accept` | Diagnose a delivery blocker, plan bounded work, or assess agreed milestone criteria | [Project decisions](skills/manage-research-project/references/project-decisions.md) |
| `portfolio` | Compare named projects within actual capacity and dependencies | [Portfolio review](skills/manage-research-project/references/portfolio-review.md) |
| `init` / `retrofit` | Establish records or adapt an existing workspace without disrupting paths | [Workspace setup](skills/manage-research-project/references/workspace-setup.md) |
| `checkpoint` | Update only changed task, state, decision or artifact records | [Checkpoint](skills/manage-research-project/references/checkpoint.md) |
| `audit` / `handoff` / `archive` | Check scoped integrity, preserve resumable state or freeze a declared delivery | [Audit and handoff](skills/manage-research-project/references/audit-and-handoff.md) |

These are agent workflow choices, not additional CLI flags. Use ordinary
language to specify the project, intended outcome and any material constraints.
Portfolio work needs named projects and accessible records; installing a skill
does not grant access to every project or automatically discover their state.

After installation, invoke a skill explicitly with its `$skill-name`, or make a
natural-language request that matches its description. Explicit invocation is
recommended when several installed skills could handle the same request.

```text
Use $manage-research-project to initialize this study as a
manuscript-ready research workspace without overwriting existing files.

Use $manage-research-project to diagnose this project's main delivery blocker
and propose the next milestone with evidence-based acceptance criteria.

Use $manage-research-project to prioritize these three projects within this
week's confirmed capacity, using their supplied current summaries.

Use $bulk-rnaseq-upstream to validate my paired-end FASTQ and shared reference
bundle, then prepare a reproducible HISAT2-to-featureCounts upstream run.

Use $bulk-rnaseq-analysis to review this count matrix, choose the appropriate
RNA-seq backend, and produce a reproducible downstream-analysis plan.

Use $critical-paper-reading to map this paper's major claims to evidence,
identify causal overreach, and propose decisive follow-up experiments.

Use $scientific-reasoning to define the estimand and competing explanations
for this treatment-response hypothesis, then propose a falsification plan.

Use $scrna-analysis-core to inspect this AnnData object and determine whether
the requested donor-level contrast is estimable before choosing an analysis.
```

Codex detects skill changes automatically. If a new or updated skill does not
appear, restart Codex. See the [official skill documentation](https://learn.chatgpt.com/docs/build-skills)
for discovery and invocation behavior.

## Which skill should I use?

| Goal | Skill | Example request |
|---|---|---|
| Start, retrofit, audit, checkpoint, hand off, or archive a research project | `manage-research-project` | “Audit this project for reproducibility and create the missing project-memory records.” |
| Review project progress, plan a stage, accept a milestone or compare portfolio priorities | `manage-research-project` | “Identify the critical delivery gap and give the smallest defensible next step.” |
| Process paired-end bulk RNA-seq FASTQ into gene-level counts with a shared immutable reference | `bulk-rnaseq-upstream` | “Validate this FASTQ set and reference bundle, then prepare the upstream run.” |
| Route a bulk RNA-seq request to local, GEO, or cancer-cohort analysis backends | `bulk-rnaseq-analysis` | “Analyze these raw counts and explain which backend and expression scale are appropriate.” |
| Critically assess one scientific paper beyond summarization | `critical-paper-reading` | “Build a claim–evidence map and distinguish association from causal support.” |
| Develop or audit a research question and its evidence requirements | `scientific-reasoning` | “Separate local mechanism, population prediction and treatment-selection claims.” |
| Plan or review a single-cell RNA-seq workflow and inspect its data contract | `scrna-analysis-core` | “Check counts, biological replication, batch confounding and this contrast.” |

Skills may be combined sequentially. For example, use
`manage-research-project` to establish the workspace,
`bulk-rnaseq-upstream` to create an auditable count matrix from FASTQ,
`bulk-rnaseq-analysis` for downstream analysis, and finally
`critical-paper-reading` to evaluate literature supporting the interpretation.

Combine only the capabilities the actual request needs. Installation does not
make every skill mandatory: isolated syntax, format conversion, plot styling,
ordinary paper summaries and unchanged records should not expand into full
workflow reviews. Reuse adequate current evidence; refresh it when the object,
design, source or intended use changes. Explicitly naming a skill also does
not authorize unrequested analysis, project reorganization or external writes.

Project management records and assesses evidence, while domain workflows carry
out analysis and supply its scientific review. A completed task, accepted
milestone, successful command and scientifically authorized claim are distinct.

## Install from GitHub

Ask Codex to install one skill from its GitHub directory:

```text
Install the skill from
https://github.com/yelu61/agent-ready-research-skills/tree/main/skills/<skill-name>
```

For local development or immediate access to repository edits, clone the
collection and link the desired skill into the shared Agent Skills discovery
directory:

```bash
git clone https://github.com/yelu61/agent-ready-research-skills.git \
  "$HOME/Skills/agent-ready-research-skills"

skill_name="manage-research-project"
mkdir -p "$HOME/.agents/skills"
ln -s \
  "$HOME/Skills/agent-ready-research-skills/skills/$skill_name" \
  "$HOME/.agents/skills/$skill_name"
```

Do not overwrite an existing installation or link without checking its owner.
Linked files reflect checkout edits; client discovery refresh follows the
official behavior described above.

## Update a local checkout

Inspect local changes before pulling; preserve work in progress rather than
discarding it to update the skills. Linked installations point to the checkout:

```bash
git -C "$HOME/Skills/agent-ready-research-skills" status --short
git -C "$HOME/Skills/agent-ready-research-skills" pull --ff-only
```

If a changed skill is not reflected in the client, restart Codex. Updating the
checkout does not install external analysis dependencies or start any workflow.

## Validate

Run package validation and repository regression tests:

```bash
python3 scripts/validate_skills.py
python3 -m unittest discover -s tests -v
```

The GitHub Actions workflow runs these checks on pushes and pull requests and
has a separate numerical dependency job. See [DEPENDENCIES.md](DEPENDENCIES.md)
for the distinction between wrapper regressions, numerical fixtures, and full
bioinformatics execution. Prompt cases are evaluation inputs, not proof of
model-level success unless their actual outputs have been reviewed.

Management planning/review requires a capable agent and current project
evidence. Local helpers perform specific filesystem and contract operations;
they do not implement external task-system synchronization, durable event
processing, transaction recovery or a scheduler. See [DEPENDENCIES.md](DEPENDENCIES.md)
for these execution and validation boundaries.

## License and resource provenance

Original code, instructions, schemas and synthetic fixtures are distributed
under the [MIT License](LICENSE), also included in each standalone package.
[SOURCES.md](SOURCES.md) identifies methodological sources and maintenance rules.
Linked publications, external software, databases and researcher identities
retain their own rights; this license does not relicense them or imply their
authors endorse these skills. Publisher full text and personal perspective
skills are not bundled.

This repository is the sole maintenance source for `scientific-reasoning` and
`scrna-analysis-core` after migration. Local compatibility links may remain in
the private collection, but edits and releases belong here; do not maintain a
second private copy.

## Repository policy

- Include only user-authored scientific skills that are safe to redistribute.
- Keep third-party shared skills under `~/.agents/skills/` and client-specific
  skills in their client discovery roots; do not copy them into this repo.
- Keep local-only authored skills in a separate Projects checkout until their
  source material, machine paths, and redistribution rights pass review.
- Keep each skill self-contained.
- Put user-facing repository documentation and release history at repository
  root, not inside an individual skill.
- Do not commit secrets, private datasets, project-specific results, or
  machine-specific absolute paths.
- Validate before committing.
- Use skill-scoped release tags, for example
  `manage-research-project-v1.0.0`.
