# Runtime, evidence and source checks

## External dependencies

The skill ships orchestration and validation code, not reference genomes or
third-party bioinformatics binaries. Use an already approved environment or
prepare a separately managed one; record actual versions for each execution.
Do not infer successful installation from a skill being discoverable.

| Operation | Required runtime or command | Contract |
| --- | --- | --- |
| Local validators | Python 3.9+ (standard library only), Bash, basic Unix utilities | No Python package installation or network required |
| Alignment/counting | `hisat2`, `samtools`, `featureCounts` | Paired-end HISAT2 options, SAMtools view/sort/index/flagstat, featureCounts `-p --countReadPairs -B -C` |
| HISAT2 reference build | `hisat2-build`, `samtools`, UCSC `gtfToGenePred`/`genePredToBed`, `sha256sum` or `shasum` | Also HISAT2 splice/exon extractors unless `--no-annotation-index`; complete index and schema-2 manifest required |
| Human/mouse split | `xengsort`, `gzip` | `.hash/.info` index format and five paired FASTQ bins; intended host/graft IDs must match the frozen manifest |
| Xengsort index build | `xengsort`, `sha256sum` or `shasum` | `-H`/`-G` reference direction, `-n`, `-W`, fixed hash functions; resource needs depend on reference inputs |
| Optional QC/trimming | `fastqc`, `multiqc`, `trimmomatic` when enabled | Adapter FASTA required for trimming; disabling plots does not waive scientific QC |
| Strandedness evidence | `infer_experiment.py` from RSeQC, or a reviewed applicable library protocol | Evidence is reviewed externally; the runner records source/file/SHA-256 |

Run the selected command's `--help` and a small representative workflow when
adopting a new binary version; command presence alone does not establish API
compatibility. No exact end-to-end binary combination is certified by this
release. Record the successful environment lock/container digest after an
actual local validation, rather than publishing untested version pins.

## Strandedness and compatibility changes

Example configs intentionally start with unknown strandedness. Set a reviewed
`none/0`, `FR/1` or `RF/2`, `STRANDEDNESS_SOURCE=rseqc|library_protocol` and a
non-empty `STRANDEDNESS_EVIDENCE` file. That record should identify the library
protocol/sample set, observed RSeQC fractions when available, reviewer rationale
and chosen orientation. RSeQC evidence normally uses a small pilot alignment
without imposing a strand restriction and the frozen transcript BED12; pilot
output is diagnostic, not a completed primary count run. Ambiguous fractions
remain unresolved until reviewed; do not fabricate an unstranded conclusion.

Older configs without evidence and older references without schema-2 index
fingerprints fail preflight. Follow [reference management](reference_management.md)
to recover/build compatible bundles. These checks do not rewrite existing
configs, reference metadata, or data. The sample manifest adds a `bam` column
after the existing sample/r1/r2 fields. Relative paths are interpreted from
the runner's invocation directory; reuse that directory for standalone checks
or use absolute paths. No expression matrix transformations are performed.

## Validation boundary

Release checks on 2026-09-08 exercised the real Bash/Python runners using tiny
files and substitutable tool stubs. Tests cover reference-byte drift, legacy
and duplicate metadata, both HISAT2 index formats, host/graft identity swaps,
index drift before classification, unknown strandedness, stale trimmed sample
exclusion, sample-column identity/order and non-negative integer count rows.
This establishes wrapper/contract behavior, not alignment accuracy, strand
inference accuracy, Xengsort classification sensitivity or numerical biological
validity. The release-check environment had no HISAT2, SAMtools, featureCounts,
Xengsort, RSeQC, UCSC converters or optional QC/trimming tools on PATH, so no
real FASTQ-to-count integration run or real tool-version certification occurred.

Before production on a new environment, run a small known dataset with expected
fragments, verify strand orientation and reference identity, inspect mapping
and assigned/unassigned summaries, and check all requested figures. Input
preflight checks filenames/pair presence; it does not scan every input FASTQ
record or certify read-ID synchronization. The Xengsort post-check verifies
record totals and bin conservation, not sequence-classification truth. Count
validation accepts structurally valid zeros; poor mapping or all-zero samples
must still receive explicit scientific QC rather than being called usable.

## Sources and freshness

| Source | Checked | What it supports / boundary |
| --- | --- | --- |
| [HISAT2 manual](https://daehwankimlab.github.io/hisat2/manual/) | 2026-09-08 | Paired read orientation, `.ht2`/`.ht2l`, index and alignment flags; not a benchmark of this wrapper |
| [featureCounts official usage](https://subread.sourceforge.net/featureCounts.html) | 2026-09-08 | Explicit `-p --countReadPairs` for paired fragment counting and gene-level exon summaries |
| [Xengsort official repository/usage guide](https://gitlab.com/genomeinformatics/xengsort) | 2026-09-08 | Host/graft FASTA direction, index/classify interface and five bins; recheck installed release help before using |
| [PDX benchmark, npj Precision Oncology 2025](https://doi.org/10.1038/s41698-025-00902-z) | 2026-09-08 | Supports Xengsort as a defensible default within the study's references/library settings; not universal best performance |
| [Ensembl rat assembly update](https://www.ensembl.info/2024/07/19/updated-gene-annotation-for-rattus-norvegicus-norway-rat/) | 2026-09-08 | GRCr8 is the new rat reference candidate; preserve mRatBN7.2 when reproducing older work |
| [RSeQC documentation](https://rseqc.sourceforge.net/#infer-experiment-py) | Retrieval attempted 2026-09-08; timed out | Canonical documentation link retained; this release does not claim a freshly verified RSeQC API or release |

Recheck sources when the tool interface, library protocol or reference release
changes. Dates describe source verification, not a promise that every linked
page or external binary will remain available. Preserve verified source/build
provenance locally when freezing a run; an online outage must not be reported as
a successful lookup.
