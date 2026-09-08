# Cross-modality identity and matching review

Use this small registry when results from bulk RNA, single-cell, spatial,
proteomic or other measurements need to be related. Keep existing file paths;
these tables may live beside the project's existing sample metadata. This is
an optional identity check, not a prerequisite for unrelated project work.
It requires only Python 3.11+ and the standard library, with no other skill,
analysis backend, scLucid or network connection.

## Two tables, no implied pairing

`measurements.tsv` or `.csv` requires five columns:

| Column | Meaning |
|---|---|
| `measurement_id` | Unique stable ID of an assay, library, image, or cell-level measurement represented by this row |
| `donor_id` | Stable donor / subject / experimental organism ID; use appropriate biological unit terminology in the project dictionary |
| `specimen_id` | Stable ID of one biological collection specimen; a new collection timepoint needs a new specimen ID |
| `modality` | What was measured; consistent project-defined labels such as `scRNA`, `spatial-RNA`, `ATAC` |
| `timepoint` | Biological collection timepoint, using consistent project-defined labels; not sequencing date |

Only add `aliquot_id`, `section_id`, `cell_id`, `cell_namespace` when relevant.
Additional columns such as `source_record`, `artifact_id`, `batch`, or
`run_id` are preserved in the input and permitted, but not interpreted by this
checker. Put stable source-record references in these columns to support later
human or domain review. These are declared records, not externally verified
identity evidence.

IDs are global within the table except cells, whose identity is the pair
`(cell_namespace, cell_id)`. Use project-qualified aliquot/section IDs rather
than reusing `section1` across specimens. A cell namespace must represent a
documented comparable identity system, such as a shared multimodal capture
with a recorded barcode-matching procedure. Two independent libraries sharing
the same barcode sequence do not identify the same biological cell. Do not
use cluster labels, inferred cell types, pooled assays or spot IDs as cell IDs
to claim exact same-cell pairing. Spots may contain several cells.

Unknown biological identity fields may be blank. Blank, `NA`, `N/A`, `unknown`,
`TODO`, `none`, and `null` (case-insensitive) are reserved missing values and
produce review findings. They are not merged as a shared identity. A missing
measurement ID or modality is an error. Do not fill unknown fields by guessing.
Pool or mixed-donor measurements need their own explicit constituent mapping;
this minimal checker does not model mixtures or certify deconvolution.

`pairs.tsv` or `.csv` is optional and requires `left_id`, `right_id`, `relation`.
Add the recommended `evidence` column containing a source-record reference or
brief matching rationale. Missing evidence produces a review finding. Evidence
text is not fetched, verified, or judged sufficient by this tool.

| `relation` | Documentary conditions | What it does not establish |
|---|---|---|
| `same_donor` | Same known donor; different collection timepoints prompt review | Same specimen, simultaneous measurement, same cells |
| `same_specimen` | Same donor, collection specimen and timepoint | Same aliquot, section, cell or independent replicate |
| `same_cell` | Same donor, specimen, timepoint, cell namespace and cell ID; different sections require review | Biological identity merely because names/barcodes match |
| `longitudinal` | Same donor with different collection timepoints and specimens | Time order, exchangeability, causal effects or model suitability |

Relationships are explicit, undirected declarations. No relationship is inferred
from names, row order, equal counts, matching donor alone, or transitive chains.
Multiple sections can legitimately be related as `same_specimen`; this never
promotes them to the same cell. Cross-section exact cell identity needs a
separate spatial/identity review even if it is asserted in the table.
Timepoints are labels: the checker neither sorts them nor equates `baseline`
with `T0`. Use a project dictionary to harmonize labels with evidence.
Here `longitudinal` means serial biological collections. For repeated live
imaging or repeated assays of one stored specimen, retain the collection
timepoint, record a separate observation/assay time in an extra column, and
declare `same_specimen` where supported. This checker does not model the
temporal design of those experiments.

Unpaired and partially paired studies are valid registry use cases. Omit the
pairs file or supply only documented pairs. Remaining measurements are listed
as unpaired without an error or invented match. A registry does not determine
whether a downstream algorithm supports that pairing pattern. Domain review
must still assess experimental units, sample counts, missingness, batch/design
confounding and the intended statistical comparison.

## Run and interpret

```bash
python scripts/validate_sample_map.py \
  --measurements /path/to/measurements.tsv --pairs /path/to/pairs.tsv --json
```

The command reads tables and emits a report to stdout; it creates, edits and
overwrites no files. CSV/TSV format follows the filename extension. UTF-8 with
or without a BOM is accepted. Use ordinary shell redirection to a **new** report
path if needed, never an input path. Inputs have SHA-256 hashes in the report.

- Exit `0`, `valid`: documentary consistency checks found no issue.
- Exit `1`, `review`: incomplete identities, unsupported pairing evidence or
  other unresolved context; useful checks and the unpaired inventory remain
  available.
- Exit `2`, `invalid`: malformed tables, duplicate IDs, conflicting biological
  parents, or a contradiction in an explicit relation.

Every report explicitly sets `identity_authenticity_verified=false` and
`scientific_validity_assessed=false`. A passing table must never become a
scientific readiness declaration. During checkpoint/archive, record the input
hashes, report and unresolved issues with the relevant result/analysis records.
Retain source records and the adjudication of conflicts; do not edit IDs merely
to make a checker pass. One library's cells, adjacent sections and repeated
assays are not automatically independent biological replicates.

## Synthetic examples

All supplied rows and evidence labels are fabricated test fixtures, not research
data or factual identity assertions:

- [Paired measurements](../assets/examples/multimodal-paired-measurements.tsv)
  and [explicit pairs](../assets/examples/multimodal-paired-pairs.tsv): same
  capture cells across modalities plus distinct sections of one specimen.
- [Unpaired measurements](../assets/examples/multimodal-unpaired-measurements.tsv):
  valid with no `--pairs` argument.
- [Longitudinal measurements](../assets/examples/multimodal-longitudinal-measurements.csv)
  and [pairs](../assets/examples/multimodal-longitudinal-pairs.csv): serial
  collections, with distinct specimen IDs.
- [Conflicting measurements](../assets/examples/multimodal-conflict-measurements.tsv)
  and [pairs](../assets/examples/multimodal-conflict-pairs.tsv): reject a
  specimen assigned to different donors and mismatched pairing identities.

The table schema and validator are original project-management code. They do
not implement a community sample ontology or a full patient identity service.
