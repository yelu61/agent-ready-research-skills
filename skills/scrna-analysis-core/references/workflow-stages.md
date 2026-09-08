# Workflow Stage Review

Use this reference for the executable path from input provenance through stable
cell identities. Report evidence and decisions; do not merely list tools.

## 1. Provenance and Object Integrity

Require:

- source and version of the count matrix, reference genome, chemistry, and
  feature definition;
- unique cell and feature identifiers;
- an authoritative raw-count representation;
- explicit biological sample, condition, and technical batch fields;
- preserved original identifiers and a record of derived fields;
- sparse storage where appropriate and separation of counts from transformed
  representations.

`layers["counts"]` is the preferred explicit location for count-based tools.
`adata.raw` is a gene-expression snapshot, not a universal replacement for a
counts layer. Do not assume `.X` semantics from its numeric type alone.

Block formal comparisons when the biological sample or experimental unit
cannot be reconstructed.

## 2. Raw Data and Droplet Decisions

Record whether input is raw reads, an unfiltered droplet matrix, or a filtered
cell matrix. For droplet assays, review:

- cell-calling evidence and recovery relative to experimental expectations;
- empty droplets and ambient RNA source profile;
- sample-specific chemistry and sequencing depth;
- whether ambient correction was performed before downstream transformation;
- whether raw and corrected counts remain separately available.

Ambient correction is not automatically required for every dataset. Recommend
it when contamination is plausible and materially changes marker specificity
or downstream interpretation. Verify known soup genes and plausible expression
after correction.

## 3. Cell Quality and Doublets

Assess QC distributions per sample or library, jointly across:

- total counts or reads;
- detected features;
- mitochondrial fraction with species-aware feature mapping;
- optional ribosomal, hemoglobin, stress, or modality-specific metrics;
- library complexity and top-gene dominance;
- expected cell-type size or RNA-content differences.

Use robust, lenient, sample-aware outlier rules as a starting point. Fixed
global cutoffs require empirical justification. Always report cells removed per
sample and per provisional lineage, and reassess after annotation when rare or
fragile populations could be selectively lost.

Run doublet detection per capture or technical batch, not after aggregating
unrelated batches. Combine scores with expected multiplet rate, library
loading, cluster context, and mixed-lineage markers. Flag uncertain cells when
hard removal would erase plausible biology.

## 4. Normalization and Feature Selection

Choose the representation according to its consumer:

| Consumer | Appropriate input |
| --- | --- |
| Visualization and many Scanpy exploratory steps | shifted-log or another documented normalized representation |
| Count models, pseudobulk, scVI | untransformed counts expected by the model |
| PCA or neighbor graph | method-compatible normalized or residual representation |
| Marker visualization | non-integrated expression with known scale |

Do not require a whole-dataset `scaled` layer. Scaling can densify large
objects and is a method-specific intermediate.

Feature selection should preserve the biology required by the objective.
Record method, batch handling, number of selected features, excluded feature
classes, and whether known lineage or target genes remain observable. HVG
counts such as 2,000 or 4,000 are candidates for sensitivity analysis, not
universal truths.

## 5. Dimensionality Reduction and Neighborhoods

Choose PC or latent dimensions using several signals: variance or deviance,
technical association, biological structure, neighbor stability, and
downstream sensitivity. UMAP is a visualization of a chosen graph, not evidence
of discrete populations or quantitative distance.

For neighbors, record representation, dimensions, metric, neighborhood size,
random seed, and software versions. Test whether major conclusions survive
reasonable changes in dimension and neighborhood choices.

## 6. Integration

First ask whether integration is needed. Visualize unintegrated data and
separate batch effects from biological composition differences. Never correct
away a condition that is structurally confounded with batch.

Inspect the batch-by-condition graph and the full design matrix. Disconnected
components can make cross-component contrasts non-estimable while leaving
within-component contrasts estimable. State the actual contrast. Assess paired
or repeated units and other covariates separately; a connected graph is not a
guarantee of biological replication or absence of unmeasured confounding.

Select an integration model based on:

- batch hierarchy and overlap of shared populations;
- whether labels or a reference are available;
- whether the purpose is visualization, clustering, reference mapping, or
  expression modeling;
- scale, compute constraints, and reproducibility.

Evaluate at least biological conservation and batch removal. Use qualitative
checks plus relevant quantitative metrics; no single score establishes
validity. Compare unintegrated and integrated representations and, for
consequential work, compare more than one defensible strategy.

Use the integrated latent space for neighborhoods or mapping when justified.
Do not use batch-corrected or integrated expression for pseudobulk differential
expression unless the statistical model explicitly supports that use.

## 7. Clustering

Use graph community detection such as Leiden when discrete partitions are
useful. Treat resolution as a biological granularity decision. Prefer broad
lineages followed by compartment-specific subclustering over a single very
high-resolution partition.

Review:

- stability across seeds, resolutions, and reasonable graph settings;
- per-sample contribution to each cluster;
- marker coherence and negative-marker contradictions;
- doublet, low-quality, cell-cycle, stress, and dissociation enrichment;
- whether continuous states are being forced into arbitrary clusters.

Clusters are computational partitions, not cell types.

## 8. Annotation and Cell States

Use a hierarchy: compartment -> lineage -> type -> state. Combine:

- multiple positive and negative markers;
- tissue and disease context;
- per-sample reproducibility;
- reference mapping or automated prediction with confidence and ontology;
- manual review of conflicts and unknown or mixed labels.

Reference-based labels depend on reference quality and query similarity. Keep
predicted, reviewed, and final labels in separate fields. Record marker
evidence, prediction confidence, reviewer, and version.

Separate identity from state: activation, stress, cycling, interferon response,
exhaustion, and therapy response should not automatically define a new cell
type. Derive state programs using coherent gene sets and replicate-level
patterns rather than a single marker.

## 9. Tumor-Specific Gates

Separate malignant-cell inference from immune and stromal annotation. Do not
label malignancy from epithelial markers or a single CNV call. Combine
sample-aware evidence such as:

- tissue origin and epithelial identity;
- broad CNV pattern with plausible normal references;
- tumor-associated programs and inter-patient structure;
- orthogonal genomic, pathology, or known driver evidence when available.

Keep `malignant`, `non_malignant`, and `uncertain` states. Distinguish
clone-like genomic structure from reversible transcriptional state. Report CNV
method assumptions and sensitivity to reference-cell selection.

Near-diploid malignant cells and non-epithelial cancers may lack the usual CNV
or epithelial evidence; retain uncertain labels instead of inferring normality
from absence of CNV. Cell-state expression can mimic broad genomic patterns.
Choose expression-only versus allele-aware methods according to assay, read
availability and reference quality; compare orthogonal DNA/pathology when
available. Do not promote expression-inferred clone-like groups to validated
lineages. Current primary benchmarks are linked in [Source map](source-map.md).
