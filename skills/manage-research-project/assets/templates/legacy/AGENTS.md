# Project working agreements

Read `docs/PROJECT_STATUS.md` and `docs/SESSION_HANDOFF.md` first. Load the
brief, data dictionary, plan and relevant decisions only when the task needs
them. Use `PROJECT_MAP.json` when present to resolve their actual paths.

Preserve the existing layout and authored source. Do not create parallel source
roots or move files just to match a template. A map documents ownership; it
does not relocate files or create backend capabilities.

Protected raw roots: {{RAW_ROOTS}}. Treat original source bytes as read-only;
the conventional name is data/raw, but existing projects may use other names.
Keep run outputs and reviewed deliverables separate from source data and code.
Source roots: {{SOURCE_ROOTS}}. Native runs: {{RUN_ROOT}}.
Reviewed results: {{RESULTS_ROOT}}.

Preserve unrelated modifications and historical results. Do not put credentials,
direct participant identifiers or re-identification keys into project memory.
Unknown source, sample or run metadata remain unknown.

After substantive work, update only changed facts: current status and next
action, new decisions, input/parameter changes and current evidence-linked
findings. Preserve earlier decisions and superseded results.

Keep planning, execution, numerical checks, scientific conclusions and archives
distinct. Structure checks and hashes cannot certify scientific validity.
Domain review determines experimental units, model validity and claim scope.
Use formal readiness records only when the intended use requires them.

Formal manager registries/specifications retain `provenance/`, `analysis/specs/`
and `analysis/readiness/`. Record actual input/output paths in their manifests.
Verify each domain tool supports requested mapped paths before executing it.
