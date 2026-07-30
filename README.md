# Agent-Ready Research Skills

Reusable, self-contained agent skills for organizing reproducible scientific
research projects.

## Included skills

| Skill | Purpose | Status |
|---|---|---|
| [`manage-agent-ready-research-project`](skills/manage-agent-ready-research-project/) | Initialize, retrofit, checkpoint, audit, hand off, and archive an evidence-traceable research workspace | Core |

Each directory under `skills/` is independently installable. Runtime
instructions, scripts, references, and assets required by a skill must remain
inside that skill directory.

## Install from GitHub

After the repository has been published, ask Codex to install the skill from:

```text
https://github.com/OWNER/agent-ready-research-skills/tree/main/skills/manage-agent-ready-research-project
```

For local development, clone the repository and link the skill into the shared
Agent Skills discovery directory:

```bash
ln -s \
  "$HOME/Projects/agent-ready-research-skills/skills/manage-agent-ready-research-project" \
  "$HOME/.agents/skills/manage-agent-ready-research-project"
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

- Keep each skill self-contained.
- Put user-facing repository documentation and release history at repository
  root, not inside an individual skill.
- Do not commit secrets, private datasets, project-specific results, or
  machine-specific absolute paths.
- Validate before committing.
- Use skill-scoped release tags, for example
  `manage-agent-ready-research-project-v1.0.0`.

