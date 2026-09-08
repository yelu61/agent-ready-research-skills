#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  check_reference_layout.sh /path/to/versioned/reference_bundle [index_prefix]
EOF
}

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage
  exit 1
fi

REFDIR="$1"
PREFIX="${2:-${REFDIR}/hisat2_index/genome_hisat2_index}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
command -v python3 >/dev/null 2>&1 || { echo "Missing command: python3" >&2; exit 1; }

missing=0

check_file() {
  local path="$1"
  if [[ ! -s "${path}" ]]; then
    echo "Missing or empty: ${path}" >&2
    missing=1
  else
    echo "OK: ${path}"
  fi
}

check_file "${REFDIR}/genome.fa"
check_file "${REFDIR}/genes.gtf"

if [[ -e "${REFDIR}/genes.bed12" ]]; then
  if awk 'BEGIN { seen=0 }
    /^#/ || NF == 0 { next }
    {
      seen=1
      if (NF != 12 || $10 !~ /^[1-9][0-9]*$/) exit 1
      sizes=$11
      starts=$12
      sub(/,$/, "", sizes)
      sub(/,$/, "", starts)
      if (split(sizes, block_sizes, ",") != $10 || split(starts, block_starts, ",") != $10) exit 1
    }
    END { if (!seen) exit 1 }' "${REFDIR}/genes.bed12"; then
    echo "OK: ${REFDIR}/genes.bed12 (transcript BED12)"
  else
    echo "Invalid: ${REFDIR}/genes.bed12 does not contain transcript BED12 rows" >&2
    missing=1
  fi
else
  echo "Missing: ${REFDIR}/genes.bed12 is required for RSeQC strandedness checks" >&2
  missing=1
fi

complete_index_set() {
  local suffix="$1"
  local part
  for part in {1..8}; do
    [[ -s "${PREFIX}.${part}.${suffix}" ]] || return 1
  done
}

if complete_index_set "ht2" || complete_index_set "ht2l"; then
  echo "OK: complete HISAT2 index found for prefix ${PREFIX}"
else
  echo "Missing or incomplete: expected all eight HISAT2 index files for prefix ${PREFIX}" >&2
  missing=1
fi

if [[ -e "${REFDIR}/genome.fa.fai" ]]; then
  echo "OK: ${REFDIR}/genome.fa.fai"
  TMP_CHECK=$(mktemp -d "${TMPDIR:-/tmp}/check_reference_layout.XXXXXX")
  trap 'rm -rf "${TMP_CHECK}"' EXIT
  awk '{print $1}' "${REFDIR}/genome.fa.fai" | sort -u > "${TMP_CHECK}/fasta.contigs"
  awk '$0 !~ /^#/ && NF >= 1 {print $1}' "${REFDIR}/genes.gtf" | sort -u > "${TMP_CHECK}/gtf.contigs"
  comm -23 "${TMP_CHECK}/gtf.contigs" "${TMP_CHECK}/fasta.contigs" > "${TMP_CHECK}/gtf_only.contigs"
  if [[ -s "${TMP_CHECK}/gtf_only.contigs" ]]; then
    echo "Invalid: GTF contains contigs absent from FASTA:" >&2
    sed -n '1,10p' "${TMP_CHECK}/gtf_only.contigs" >&2
    missing=1
  else
    gtf_contigs=$(wc -l < "${TMP_CHECK}/gtf.contigs" | tr -d ' ')
    echo "OK: all ${gtf_contigs} GTF contig name(s) occur in FASTA"
  fi
else
  echo "Missing: ${REFDIR}/genome.fa.fai; contig compatibility cannot be checked" >&2
  missing=1
fi

if [[ -e "${REFDIR}/.build_incomplete" ]]; then
  echo "Invalid: incomplete reference-build marker found at ${REFDIR}/.build_incomplete" >&2
  missing=1
fi

if ! python3 "${SCRIPT_DIR}/verify_reference_fingerprints.py" hisat2 "${REFDIR}" "${PREFIX}"; then
  missing=1
fi

if [[ "${missing}" -ne 0 ]]; then
  exit 1
fi

echo "Reference layout looks usable."
