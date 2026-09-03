# Shared reference management

## Reuse unit

A reference bundle is reusable only while all of these remain unchanged:

- species and assembly;
- genomic FASTA bytes and checksum;
- GTF source, release, bytes, and checksum;
- contig naming convention;
- HISAT2 build mode and index basename;
- transcript BED12 conversion inputs and method.

Store each bundle in a versioned directory such as:

```text
<REFERENCE_ROOT>/human/GRCh38_GENCODE_v49/
├── genome.fa
├── genome.fa.fai
├── genes.gtf
├── genes.bed12
├── reference.meta.tsv
└── hisat2_index/
    ├── genome_hisat2_index.1.ht2
    └── ... genome_hisat2_index.8.ht2
```

Projects set `REFERENCE_DIR` to this directory. They do not copy or modify the
bundle. Preserve old bundles so earlier projects remain reproducible.

## What is built once

For one exact FASTA/GTF release, create these once and reuse them:

- `genome.fa.fai`;
- the complete HISAT2 index;
- splice-site and exon helper files used for index construction;
- transcript-level `genes.bed12` for RSeQC;
- provenance and checksum metadata.

`genes.bed12` changes whenever the GTF changes. Rebuild it after an annotation
release change, a GTF filtering change, or a conversion-method change. A new
project using the same frozen GTF does not regenerate it.

## Updating references

Treat reference updates as version creation:

1. create a new empty version directory;
2. build it with `scripts/prepare_reference_hisat2.sh`;
3. validate it with `scripts/check_reference_layout.sh`;
4. test one known sample before making it the default for new projects;
5. retain the preceding version for reproduction.

Never replace files inside a bundle already used by a completed or active run.

## Existing local references

An existing bundle may be reused without rebuilding when it already satisfies
the layout checker and its assembly/annotation identity is known. Add or repair
`reference.meta.tsv` once at the reference-store level; do not create a separate
metadata copy in each analysis project. The run manifest records the selected
bundle path, expected IDs, and metadata checksum.

At minimum, the metadata table must contain:

```text
key\tvalue
bundle_schema_version\t1
reference_id\tGRCh38
annotation_id\tGENCODE_v49
fasta_sha256\t<sha256>
gtf_sha256\t<sha256>
bed12_sha256\t<sha256>
index_prefix\tgenome_hisat2_index
```

Use the real identifiers and checksums for the local bundle. Do not copy these
example values into another species or release.
