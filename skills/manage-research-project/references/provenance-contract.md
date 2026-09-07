# Provenance and integrity contract

Provenance answers what an artifact is, where it came from and which execution
created it. Integrity checks whether recorded bytes changed. Neither proves
source authenticity, analytical validity or biological truth.

## Three linked records

### Layout identity

New projects record `research-project-layout/v2` in
`provenance/PROJECT_LAYOUT.json`. The manifest identifies the only authored
workflow root, native-run root, notebook-output root, curated-results root,
run-ID pattern and external locked-backend policy. It is structural metadata,
not evidence that an analysis ran or is scientifically ready.

Projects without this manifest are legacy projects. Do not synthesize the
manifest during retrofit or infer that legacy paths have migrated.

### Source baseline

`provenance/SOURCE_MANIFEST.json` records immutable source IDs, project-relative
paths, byte sizes, SHA-256 checksums, scope and source/access context. Create it
with `build_source_manifest.py`; the command is dry-run and refuses overwrite.
Each `source_id` is deterministically derived from the normalized relative path
and current digest, so changing bytes at the same path produces a new identity.

```bash
python scripts/build_source_manifest.py /path/to/project --json
python scripts/build_source_manifest.py /path/to/project --apply \
  --source-system GEO --source-reference GSE12345 \
  --acquired-at 2026-09-03T00:00:00Z --data-freeze-id GSE12345-2026-09-03 \
  --access-level public --subject-id-level deidentified
python scripts/verify_source_manifest.py /path/to/project --json
```

Replace the example accession, freeze and acquisition time with verified source
metadata. Omit an unknown optional field rather than recording an example or
placeholder as fact; such a manifest cannot support
`source_provenance_status=verified` until the identity context is complete.

Changed, missing or unexpected files inside the declared scope fail integrity.
Absolute paths, parent traversal and symlinks are rejected. A hash demonstrates
byte identity only; source system, release, acquisition date, license/agreement
and identifier level still require evidence.

Use the same non-overwriting builder with explicit code include paths and a
different output (for example `provenance/CODE_MANIFEST.json`) to bind the
actual executable code used by a readiness report. Do not substitute a text
revision label for file coverage.

### Artifact registry

`provenance/ARTIFACTS.tsv` assigns immutable `artifact_id` values to sources,
specifications, configs, intermediates and deliverables. Record parent artifact
IDs, propagated source IDs, generating run, checksum, access class and lifecycle
status. Never reuse an artifact ID for different bytes or meaning.

A readiness-cited artifact row must contain a concrete artifact ID, analysis
ID, project-relative path, role and RFC 3339 recording time; verified or
not-applicable source provenance; current lifecycle; valid access class; exact
SHA-256 and byte size. Restricted or controlled artifacts also require an
agreement/access reference. Its `analysis_id` must match the assessment, and an
output artifact's `run_id` must match the run that cites it. For a data-bearing
analysis, semicolon-delimited `source_ids` must be a non-empty subset of the
assessment's source IDs; the input, output and validation artifacts cited by a
run must each collectively cover the exact assessed source set. Data-free
artifacts must leave `source_ids` empty.

### Run registry

`provenance/RUNS.tsv` records what actually executed: analysis ID, entry point,
hash-bound config, input/output artifact IDs, revisions, environment, timestamps, exit
code and log. It can also bind the exact readiness ID/report/hash that
authorized the run. An evidence-generating run may legitimately precede the
new readiness decision; in that case, leave the current-readiness fields empty
or bind the earlier authorization rather than creating a circular hash between
the run row and the report that cites it. `execution_status=completed` proves
only process completion.
Technical validation records its kind, scope, criterion and evidence IDs. The
achieved scientific-validation level, claim authorization and readiness remain
separate fields and records.

Artifact-ID lists use semicolons, for example `ART-IN-01;ART-IN-02`. A run used
as `PASS`/`NA` evidence must close every input, output and validation-evidence
ID uniquely to `ARTIFACTS.tsv`, may not reuse one artifact as both input and
output, may not use the same registered path as both input and output, must
bind each output back to the run, and must point to an existing
non-symlink log. It must also match the assessed spec, entry point, code state,
backend and environment; have ordered RFC 3339 timestamps, exit code zero and
passed technical validation. Input artifact IDs may be empty only for a spec
whose explicit `data_requirement` is `none`; outputs and validation evidence
remain mandatory.

For a `PASS`/`NA` run, `config_path` is either a project-relative regular file
bound by `config_sha256`, or the exact literal `not_applicable` with an empty
hash. Each output's `parent_artifact_ids` must exactly match that run's declared
input artifact IDs. The free-text `role` column remains descriptive rather than
a machine-enforced artifact type; run fields and parent links carry the
machine-checked input/output semantics.

Readiness evidence stores `record_sha256` for the canonical referenced
artifact row, run row or decision section. Recomputing that digest does not
make an incomplete row acceptable: the semantic row checks above still apply.
Registries are append-only histories; supersede or invalidate records instead
of silently editing evidence already used by an assessment.

A readiness `run` evidence object also stores `log_sha256` and an
`artifact_record_sha256s` map. The map keys must exactly equal the union of the
run's input, output and validation artifact IDs. This assessment-level binding
detects later log edits and artifact-ID rebinding even when the RUNS row itself
has not changed.

Canonical row bytes are UTF-8 JSON of the complete header-to-string mapping
with keys sorted, no insignificant whitespace and non-ASCII text preserved.
Canonical decision bytes are the matched Markdown section after surrounding
whitespace is stripped, followed by one newline. The validator uses these rules
so a record digest is portable across platforms and independent of TSV column
order.

## Lineage closure

### Importing native run metadata

Use the generic importer instead of writing a project-specific registration
script when a domain adapter supplies mapped metadata:

```bash
python scripts/register_run.py /path/to/project \
  --metadata workflows/<workflow_id>/registration.json
python scripts/register_run.py /path/to/project \
  --metadata workflows/<workflow_id>/registration.json --apply
```

The JSON has `run` using existing RUNS.tsv field names and an `artifacts` list
using ARTIFACTS.tsv fields. An artifact may additionally declare `direction`
(`input`, `output`, `delivery`) and `parent_paths` naming other registered paths.
Use `direction=reference` for an already registered source from a parent run;
it must resolve uniquely by path and checksum. Existing input identities are
also reused, preserving their original generating run.
All paths are project-relative regular files. The importer computes SHA-256,
sizes and stable IDs, resolves parent links, fills the run's input/output IDs,
and appends idempotently; it refuses to rebind an existing ID or follow symlinks.
Delivery copies receive distinct artifact IDs and link to native source rows.
Do not run independent manual registry writes concurrently with an import.
An older registry with a different header is left unchanged; inspect its
contract before a separately scoped migration rather than silently replacing it.

Missing provenance/access/validation remain unverified/unknown/not_assessed.
The importer neither creates readiness nor supplies missing execution evidence.
A native completion timestamp does not establish exit status or passed
validation. Add source IDs and reviewed evidence through the established domain
contract before using an imported row as scientific readiness evidence.

### Typed manifest paths

Ordinary `*_path` fields always name paths. In mixed `path_or_value` columns,
use `value_type` (`path`, `commit`, `revision`, `identifier`, `value`) to disambiguate;
legacy bare hexadecimal commit values are also recognized. Portable delivery
manifests with `path`, `source_path`, `source_run_id` resolve `path` relative to
the manifest directory; source paths document ancestry without requiring the
source run to travel with the delivery. Missing real file targets still warn.

Before using an output in `results/` as a reviewed conclusion, require all of the
following:

1. the run identifies exact input and output artifact IDs;
2. those input source IDs occur in the bound source manifest;
3. the analysis spec hash matches the run context; if a readiness report
   authorized that run, its recorded ID/path/hash matches that prior record;
4. execution completed and expected files exist;
5. the readiness declaration is current for the intended use;
6. the proposed wording stays within the report's
   `authorized_claim_classes`;
7. the curated artifact links back to the immutable native run.

Decision evidence must close uniquely to a `D-YYYYMMDD-NN` section in
`docs/DECISION_LOG.md`, bind the analysis or scope, match its encoded date and
contain exactly one concrete `Decision`, `Evidence/source` and `Reason` field.

Propagated source IDs make lineage explicit and internally checkable; they do
not prove that a transformation really used those sources. Domain assessment
must still inspect the registered parents, run logic and scientific evidence
when that truth matters.

Diagnostic outputs from blocked or failed runs may be retained, but they must
not become the current conclusion source.

## Restricted or unavailable sources

Do not bypass permissions to compute a checksum. `hash_status=not_permitted`
is only for a local source that policy permits registering but not reading; it
requires an access reference and produces review/unknown integrity. A remote or
controlled source that is not locally materialized should be recorded as an
external accession/reference in project documentation, not as a fictitious
local file entry.

Never place credentials, direct identifiers or re-identification keys in a
manifest, log or restart prompt.

## Snapshot and archive

An archive records snapshot ID, parent snapshot, git revision and dirty state,
included/excluded scope, hashes, environment, current readiness records, open
issues and access constraints. Re-verify after copying. Restricted raw data are
referenced rather than copied unless authorization explicitly permits copying.

An archive is a preservation event; it does not imply reproduction,
independent validation or scientific confirmation.
