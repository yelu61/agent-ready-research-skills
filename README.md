# Agent-Ready Research Skills

Reusable, self-contained scientific agent skills created and maintained by Lu
Ye. This public repository is the canonical source for publishable authored
skills; it does not vendor third-party, package-managed, plugin-managed, or
client-specific installations.

## Included skills

| Skill | Purpose | Status |
|---|---|---|
| [`manage-research-project`](skills/manage-research-project/) | Manage research structure, source/artifact/run provenance, scoped readiness, handoff, and archives without conflating execution with scientific validity | Core |
| [`bulk-rnaseq-upstream`](skills/bulk-rnaseq-upstream/) | Validate shared references and run paired-end FASTQ through HISAT2, featureCounts, and optional human-mouse read classification | Core |
| [`bulk-rnaseq-analysis`](skills/bulk-rnaseq-analysis/) | Route reproducible bulk RNA-seq work between the RNAseq-Templates and TCGA analysis backends | Core |
| [`critical-paper-reading`](skills/critical-paper-reading/) | Map scientific claims to evidence, calibrate causal strength, audit validity, and design actionable follow-up work | Core |

Each directory under `skills/` is independently installable. Runtime
instructions, scripts, references, and assets required by a skill must remain
inside that skill directory.

## Quick start

After installation, invoke a skill explicitly with its `$skill-name`, or make a
natural-language request that matches its description. Explicit invocation is
recommended when several installed skills could handle the same request.

```text
Use $manage-research-project to initialize this study as a
manuscript-ready research workspace without overwriting existing files.

Use $bulk-rnaseq-upstream to validate my paired-end FASTQ and shared reference
bundle, then prepare a reproducible HISAT2-to-featureCounts upstream run.

Use $bulk-rnaseq-analysis to review this count matrix, choose the appropriate
RNA-seq backend, and produce a reproducible downstream-analysis plan.

Use $critical-paper-reading to map this paper's major claims to evidence,
identify causal overreach, and propose decisive follow-up experiments.
```

Open a new Codex task or restart the agent client after first installation so
its skill index is refreshed.

## Which skill should I use?

| Goal | Skill | Example request |
|---|---|---|
| Start, retrofit, audit, checkpoint, hand off, or archive a research project | `manage-research-project` | “Audit this project for reproducibility and create the missing project-memory records.” |
| Process paired-end bulk RNA-seq FASTQ into gene-level counts with a shared immutable reference | `bulk-rnaseq-upstream` | “Validate this FASTQ set and reference bundle, then prepare the upstream run.” |
| Route a bulk RNA-seq request to local, GEO, or cancer-cohort analysis backends | `bulk-rnaseq-analysis` | “Analyze these raw counts and explain which backend and expression scale are appropriate.” |
| Critically assess one scientific paper beyond summarization | `critical-paper-reading` | “Build a claim–evidence map and distinguish association from causal support.” |

Skills may be combined sequentially. For example, use
`manage-research-project` to establish the workspace,
`bulk-rnaseq-upstream` to create an auditable count matrix from FASTQ,
`bulk-rnaseq-analysis` for downstream analysis, and finally
`critical-paper-reading` to evaluate literature supporting the interpretation.

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
ln -s \
  "$HOME/Skills/agent-ready-research-skills/skills/$skill_name" \
  "$HOME/.agents/skills/$skill_name"
```

Restart or open a new Codex task after first installation. Edits made through
the repository checkout are then immediately available to linked agent clients.

## Update a local checkout

Pull the repository; linked installations update immediately because they point
to the checkout rather than copied skill directories:

```bash
git -C "$HOME/Skills/agent-ready-research-skills" pull --ff-only
```

After an update that changes skill metadata, open a new task so the client
rebuilds its skill index.

## Validate

Run both repository validation and behavioral smoke tests:

```bash
python3 scripts/validate_skills.py
python3 -m unittest discover -s tests -v
```

The GitHub Actions workflow runs the same checks on pushes and pull requests.

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
