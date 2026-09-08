# External Benchmark and Maintenance Map

Last source verification: 2026-09-07. Rule revision: 2026-09-08.

The primary external benchmark is the living
[Single-cell best practices](https://www.sc-best-practices.org/preamble.html)
book. It is used as a benchmark and routing map, not copied as a fixed recipe.
Its own preamble emphasizes externally benchmarked methods where available,
workflow flexibility, and continuing updates.

## Adopted Principles

| Topic | Skill behavior | Source |
| --- | --- | --- |
| QC | joint, sample-aware, lenient robust filtering; batch-specific doublet review | [Quality control](https://www.sc-best-practices.org/preprocessing_visualization/quality_control.html) |
| Normalization | representation must match downstream consumer | [Normalization](https://www.sc-best-practices.org/preprocessing_visualization/normalization.html) |
| Feature selection | avoid treating arbitrary HVG defaults as universal | [Feature selection](https://www.sc-best-practices.org/preprocessing_visualization/feature_selection.html) |
| Clustering | Leiden on a KNN graph; use subclustering for finer structure | [Clustering](https://www.sc-best-practices.org/cellular_structure/clustering.html) |
| Annotation | combine manual evidence and reference-based predictions; audit reference fit | [Annotation](https://www.sc-best-practices.org/cellular_structure/annotation.html) |
| Integration | diagnose need first; evaluate batch removal and biological conservation | [Data integration](https://www.sc-best-practices.org/cellular_structure/integration.html) |
| Differential expression | sample-level pseudobulk is the default for replicated condition effects | [Differential expression](https://www.sc-best-practices.org/conditions/differential_gene_expression.html) |
| Composition | distinguish labeled composition from continuous neighborhood abundance | [Compositional analysis](https://www.sc-best-practices.org/conditions/compositional.html) |
| Pathways | separate enrichment testing from activity scoring; honor complex design | [Gene-set analysis](https://www.sc-best-practices.org/conditions/gsea_pathway.html) |
| Trajectory | select method from biological topology and root knowledge | [Pseudotime](https://www.sc-best-practices.org/trajectories/pseudotemporal.html) |
| Velocity | verify kinetic and phase-portrait assumptions | [RNA velocity](https://www.sc-best-practices.org/trajectories/rna_velocity.html) |
| Communication | treat transcript-based interactions as hypotheses | [Cell-cell communication](https://www.sc-best-practices.org/mechanisms/cell_cell_communication.html) |

## Primary and Official Checks

| Decision | Source checked | Scope/limit |
| --- | --- | --- |
| Sample-level condition inference | [Squair et al., 2021](https://www.nature.com/articles/s41467-021-25960-2) | Account for biological replicates; no universally optimal DE method for every estimand |
| Integration quality | [Luecken et al., Nature Methods](https://www.nature.com/articles/s41592-021-01336-8) | Assess both technical removal and biology; benchmark rankings depend on task |
| Feature-selection sensitivity | [Feature selection and integration/querying, 2025](https://www.nature.com/articles/s41592-025-02624-3) | HVG method/count affect the task; no universal fixed feature count |
| CNV/malignancy review | [Schmid et al., 2025](https://www.nature.com/articles/s41467-025-62359-9) | Independent benchmark across 21 datasets and 6 methods; reference, assay and genomic structure affect performance |
| Communication inference | [Dimitrov et al., 2022](https://www.nature.com/articles/s41467-022-30755-0) | Both method and prior resource alter predictions; transcript-based scores are not direct signaling measurements |
| AnnData structural semantics | [Official AnnData API](https://anndata.readthedocs.io/en/stable/generated/anndata.AnnData.html) and [read_h5ad](https://anndata.readthedocs.io/en/latest/generated/anndata.io.read_h5ad.html) | A raw snapshot is not certified counts; backed mode has slot/version limits. Latest documentation does not imply tested compatibility |

Local runtime versions and actual test scope are recorded in
[Runtime and audit limits](runtime-and-audit-limits.md). Source checks support
rules; synthetic helper tests do not establish full pipeline or biological
performance. The handoff and readiness system are author-designed conventions.

## Skill-Specific Additions

This skill adds requirements not supplied by a tutorial chapter sequence:

- explicit operating modes and readiness statuses;
- parameter decision cards and sensitivity checks;
- result-reading guidance tied to final parameter selection;
- dependency-aware rerun scope;
- tumor malignancy gates;
- claim calibration and handoff to scientific reasoning;
- regression cases for maintaining behavior.

## Maintenance Rule

At least before a material release:

1. check the source book changelog and affected chapters;
2. verify major method recommendations against current primary benchmarks or
   official documentation;
3. update the review logic rather than pinning tutorial package versions;
4. run all evaluation cases;
5. record the review date here.
