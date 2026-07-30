# Agent-Ready Research Skills

Reusable, self-contained scientific agent skills created and maintained by Lu
Ye. This public repository is the canonical source for publishable authored
skills; it does not vendor third-party, package-managed, plugin-managed, or
client-specific installations.

## Included skills

| Skill | Purpose | Status |
|---|---|---|
| [`manage-agent-ready-research-project`](skills/manage-agent-ready-research-project/) | Initialize, retrofit, checkpoint, audit, hand off, and archive an evidence-traceable research workspace | Core |
| [`bulk-rnaseq-analysis`](skills/bulk-rnaseq-analysis/) | Route reproducible bulk RNA-seq work between the RNAseq-Templates and TCGA analysis backends | Core |
| [`critical-paper-reading`](skills/critical-paper-reading/) | Map scientific claims to evidence, calibrate causal strength, audit validity, and design actionable follow-up work | Core |

Each directory under `skills/` is independently installable. Runtime
instructions, scripts, references, and assets required by a skill must remain
inside that skill directory.

## Install from GitHub

After the repository has been published, ask Codex to install the skill from:

```text
https://github.com/yelu61/agent-ready-research-skills/tree/main/skills/<skill-name>
```

For local development, clone the repository and link the skill into the shared
Agent Skills discovery directory:

```bash
skill_name="manage-agent-ready-research-project"
ln -s \
  "$HOME/Projects/agent-ready-research-skills/skills/$skill_name" \
  "$HOME/.agents/skills/$skill_name"
```

Restart or open a new Codex task after first installation. Edits made through
the repository checkout are then immediately available to linked agent clients.

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
  `manage-agent-ready-research-project-v1.0.0`.
