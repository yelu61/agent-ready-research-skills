# Scientific project profiles

Apply only the profile relevant to the project. These are audit prompts, not
automatic method choices.

## Bulk RNA-seq

- Confirm raw counts, annotation version, sample design and biological
  replicates.
- Record design formula, contrasts, filtering, normalization, shrinkage and FDR.
- Separate ranked enrichment from thresholded ORA.
- Track complete result tables separately from selected figures.

## Single-cell and spatial omics

- Record donor/sample as the experimental unit; never treat cells as biological
  replicates.
- Track raw counts, normalized matrices, embeddings and integrated objects.
- Record QC, doublet, batch integration, annotation hierarchy and excluded cells.
- Distinguish descriptive cell-level plots from sample-level inference.

## Proteomics, AP-MS and proximity labeling

- Confirm assay terminology; do not conflate AP-MS with enzymatic proximity
  labeling.
- Record protein/peptide level, missing encoding, normalization, imputation,
  controls, bait recovery and replicate evidence.
- Define candidate gates and enrichment universe explicitly.
- Separate co-enrichment from direct binding and causal mechanism.

## Multi-omics and time courses

- Maintain a cross-modality sample/subject/timepoint key.
- Audit missing modalities, nonmatching time points and modality-specific batch.
- Complete per-modality QC before integration.
- Treat cross-omics concordance as association unless causally validated.

## Public cohorts and clinical data

- Record repository, release, query/download date and identifier granularity.
- Separate sample-level and patient-level IDs.
- Define inclusion/exclusion, endpoint, censoring and covariates.
- Record privacy and redistribution constraints.

## Imaging and wet-lab-associated computation

- Preserve acquisition metadata, segmentation versions and blinded review state.
- Define image, field, section, animal and experiment as distinct units.
- Link computational outputs to experiment logs and validation batches.

## Manuscript-stage additions

- Freeze figure and table manifests.
- Track source data and exact panel versions.
- Maintain `AUTHOR_QUERIES.md`.
- Record database and software snapshots.
- Keep claims aligned across Results, Methods, legends and Supplementary Tables.
