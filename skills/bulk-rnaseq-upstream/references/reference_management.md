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

An existing bundle may be reused without rebuilding when it satisfies the
schema-2 layout/fingerprint checker and its assembly/annotation identity is
known. The checker streams and hashes every FASTA, FAI, GTF, BED12 and all eight
index files each time; allow time for this read-only pass on large bundles.
The run manifest records the selected bundle path, expected IDs and metadata
checksum. Hash agreement detects drift from recorded bytes; it does not prove
biological compatibility when the original build record was incorrect.

At minimum, the metadata table must contain:

```text
key\tvalue
bundle_schema_version\t2
reference_id\tGRCh38
annotation_id\tGENCODE_v49
fasta_sha256\t<sha256>
fai_sha256\t<sha256>
gtf_sha256\t<sha256>
bed12_sha256\t<sha256>
index_prefix\tgenome_hisat2_index
index_suffix\tht2
index_1_sha256\t<sha256>
... index_2_sha256 through index_8_sha256 ...
```

Use the real identifiers and checksums for the local bundle. Do not copy these
example values into another species or release.

## Legacy bundles and Xengsort

Schema-1 metadata with only FASTA/GTF/BED12 fields no longer passes. Do not
blindly hash the files now present and call that evidence of the historical
build. First recover the original FASTA/GTF releases, build logs/parameters,
index version and a trusted record establishing that the index/BED12/FAI were
derived from those inputs. Check the old recorded input hashes before adding
new fields. With that evidence, a reference-store administrator may register a
new versioned metadata bundle describing the unchanged verified bytes, retaining
the old metadata; projects should not patch the old bundle in place. If source
identity cannot be recovered, build a fresh reference from known inputs in a
new directory. There is no automatic schema-upgrade command.

New Xengsort builds additionally require `--host-label`, `--graft-label`,
`--host-reference-id` and `--graft-reference-id`. The builder records these
alongside source FASTA counts, per-FASTA fingerprints and SHA-256 of `.hash`
and `.info`. Classification compares all four identities to the run config
before execution. Original FASTA paths need not remain mounted when reusing
a frozen index; their identities/hashes are preserved provenance, while both
index files are always checked. Legacy Xengsort indices require recovered
direction/build evidence and schema-2 registration, or a new verified build.

Only one complete HISAT2 `.ht2` or `.ht2l` set is permitted per index prefix.
Mixed formats are rejected rather than letting the aligner choose a set other
than the one that was verified.
