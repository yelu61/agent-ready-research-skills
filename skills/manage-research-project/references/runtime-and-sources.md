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

No sibling skill, persona, scLucid instance or external service is required.
Scientific reviewers are optional producers of domain evidence. Without one,
finish project organization, source integrity and handoff with scientific
readiness `not_assessed`. Installed analysis tools remain governed by their own
input, software and data requirements.

## Methodological provenance

Last checked: 2026-09-08. The schemas, templates and scripts here are original
project conventions, not verbatim implementations of an external standard.

| Source | Principle used | Limit |
|---|---|---|
| [FAIR principles](https://doi.org/10.1038/sdata.2016.18) | Machine-readable identity, provenance and reuse context | A hash or completed metadata template alone does not make data FAIR or scientifically valid. |
| [Workflow Run Crate official profile](https://www.researchobject.org/workflow-run-crate/profiles/workflow_run_crate/) | Distinguish workflow identity, execution and associated inputs/outputs | This skill currently uses its own TSV/JSON contracts; RO-Crate conformance/export is not implemented. |

Recheck affected references when changing provenance semantics. Do not mark a
review complete merely by updating its date. All external articles and software
retain their own licenses; no publisher full text or third-party runtime code is
bundled in this package.
