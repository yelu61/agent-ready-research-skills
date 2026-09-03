#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  prepare_reference_hisat2.sh --fasta genome.fa --gtf genes.gtf \
    --outdir /path/to/shared/rnaseq_refs/human/GRCh38_GENCODE_v49 \
    --reference-id GRCh38 --annotation-id GENCODE_v49 --threads 16 \
    [--prefix genome_hisat2_index] [--no-annotation-index]

What it does:
  1. Creates hisat2_index/
  2. Generates splice-site and exon helper files from GTF
  3. Builds a HISAT2 index
  4. Generates FASTA index and transcript BED12

Required:
  --fasta    Path to genome FASTA
  --gtf      Path to gene annotation GTF
  --outdir   Standardized reference output directory
  --reference-id   Assembly identifier recorded in reference.meta.tsv
  --annotation-id  Annotation source/release recorded in reference.meta.tsv

Optional:
  --threads  Number of threads, default 16
  --prefix   Index basename, default genome_hisat2_index
  --no-annotation-index   Build plain index without --ss/--exon
EOF
}

FASTA=""
GTF=""
OUTDIR=""
THREADS=16
PREFIX="genome_hisat2_index"
USE_ANNOTATION_INDEX="yes"
REFERENCE_ID=""
ANNOTATION_ID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --fasta|--gtf|--outdir|--threads|--prefix|--reference-id|--annotation-id)
      option="$1"
      [[ $# -ge 2 && -n "${2:-}" && "${2}" != --* ]] || {
        echo "Missing value for ${option}" >&2
        usage
        exit 1
      }
      case "${option}" in
        --fasta) FASTA="$2" ;;
        --gtf) GTF="$2" ;;
        --outdir) OUTDIR="$2" ;;
        --threads) THREADS="$2" ;;
        --prefix) PREFIX="$2" ;;
        --reference-id) REFERENCE_ID="$2" ;;
        --annotation-id) ANNOTATION_ID="$2" ;;
      esac
      shift 2
      ;;
    --no-annotation-index) USE_ANNOTATION_INDEX="no"; shift 1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ -z "${FASTA}" || -z "${GTF}" || -z "${OUTDIR}" || -z "${REFERENCE_ID}" || -z "${ANNOTATION_ID}" ]]; then
  echo "--fasta, --gtf, --outdir, --reference-id and --annotation-id are required" >&2
  usage
  exit 1
fi

[[ "${THREADS}" =~ ^[1-9][0-9]*$ ]] || { echo "--threads must be a positive integer" >&2; exit 1; }
command -v hisat2-build >/dev/null 2>&1 || { echo "Missing command: hisat2-build" >&2; exit 1; }
command -v samtools >/dev/null 2>&1 || { echo "Missing command: samtools" >&2; exit 1; }
command -v gtfToGenePred >/dev/null 2>&1 || { echo "Missing command: gtfToGenePred" >&2; exit 1; }
command -v genePredToBed >/dev/null 2>&1 || { echo "Missing command: genePredToBed" >&2; exit 1; }
if ! command -v sha256sum >/dev/null 2>&1 && ! command -v shasum >/dev/null 2>&1; then
  echo "Missing SHA-256 utility: install sha256sum or shasum" >&2
  exit 1
fi
if [[ "${USE_ANNOTATION_INDEX}" == "yes" ]]; then
  for cmd in hisat2_extract_splice_sites.py hisat2_extract_exons.py; do
    command -v "${cmd}" >/dev/null 2>&1 || { echo "Missing command: ${cmd}" >&2; exit 1; }
  done
fi

[[ -f "${FASTA}" ]] || { echo "FASTA not found: ${FASTA}" >&2; exit 1; }
[[ -f "${GTF}" ]] || { echo "GTF not found: ${GTF}" >&2; exit 1; }

FASTA_ABS="$(cd "$(dirname "${FASTA}")" && pwd)/$(basename "${FASTA}")"
GTF_ABS="$(cd "$(dirname "${GTF}")" && pwd)/$(basename "${GTF}")"
INDEX_PREFIX="${OUTDIR}/hisat2_index/${PREFIX}"

if [[ -e "${OUTDIR}" && ! -d "${OUTDIR}" ]]; then
  echo "OUTDIR exists and is not a directory: ${OUTDIR}" >&2
  exit 1
fi
first_entry=""
if [[ -d "${OUTDIR}" ]]; then
  first_entry=$(find "${OUTDIR}" -mindepth 1 -maxdepth 1 -print -quit)
fi
if [[ -n "${first_entry}" ]]; then
  echo "Refusing to reuse a populated reference directory: ${OUTDIR}" >&2
  echo "Choose a versioned empty directory or inspect the existing reference first." >&2
  exit 1
fi

mkdir -p "${OUTDIR}/hisat2_index"
BUILD_MARKER="${OUTDIR}/.build_incomplete"
touch "${BUILD_MARKER}"
build_complete="no"
trap 'if [[ "${build_complete}" != "yes" ]]; then echo "Reference build did not complete; marker retained at ${BUILD_MARKER}" >&2; fi' EXIT

cp -p "${FASTA_ABS}" "${OUTDIR}/genome.fa"
cp -p "${GTF_ABS}" "${OUTDIR}/genes.gtf"
samtools faidx "${OUTDIR}/genome.fa"

if [[ "${USE_ANNOTATION_INDEX}" == "yes" ]]; then
  hisat2_extract_splice_sites.py "${OUTDIR}/genes.gtf" > "${OUTDIR}/hisat2_index/genome.ss"
  hisat2_extract_exons.py "${OUTDIR}/genes.gtf" > "${OUTDIR}/hisat2_index/genome.exon"

  hisat2-build -p "${THREADS}" \
    --ss "${OUTDIR}/hisat2_index/genome.ss" \
    --exon "${OUTDIR}/hisat2_index/genome.exon" \
    "${OUTDIR}/genome.fa" \
    "${OUTDIR}/hisat2_index/${PREFIX}"
else
  hisat2-build -p "${THREADS}" \
    "${OUTDIR}/genome.fa" \
    "${OUTDIR}/hisat2_index/${PREFIX}"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/gtf_to_bed12.sh" "${OUTDIR}/genes.gtf" "${OUTDIR}/genes.bed12"

sha256_file() {
  local path="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${path}" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "${path}" | awk '{print $1}'
  else
    echo "UNAVAILABLE"
  fi
}

cat > "${OUTDIR}/reference.meta.tsv" <<EOF
key	value
bundle_schema_version	1
reference_id	${REFERENCE_ID}
annotation_id	${ANNOTATION_ID}
fasta_source	${FASTA_ABS}
gtf_source	${GTF_ABS}
fasta_sha256	$(sha256_file "${OUTDIR}/genome.fa")
gtf_sha256	$(sha256_file "${OUTDIR}/genes.gtf")
bed12_sha256	$(sha256_file "${OUTDIR}/genes.bed12")
outdir	${OUTDIR}
threads	${THREADS}
index_prefix	${PREFIX}
annotation_aware_index	${USE_ANNOTATION_INDEX}
hisat2_build_version	$(hisat2-build --version 2>&1 | head -n 1)
samtools_version	$(samtools --version 2>&1 | head -n 1)
build_date	$(date -u '+%Y-%m-%dT%H:%M:%SZ')
EOF

rm -f "${BUILD_MARKER}"
if ! "${SCRIPT_DIR}/check_reference_layout.sh" "${OUTDIR}" "${INDEX_PREFIX}"; then
  touch "${BUILD_MARKER}"
  exit 1
fi

build_complete="yes"
trap - EXIT

echo "Reference prepared under: ${OUTDIR}"
echo "Index prefix: ${OUTDIR}/hisat2_index/${PREFIX}"
