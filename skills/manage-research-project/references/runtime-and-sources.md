# Runtime, independent installation and sources

Python 3.11+ and the standard library are sufficient for supported helpers.
Execution has been checked on macOS; Linux is the configured CI target.
Safe scaffold application and registry appends require POSIX directory/file
operations. Native Windows write support is not claimed; use a supported
Linux/WSL environment for those operations. Read-only inspection remains usable
where its Python/file dependencies are available.

`register_run.py --apply` needs fcntl locking, O_NOFOLLOW and O_DIRECTORY; it
reports unsupported runtimes before modifying records. A successful structure
audit does not establish software reproduction or scientific validity.

The exploratory memory audit also uses POSIX no-follow reads and refuses
unsupported platforms, aliases and oversized memory files. Project mapping and
the CSV/TSV sample-relation validator require no third-party Python packages.
No pipeline or domain backend is installed by these helpers.

No sibling skill, persona, scLucid instance or external service is required.
Scientific reviewers are optional producers of domain evidence. Without one,
finish project organization, source integrity and handoff with scientific
readiness `not_assessed`. Installed analysis tools remain governed by their own
input, software and data requirements.

## Management modules and implementation limits

Project review, planning, milestone acceptance and portfolio prioritization
are instruction workflows over supplied or actually inspected project records.
They are self-contained and require no external project application. A real
remote read/write still requires the host's available tools, actual schema and
authorization; no vendor is assumed to own the user's tasks.

This package does not implement external write adapters, durable event
deduplication, transactional recovery, background monitoring or scheduling.
Version checks and rereads should be used where applicable but are not an
atomic compare-and-swap guarantee. Do not execute conceptual function names or
report an integration as deployed merely because instructions describe it.

On 2026-09-11, the locally authored `research-program-manager` v0.1 draft's
decision/portfolio protocols and logical state rules were integrated here.
Its reusable decision material is in [Project decisions](project-decisions.md),
[Portfolio review](portfolio-review.md) and [Document contract](document-contract.md).
The former deployment roadmap and project-specific setup examples are not
distributed as runnable capability. Existing helper code and CLI interfaces
remain unchanged. Synthetic evaluation requests are not evidence of a live
external integration or long-term management performance.

## Methodological provenance

Last checked: 2026-09-08. The schemas, templates and scripts here are original
project conventions, not verbatim implementations of an external standard.

The exploratory profile, project-map schema and multimodal identity examples
are original project-management resources. Examples contain synthetic IDs.
The identity validator checks supplied records for consistency; it neither
authenticates specimen provenance nor infers physical same-cell pairing.

| Source | Principle used | Limit |
|---|---|---|
| [FAIR principles](https://doi.org/10.1038/sdata.2016.18) | Machine-readable identity, provenance and reuse context | A hash or completed metadata template alone does not make data FAIR or scientifically valid. |
| [Workflow Run Crate official profile](https://www.researchobject.org/workflow-run-crate/profiles/workflow_run_crate/) | Distinguish workflow identity, execution and associated inputs/outputs | This skill currently uses its own TSV/JSON contracts; RO-Crate conformance/export is not implemented. |

Recheck affected references when changing provenance semantics. Do not mark a
review complete merely by updating its date. All external articles and software
retain their own licenses; no publisher full text or third-party runtime code is
bundled in this package.
