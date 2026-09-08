# Dependencies and validation boundary

Each skill bundles its own authored instructions, helper scripts, schemas,
references and MIT license. External software, scientific datasets and other
skills are not bundled. No install or network access is required for reviewing
materials already supplied to the reasoning and paper-reading workflows.

| Package | Core runtime | Additional requirements for execution | Optional adapters and fallback |
|---|---|---|---|
| manage-research-project | Python 3.11+, standard library | Safe writes require POSIX file operations; registry appends also require `fcntl` | Domain review skills can supply evidence; absent reviewers leave scientific readiness `not_assessed` while structure/provenance work completes |
| bulk-rnaseq-upstream | Bash, Python 3.9+, Unix utilities for local validation | HISAT2, SAMtools, featureCounts; reference building additionally needs UCSC tools; selected split/trimming/QC branches need their named tools | Downstream skills are optional. Reference and library evidence still govern execution; see package runtime reference |
| bulk-rnaseq-analysis | Python 3.11+, standard library for routing/preflight | An explicitly identified RNAseq-Templates or TCGA backend checkout and that backend's R environment; executable readiness requires revision-bound capability evidence | Project manager and other skills are optional. With no backend, deliver plan/audit with execution readiness false |
| critical-paper-reading | A capable agent and supplied source material | Network/source tools only when fetching or verifying current external evidence | Other skills are optional; unavailable full text or lookup is an explicit evidence gap |
| scientific-reasoning | A capable agent; Python 3.11+ only for optional handoff validator | Supplied question, evidence and study context | scLucid, single-cell reviewer and named perspectives are optional; use native reasoning and generic lenses |
| scrna-analysis-core | A capable agent; Python 3.11+ for helper scripts | Inspecting `.h5ad` needs AnnData, NumPy, SciPy and pandas (plus their HDF5 dependencies) | scLucid and other skills are optional. Without numerical dependencies, complete a document-based review and mark object inspection unperformed |

See each skill's source/runtime reference for exact commands, supported data
contracts and limitations. Dependency absence must never be reported as a
successful execution. This repository does not ship scLucid or persona skill
sources and has no runtime import from them.

## Repository checks

The standard-library test run checks contracts, routing, filesystem safety and
synthetic shell workflows. Numerical single-cell cases skip explicitly if the
AnnData stack is unavailable. To run those cases, use a separate environment:

```bash
python3 -m venv .venv-validation
.venv-validation/bin/python -m pip install -r tests/requirements-numerical.txt
.venv-validation/bin/python -m unittest discover -s tests -v
```

The numerical CI job checks imports before testing so a broken dependency stack
cannot silently turn all numerical cases into skips. Pins identify a regression
environment, not recommended analysis defaults or a certified production stack.
No full FASTQ-to-count run, real R backend analysis, or biological benchmark is
implied by passing these tests. Readiness v1 is the supported project-manager
interface; its experimental v2 library is not a supported command-line gate.
