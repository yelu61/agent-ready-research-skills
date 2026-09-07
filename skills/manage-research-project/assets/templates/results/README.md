# Curated results

This directory contains reviewed deliverables. Choose question or domain-module
navigation for the intended audience and document the current delivery here.
For example, a question-oriented layout is:

    results/
    └── <question_id>/
        ├── tables/
        ├── figures/
        └── report/

RNA-seq may instead use `00_report/`, `01_qc/`, `02_degs/`, `03_ORA/`,
`04_GSEA/`, and `05_custom_genes/`, with tables and figures within each module.
Create directories when they have deliverables or explicit empty-result records. Complete
backend-native output stays in analysis/runs/<run_id>/; temporary intermediates
stay inside that run. Every curated artifact must link to its source run and
source artifact in provenance/ARTIFACTS.tsv.

Share physical files and included relative report resources. Provenance records
identify source runs, but opening this delivery must not require those runs.
Complete reviewed module output and a short headline report may coexist.
