# Repository instructions

This repository is the canonical source for a collection of independently
installable Agent Skills.

## Editing rules

- Treat every direct child of `skills/` as a self-contained distributable unit.
- Do not make a skill depend on files outside its own directory.
- Keep repository-facing documentation at repository root.
- Preserve existing skill behavior unless the task explicitly changes it.
- Do not add private research data, manuscript drafts, credentials, tokens, or
  machine-specific paths.
- Use `apply_patch` for manual source edits.

## Required checks

After changing any skill, run:

```bash
python3 scripts/validate_skills.py
python3 -m unittest discover -s tests -v
```

When behavior changes, update the relevant tests and the root `CHANGELOG.md`.

