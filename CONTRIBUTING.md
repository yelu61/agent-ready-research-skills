# Contributing

## Add or revise a skill

1. Confirm the skill is user-authored, scientific, and safe to redistribute;
   do not vendor installed third-party skills.
2. Keep the skill in `skills/<skill-name>/`.
3. Use lowercase hyphen-case and make the folder name match the `name` in
   `SKILL.md`.
4. Keep `SKILL.md` concise and route detailed material to `references/`.
   Put the actual task and likely exclusions early in the description. A
   package name, file type or scientific topic alone should not attract an
   unrelated workflow. Keep normal automatic discovery unless an explicit-only
   policy is deliberately requested; naming a skill does not expand task scope.
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
   Prompt examples are authored evaluation cases until actual model outputs
   have been inspected; distinguish them from executable regression tests.
9. Run:

   ```bash
   python3 scripts/validate_skills.py
   python3 -m unittest discover -s tests -v
   ```

## Keep documentation and ownership consistent

Update the root README, Chinese usage guide, dependency/source ledgers and
CHANGELOG when a change affects discoverability, supported workflows or
execution boundaries. Keep detailed runtime instructions inside the owning
package so it remains independently installable.

When combining skills, preserve existing helper interfaces and current project
record ownership. Reconcile task status, milestone acceptance and scientific
state instead of translating labels across unrelated objects. Move conditional
instructions into reachable references and test representative small tasks as
well as the newly integrated modes. Retain source provenance and a recoverable
copy of retired material without publishing private examples or local backups.

## Validate and publish

Verify each changed package from an isolated copy with no sibling skills.
Run relevant numerical regressions in a working dependency environment; report
versions, skips and tool stubs rather than presenting them as biological
validation. When changing instructions substantially, compare representative
old/candidate outputs without giving the test agent expected answers. Record
unverified behavior; an entrypoint size reduction is not measured speedup.

Before an authorized commit/push, inspect the exact diff and new files, verify
that the target branch/remote are intended, and check remote divergence. Stage
the reviewed source and supporting tests/docs, not runtime caches, evaluation
workspaces or private project records. Preserve unrelated work and avoid force
pushing. Verify the remote commit after pushing; report CI as pending, passed
or failed based on its actual status.

A normal repository update does not require a new version tag. When explicitly
cutting a versioned skill release, update `CHANGELOG.md` and create the chosen
skill-scoped semantic-version tag, for example:

```bash
git tag -a manage-research-project-v1.0.0 \
  -m "manage-research-project v1.0.0"
```
