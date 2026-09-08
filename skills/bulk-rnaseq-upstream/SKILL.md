---
name: bulk-rnaseq-upstream
description: Prepare and run reproducible paired-end short-read bulk RNA-seq upstream processing from FASTQ to gene-level integer counts using versioned shared references, HISAT2, featureCounts, optional trimming, and Xengsort for human-mouse mixtures. Use for raw-FASTQ upstream work; not for downstream differential analysis, single-cell, long-read, transcript-level quantification, or host-pathogen dual RNA-seq.
---

# Bulk RNA-seq upstream

Turn paired-end FASTQ into auditable gene-level integer counts. Determine the
sequence-source model before choosing a reference or executing a command.

Resolve `scripts/`, `assets/`, and `references/` relative to the directory that
contains this `SKILL.md`; do not assume the bundled files were copied into the
analysis project. In the examples below, `SKILL_DIR` is that resolved directory.

## Reference contract

Read [reference management](references/reference_management.md) when selecting,
registering, building, or updating a reference. Use a versioned, read-only shared
`REFERENCE_DIR`; do not download or rebuild the same reference in every project.

The immutable reference unit is the exact FASTA, GTF, assembly, annotation
release, build parameters, and checksums. Build its HISAT2 index, FASTA index,
and transcript BED12 once. A reference update creates a new directory; it never
changes an existing bundle in place.

Read [common species references](references/common_species_reference_map.md)
when choosing an assembly or annotation source.

## Choose the model

Read [model and reference routing](references/model_reference_routing.md) when a
sample may contain more than one biological sequence source.

- `single_species`: one species, one reference, one count matrix.
- `same_species_mixture`: one reference; bulk alignment cannot separate its
  constituent cell types.
- `cross_species_component`: host or graft FASTQ already split by Xengsort.
- `custom_combined`: a validated host-plus-construct combined reference.
- `spike_in`: a validated host-plus-spike-in combined reference.

Reject unsplit `cross_species` and `host_pathogen` FASTQ from the single-reference
runner. Host-pathogen dual RNA-seq requires a dedicated workflow.

## Single-species or prepared component

1. Copy [the run configuration](assets/rnaseq.env.example) from `SKILL_DIR` into
   the analysis project. Treat it as trusted shell input because the runner
   sources it.
2. Set `MODEL_MODE`, `REFERENCE_DIR`, the expected reference IDs, FASTQ suffixes,
   output directory, and strandedness parameters.
3. Validate the central reference:

   ```bash
   set -a
   source rnaseq.env
   set +a
   bash "$SKILL_DIR/scripts/check_reference_layout.sh" "$REFERENCE_DIR"
   ```

4. Run the preflight, then execute the same configuration only after it passes:

   ```bash
   bash "$SKILL_DIR/scripts/run_bulk_rnaseq_hisat2.sh" rnaseq.env --check-only
   bash "$SKILL_DIR/scripts/run_bulk_rnaseq_hisat2.sh" rnaseq.env
   ```

Do not assume strandedness. Use a representative alignment and the bundle's
transcript BED12 with RSeQC, then keep HISAT2 and featureCounts settings paired
as `none/0`, `FR/1`, or `RF/2`. Set `STRANDEDNESS_SOURCE` to `rseqc` or
`library_protocol` and `STRANDEDNESS_EVIDENCE` to the reviewed output/protocol
file. Unknown or missing evidence blocks preflight, including an unstranded
`none/0` choice. The runner records the evidence checksum; it does not interpret
the evidence or certify that the chosen protocol applies to every sample.

## Human-mouse mixture

1. Build and freeze one Xengsort index for the selected human/mouse reference
   pair with `scripts/prepare_reference_xengsort.sh`.
2. Copy [the Xengsort configuration](assets/xenograft_human_mouse.env.example).
   Set host/graft labels and reference IDs to the intended direction. Preflight
   checks these against the index's schema-2 manifest and verifies both index
   files by SHA-256 before classifying any reads.
3. Preflight and run `scripts/split_xenograft_xengsort.sh`.
4. Run the HISAT2 runner separately on `.graft.1/2.fq.gz` and
   `.host.1/2.fq.gz`, using distinct reference bundles and output directories.

Primary counting excludes `both`, `ambiguous`, and `neither` reads. Preserve all
five bins for QC. Never merge human and mouse count rows by gene symbol.

## Reference provisioning

Use `scripts/prepare_reference_hisat2.sh` only when creating a new central
reference bundle. It is an administrative operation, not a per-project analysis
step. It must finish with a complete eight-file HISAT2 index, transcript BED12,
FASTA index, metadata, and source checksums.

## Output and safety invariants

- Preserve sample, run, tool-version, reference, alignment, featureCounts, and
  MultiQC provenance.
- Use a new output directory for a changed sample set or configuration.
- Do not delete FASTQ, BAM, reference, or classification bins automatically.
- Align/count only the current sample manifest's files, including after trimming.
- Require count columns to match that manifest's BAMs in order, unique gene rows,
  and non-negative integer counts before handoff. A zero-count sample still needs
  biological/QC review; structural validation is not a quality threshold.

## Runtime and compatibility

Read [runtime and sources](references/runtime-and-sources.md) for external tools,
the tested boundary, method sources and compatibility changes. Reference metadata
now requires schema 2 and actual FASTA/GTF/BED12/FAI plus index fingerprints.
Legacy bundles fail with an actionable migration message; never manufacture a
new manifest to hide unknown source or build provenance.
