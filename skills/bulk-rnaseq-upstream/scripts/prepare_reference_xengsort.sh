#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  prepare_reference_xengsort.sh \
    --host-fasta mouse.genome.fa \
    [--host-fasta mouse.transcriptome.fa] \
    --graft-fasta human.genome.fa \
    [--graft-fasta human.transcriptome.fa] \
    --host-label mouse --graft-label human \
    --host-reference-id GRCm39 --graft-reference-id GRCh38 \
    --index-prefix /path/to/shared/rnaseq_refs/human_mouse/xengsort/human_mouse \
    --nobjects 4500000000 \
    [--threads 8]

Both --host-fasta and --graft-fasta are repeatable. For RNA-seq, Xengsort's
official example includes genome and transcriptome FASTA for each species.
The default hash functions are fixed for reproducible index construction.
Estimate --nobjects for the actual reference pair; 4.5 billion is only a
human-mouse starting point, not a universal value.
EOF
}

HOST_FASTAS=()
GRAFT_FASTAS=()
INDEX_PREFIX=""
NOBJECTS=""
THREADS=8
HOST_LABEL=""
GRAFT_LABEL=""
HOST_REFERENCE_ID=""
GRAFT_REFERENCE_ID=""
HASHFUNCTIONS="linear945:linear9123641:linear349341847"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host-fasta|--graft-fasta|--index-prefix|--nobjects|--threads|--host-label|--graft-label|--host-reference-id|--graft-reference-id)
      option="$1"
      [[ $# -ge 2 && -n "${2:-}" && "${2}" != --* ]] || {
        echo "Missing value for ${option}" >&2
        usage
        exit 1
      }
      case "${option}" in
        --host-fasta) HOST_FASTAS+=( "$2" ) ;;
        --graft-fasta) GRAFT_FASTAS+=( "$2" ) ;;
        --index-prefix) INDEX_PREFIX="$2" ;;
        --nobjects) NOBJECTS="$2" ;;
        --threads) THREADS="$2" ;;
        --host-label) HOST_LABEL="$2" ;;
        --graft-label) GRAFT_LABEL="$2" ;;
        --host-reference-id) HOST_REFERENCE_ID="$2" ;;
        --graft-reference-id) GRAFT_REFERENCE_ID="$2" ;;
      esac
      shift 2
      ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

[[ ${#HOST_FASTAS[@]} -gt 0 ]] || { echo "At least one --host-fasta is required" >&2; usage; exit 1; }
[[ ${#GRAFT_FASTAS[@]} -gt 0 ]] || { echo "At least one --graft-fasta is required" >&2; usage; exit 1; }
[[ -n "${INDEX_PREFIX}" ]] || { echo "Missing required option: --index-prefix" >&2; usage; exit 1; }
[[ -n "${NOBJECTS}" ]] || { echo "Missing required option: --nobjects" >&2; usage; exit 1; }
for variable in HOST_LABEL GRAFT_LABEL HOST_REFERENCE_ID GRAFT_REFERENCE_ID; do
  [[ -n "${!variable}" && "${!variable}" != *$'\t'* && "${!variable}" != *$'\n'* && "${!variable}" != *$'\r'* ]] || {
    echo "Missing or invalid identity: ${variable}" >&2; exit 1;
  }
done
[[ "${HOST_LABEL}" != "${GRAFT_LABEL}" ]] || { echo "Host and graft labels must be distinct" >&2; exit 1; }

[[ "${THREADS}" =~ ^[1-9][0-9]*$ ]] || { echo "--threads must be a positive integer" >&2; exit 1; }
[[ "${NOBJECTS}" =~ ^[1-9][0-9]*$ ]] || { echo "--nobjects must be a positive integer" >&2; exit 1; }
HOST_FASTAS_ABS=()
for fasta in "${HOST_FASTAS[@]}"; do
  [[ -f "${fasta}" ]] || { echo "Host FASTA not found: ${fasta}" >&2; exit 1; }
  HOST_FASTAS_ABS+=( "$(cd "$(dirname "${fasta}")" && pwd)/$(basename "${fasta}")" )
done
GRAFT_FASTAS_ABS=()
for fasta in "${GRAFT_FASTAS[@]}"; do
  [[ -f "${fasta}" ]] || { echo "Graft FASTA not found: ${fasta}" >&2; exit 1; }
  GRAFT_FASTAS_ABS+=( "$(cd "$(dirname "${fasta}")" && pwd)/$(basename "${fasta}")" )
done
HOST_FASTAS=( "${HOST_FASTAS_ABS[@]}" )
GRAFT_FASTAS=( "${GRAFT_FASTAS_ABS[@]}" )
command -v xengsort >/dev/null 2>&1 || { echo "Missing command: xengsort" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Missing command: python3" >&2; exit 1; }
if ! command -v sha256sum >/dev/null 2>&1 && ! command -v shasum >/dev/null 2>&1; then
  echo "Missing SHA-256 utility: sha256sum or shasum is required" >&2; exit 1;
fi

if [[ -e "${INDEX_PREFIX}.hash" || -e "${INDEX_PREFIX}.info" || -e "${INDEX_PREFIX}.manifest.tsv" ]]; then
  echo "Refusing to overwrite existing Xengsort index: ${INDEX_PREFIX}" >&2
  exit 1
fi

mkdir -p "$(dirname "${INDEX_PREFIX}")"

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

xengsort index \
  --index "${INDEX_PREFIX}" \
  -H "${HOST_FASTAS[@]}" \
  -G "${GRAFT_FASTAS[@]}" \
  -n "${NOBJECTS}" \
  -W "${THREADS}" \
  --hashfunctions "${HASHFUNCTIONS}"

[[ -e "${INDEX_PREFIX}.hash" && -e "${INDEX_PREFIX}.info" ]] || {
  echo "Xengsort finished without the expected .hash/.info files" >&2
  exit 1
}

{
  printf 'key\tvalue\n'
  printf 'bundle_schema_version\t2\n'
  printf 'host_label\t%s\n' "${HOST_LABEL}"
  printf 'graft_label\t%s\n' "${GRAFT_LABEL}"
  printf 'host_reference_id\t%s\n' "${HOST_REFERENCE_ID}"
  printf 'graft_reference_id\t%s\n' "${GRAFT_REFERENCE_ID}"
  printf 'host_fasta_count\t%s\n' "${#HOST_FASTAS[@]}"
  printf 'graft_fasta_count\t%s\n' "${#GRAFT_FASTAS[@]}"
  for i in "${!HOST_FASTAS[@]}"; do
    printf 'host_fasta_%s\t%s\n' "$(( i + 1 ))" "${HOST_FASTAS[${i}]}"
    printf 'host_fasta_%s_sha256\t%s\n' "$(( i + 1 ))" "$(sha256_file "${HOST_FASTAS[${i}]}")"
  done
  for i in "${!GRAFT_FASTAS[@]}"; do
    printf 'graft_fasta_%s\t%s\n' "$(( i + 1 ))" "${GRAFT_FASTAS[${i}]}"
    printf 'graft_fasta_%s_sha256\t%s\n' "$(( i + 1 ))" "$(sha256_file "${GRAFT_FASTAS[${i}]}")"
  done
  printf 'nobjects\t%s\n' "${NOBJECTS}"
  printf 'threads\t%s\n' "${THREADS}"
  printf 'hashfunctions\t%s\n' "${HASHFUNCTIONS}"
  printf 'xengsort_version\t%s\n' "$(xengsort --version 2>&1 | head -n 1)"
  printf 'build_date\t%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  printf 'index_hash_sha256\t%s\n' "$(sha256_file "${INDEX_PREFIX}.hash")"
  printf 'index_info_sha256\t%s\n' "$(sha256_file "${INDEX_PREFIX}.info")"
} > "${INDEX_PREFIX}.manifest.tsv"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "${SCRIPT_DIR}/verify_reference_fingerprints.py" xengsort "${INDEX_PREFIX}" \
  --host-label "${HOST_LABEL}" --graft-label "${GRAFT_LABEL}" \
  --host-reference-id "${HOST_REFERENCE_ID}" --graft-reference-id "${GRAFT_REFERENCE_ID}"

echo "Xengsort index prepared: ${INDEX_PREFIX}"
