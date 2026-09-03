#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  gtf_to_bed12.sh genes.gtf genes.bed12

Requires UCSC gtfToGenePred and genePredToBed. BEDOPS gtf2bed is not used:
it emits one extended BED row per GTF feature rather than transcript BED12.
EOF
}

if [[ $# -ne 2 ]]; then
  usage
  exit 1
fi

command -v gtfToGenePred >/dev/null 2>&1 || { echo "Missing command: gtfToGenePred" >&2; exit 1; }
command -v genePredToBed >/dev/null 2>&1 || { echo "Missing command: genePredToBed" >&2; exit 1; }

INPUT_GTF="$1"
OUTPUT_BED="$2"

[[ -f "${INPUT_GTF}" ]] || { echo "GTF not found: ${INPUT_GTF}" >&2; exit 1; }
[[ ! -e "${OUTPUT_BED}" ]] || { echo "Refusing to overwrite: ${OUTPUT_BED}" >&2; exit 1; }
[[ -d "$(dirname "${OUTPUT_BED}")" ]] || { echo "Output directory not found: $(dirname "${OUTPUT_BED}")" >&2; exit 1; }

TMP_GENEPRED=$(mktemp "${TMPDIR:-/tmp}/gtf_to_bed12.genepred.XXXXXX")
TMP_BED=$(mktemp "${OUTPUT_BED}.tmp.XXXXXX")
trap 'rm -f "${TMP_GENEPRED}" "${TMP_BED}"' EXIT

gtfToGenePred -genePredExt -ignoreGroupsWithoutExons "${INPUT_GTF}" "${TMP_GENEPRED}"
genePredToBed "${TMP_GENEPRED}" "${TMP_BED}"

awk 'BEGIN { seen=0 }
  /^#/ || NF == 0 { next }
  {
    seen=1
    if (NF != 12) {
      print "Expected exactly 12 BED columns, found " NF " at line " NR > "/dev/stderr"
      exit 1
    }
    if ($10 !~ /^[1-9][0-9]*$/) {
      print "Invalid BED12 blockCount at line " NR > "/dev/stderr"
      exit 1
    }
    sizes=$11
    starts=$12
    sub(/,$/, "", sizes)
    sub(/,$/, "", starts)
    if (split(sizes, block_sizes, ",") != $10 || split(starts, block_starts, ",") != $10) {
      print "BED12 blockCount does not match blockSizes/blockStarts at line " NR > "/dev/stderr"
      exit 1
    }
  }
  END { if (!seen) { print "BED12 output is empty" > "/dev/stderr"; exit 1 } }' "${TMP_BED}"

mv "${TMP_BED}" "${OUTPUT_BED}"

echo "BED12 written to: ${OUTPUT_BED}"
