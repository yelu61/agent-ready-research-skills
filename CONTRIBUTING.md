# Contributing

## Add or revise a skill

1. Keep the skill in `skills/<skill-name>/`.
2. Use lowercase hyphen-case and make the folder name match the `name` in
   `SKILL.md`.
3. Keep `SKILL.md` concise and route detailed material to `references/`.
4. Keep every runtime dependency, script, reference, and asset inside the skill
   directory.
5. Do not add repository documentation such as `README.md` or `CHANGELOG.md`
   inside a skill.
6. Add or update behavioral tests when scripts or safety rules change.
7. Run:

   ```bash
   python3 scripts/validate_skills.py
   python3 -m unittest discover -s tests -v
   ```

## Release

Update the root `CHANGELOG.md`, commit the validated state, and create a
skill-scoped semantic-version tag:

```bash
git tag -a manage-agent-ready-research-project-v1.0.0 \
  -m "manage-agent-ready-research-project v1.0.0"
```

