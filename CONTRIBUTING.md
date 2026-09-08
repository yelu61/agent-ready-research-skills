# Contributing

## Add or revise a skill

1. Confirm the skill is user-authored, scientific, and safe to redistribute;
   do not vendor installed third-party skills.
2. Keep the skill in `skills/<skill-name>/`.
3. Use lowercase hyphen-case and make the folder name match the `name` in
   `SKILL.md`.
4. Keep `SKILL.md` concise and route detailed material to `references/`.
5. Keep authored scripts, references, schemas and assets inside the skill
   directory. Declare external runtimes, packages and data requirements in
   package references and the root dependency inventory; do not vendor them
   merely to claim self-containment. Optional adapters must have a documented
   fallback that completes the core task without sibling skills.
6. Do not add repository documentation such as `README.md` or `CHANGELOG.md`
   inside a skill.
7. Remove machine-specific paths, secrets, private research material, and raw
   publisher-derived full text before staging.
8. Add or update behavioral tests when scripts or safety rules change. Bundle
   the MIT license, identify original versus external resources, and record
   sources actually checked. A new date alone is not a freshness review.
9. Run:

   ```bash
   python3 scripts/validate_skills.py
   python3 -m unittest discover -s tests -v
   ```

## Release

Verify each changed package from an isolated copy with no sibling skills.
Run numerical regressions in a working dependency environment; report skips
and tool stubs rather than presenting them as biological validation. Do not
switch active installations until these checks pass.

Update the root `CHANGELOG.md`, commit the validated state, and create a
skill-scoped semantic-version tag:

```bash
git tag -a manage-research-project-v1.0.0 \
  -m "manage-research-project v1.0.0"
```
