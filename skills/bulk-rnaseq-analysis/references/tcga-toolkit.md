# TCGA Toolkit Backend

## Repository contract

Validate the TCGA root by checking for:

- `tcga_toolkit/VERSION`
- `tcga_toolkit/scripts/run_task.R`
- `tcga_toolkit/specs/README.md`
- `tcga_toolkit/references/task_index.md`

Treat `tcga_toolkit/` as the canonical implementation. Read
`tcga_toolkit/specs/README.md` for configuration schemas and the task index
only for the selected task.

## Task families

| Goal | Tasks |
| --- | --- |
| Inspect and prepare | `audit_data`, `prepare_bulk_rna`, `cohort_qc` |
| Expression and enrichment | `run_deg`, `run_enrichment`, `ssgsea_score` |
| Clinical and survival | `run_clinical_assoc`, `stage_analysis`, `subtype_analysis`, `survival_map` |
| TME and immune | `run_tme`, `immune_phenotype` |
| Cross-cohort | `run_gtex_compare`, `pan_cancer_expression`, `validate_sc_signatures` |
| Mutation | `maf_summary`, `mutation_survival`, `tmb_analysis` |
| Multi-omics | `cnv_summary`, `methylation_diff` |
| Networks and models | `gene_correlation_heatmap`, `wgcna_modules`, `prognostic_model` |
| Validation and treatment | `external_validate`, `drug_response` |
| Orchestration and reports | `pipeline`, `render_report` |

Use `Rscript tcga_toolkit/scripts/list_tasks.R --json` as the
machine-readable source of the current task list.

## Standard workflow

1. Inspect the project and dependencies:

   ```bash
   Rscript tcga_toolkit/scripts/inspect_project.R --project TCGA-XXX
   Rscript tcga_toolkit/scripts/check_deps.R --task <task>
   Rscript tcga_toolkit/scripts/list_runs.R --task <task>
   ```

2. Reuse a JSON configuration from `tcga_toolkit/templates/`. In a v2 project,
   keep the reviewed project copy under `workflows/bulk-rnaseq/config/` and
   bind the external toolkit with `workflows/bulk-rnaseq/backend.lock.json`.
3. Validate without running:

   ```bash
   Rscript tcga_toolkit/scripts/validate_config.R --config <config.json>
   ```

4. For a v2 project, create one new
   `analysis/runs/bulk-rnaseq__<run_label>/` root and execute with that path as
   the toolkit output root:

   ```bash
   Rscript tcga_toolkit/scripts/run_task.R \
     --config <project>/workflows/bulk-rnaseq/config/<config.json> \
     --output-root <project>/analysis/runs/bulk-rnaseq__<run_label>
   ```

5. Read the native bundle under
   `analysis/runs/bulk-rnaseq__<run_label>/tcga_runs/<task_id>/`, including
   `report.md`, `run_metadata.json`, and results/plots/objects. Here
   `tcga_runs/` is backend-native structure inside the closed project run, not
   a project-level navigation root.

Do not use `--overwrite` for a v2 project run. Select a new namespaced run label
and preserve the earlier native bundle.

## Extension rule

If a requested cancer analysis is absent from the task list, follow the
external backend's `tcga_toolkit/references/extension_guide.md`, review and
commit the reusable toolkit task there, then create a new project backend lock.
Do not modify the revision already bound by a project lock, or implement a
one-off copy inside RNAseq-Templates or the Skill.

## Performance and data rules

- Inspect actual clinical columns before choosing group, subtype, or stage
  fields.
- Prefer targeted extraction from `GTEX/gtex_RSEM_gene_tpm.gz`; avoid loading
  the full multi-gigabyte GTEx matrix unless necessary.
- Run cohort QC before prognostic modelling.
- Record the toolkit version from `tcga_toolkit/VERSION` and
  `run_metadata.json`.
- Keep local restricted datasets out of the Skill and out of the
  RNAseq-Templates repository.
