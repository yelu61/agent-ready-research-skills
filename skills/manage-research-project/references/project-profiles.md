# Scientific project profiles

Apply only the profile relevant to the project. These are audit prompts, not
automatic method choices.

For every profile, identify the independent unit, inclusion/exclusion rule,
source snapshot, domain, study type, analysis mode, requested claim class,
multiplicity family and target validation level. Route domain-specific
statistical decisions to the relevant analysis/review skill; this
project-management skill records and checks their contracts rather than
choosing methods.

## Bulk RNA-seq

- Confirm raw counts, annotation version, sample design and biological
  replicates.
- Verify sample-column to metadata-ID mapping; never accept positional mapping
  as provenance.
- Record design formula, contrasts, filtering, normalization, shrinkage and FDR.
- Separate ranked enrichment from thresholded ORA.
- Track complete result tables separately from selected figures.

## Single-cell and spatial omics

- Record donor/sample as the experimental unit; never treat cells as biological
  replicates.
- Record donor → specimen → capture/library → cell hierarchy and check that
  inference or data splitting does not leak donors across groups.
- Track raw counts, normalized matrices, embeddings and integrated objects.
- Record QC, doublet, batch integration, annotation hierarchy and excluded cells.
- Distinguish descriptive cell-level plots from sample-level inference.

## Proteomics, AP-MS and proximity labeling

- Confirm assay terminology; do not conflate AP-MS with enzymatic proximity
  labeling.
- Record protein/peptide level, missing encoding, normalization, imputation,
  controls, bait recovery and replicate evidence.
- Define candidate gates and enrichment universe explicitly.
- Distinguish missing-at-random assumptions, censoring/imputation choices and
  per-batch versus cross-batch validation.
- Separate co-enrichment from direct binding and causal mechanism.

## Multi-omics and time courses

- Maintain a cross-modality sample/subject/timepoint key.
- State which units truly overlap across modalities and how unmatched units are
  handled; sample-count concordance is not proof of identity.
- Audit missing modalities, nonmatching time points and modality-specific batch.
- Complete per-modality QC before integration.
- Treat cross-omics concordance as association unless causally validated.

## Public cohorts and clinical data

- Record repository, release, query/download date and identifier granularity.
- Record data-freeze/query specification, permitted use and whether the cohort
  was selected before or after observing outcomes.
- Separate sample-level and patient-level IDs.
- Define inclusion/exclusion, endpoint, censoring and covariates.
- Record privacy and redistribution constraints.
- Prevent patient/donor leakage across model development and validation sets.

## Imaging and wet-lab-associated computation

- Preserve acquisition metadata, segmentation versions and blinded review state.
- Define image, field, section, animal and experiment as distinct units.
- Record randomization, blinding/unblinding stage and exclusion decisions at the
  level where they occurred.
- Link computational outputs to experiment logs and validation batches.

## Manuscript-stage additions

- Freeze figure and table manifests.
- Track source data and exact panel versions.
- Maintain `AUTHOR_QUERIES.md`.
- Record database and software snapshots.
- Keep claims aligned across Results, Methods, legends and Supplementary Tables.
