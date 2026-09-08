#!/usr/bin/env bash

set -euo pipefail
shopt -s nullglob

usage() {
  cat <<'EOF'
Usage:
  split_xenograft_xengsort.sh config.env [--check-only]

Required variables:
  MODEL_MODE=cross_species
  HOST_LABEL
  GRAFT_LABEL
  HOST_REFERENCE_ID
  GRAFT_REFERENCE_ID
  THREADS
  XENGSORT_INDEX
  FASTQ_DIR
  OUTDIR

Optional variables:
  XENGSORT_MODE=count|coverage|quick
  R1_SUFFIX / R2_SUFFIX
  RUN_FASTQC=yes|no
  RUN_MULTIQC=yes|no
  ALLOW_OVERWRITE=yes|no

This script classifies already accepted FASTQ files. Inspect raw QC first and,
if trimming is required, point FASTQ_DIR at the trimmed paired reads.
EOF
}

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage
  exit 1
fi

CONFIG="$1"
CHECK_ONLY="no"
if [[ $# -eq 2 ]]; then
  [[ "$2" == "--check-only" ]] || { usage; exit 1; }
  CHECK_ONLY="yes"
fi

[[ -f "${CONFIG}" ]] || { echo "Config not found: ${CONFIG}" >&2; exit 1; }
set -a
source "${CONFIG}"
set +a

for var in MODEL_MODE HOST_LABEL GRAFT_LABEL HOST_REFERENCE_ID GRAFT_REFERENCE_ID THREADS XENGSORT_INDEX FASTQ_DIR OUTDIR; do
  [[ -n "${!var:-}" ]] || { echo "Missing config variable: ${var}" >&2; exit 1; }
done

XENGSORT_MODE="${XENGSORT_MODE:-count}"
R1_SUFFIX="${R1_SUFFIX:-_R1.fastq.gz}"
R2_SUFFIX="${R2_SUFFIX:-_R2.fastq.gz}"
RUN_FASTQC="${RUN_FASTQC:-yes}"
RUN_MULTIQC="${RUN_MULTIQC:-yes}"
ALLOW_OVERWRITE="${ALLOW_OVERWRITE:-no}"

[[ "${MODEL_MODE}" == "cross_species" ]] || {
  echo "MODEL_MODE must be cross_species for Xengsort classification" >&2
  exit 1
}
[[ "${THREADS}" =~ ^[1-9][0-9]*$ ]] || { echo "THREADS must be a positive integer" >&2; exit 1; }
[[ -n "${R1_SUFFIX}" && -n "${R2_SUFFIX}" && "${R1_SUFFIX}" != "${R2_SUFFIX}" ]] || {
  echo "R1_SUFFIX and R2_SUFFIX must be non-empty and different" >&2; exit 1;
}
case "${XENGSORT_MODE}" in count|coverage|quick) ;; *) echo "Invalid XENGSORT_MODE: ${XENGSORT_MODE}" >&2; exit 1 ;; esac
case "${RUN_FASTQC}" in yes|no) ;; *) echo "RUN_FASTQC must be yes or no" >&2; exit 1 ;; esac
case "${RUN_MULTIQC}" in yes|no) ;; *) echo "RUN_MULTIQC must be yes or no" >&2; exit 1 ;; esac
case "${ALLOW_OVERWRITE}" in yes|no) ;; *) echo "ALLOW_OVERWRITE must be yes or no" >&2; exit 1 ;; esac

[[ -d "${FASTQ_DIR}" ]] || { echo "FASTQ_DIR not found: ${FASTQ_DIR}" >&2; exit 1; }
[[ -e "${XENGSORT_INDEX}.hash" && -e "${XENGSORT_INDEX}.info" ]] || {
  echo "Xengsort .hash/.info files not found for prefix: ${XENGSORT_INDEX}" >&2
  exit 1
}

command -v xengsort >/dev/null 2>&1 || { echo "Missing command: xengsort" >&2; exit 1; }
command -v gzip >/dev/null 2>&1 || { echo "Missing command: gzip" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Missing command: python3" >&2; exit 1; }
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INDEX_MANIFEST="${XENGSORT_INDEX}.manifest.tsv"
python3 "${SCRIPT_DIR}/verify_reference_fingerprints.py" xengsort "${XENGSORT_INDEX}" \
  --host-label "${HOST_LABEL}" --graft-label "${GRAFT_LABEL}" \
  --host-reference-id "${HOST_REFERENCE_ID}" --graft-reference-id "${GRAFT_REFERENCE_ID}"
if [[ "${RUN_FASTQC}" == "yes" ]]; then
  command -v fastqc >/dev/null 2>&1 || { echo "Missing command: fastqc" >&2; exit 1; }
fi
if [[ "${RUN_MULTIQC}" == "yes" ]]; then
  command -v multiqc >/dev/null 2>&1 || { echo "Missing command: multiqc" >&2; exit 1; }
fi

R1_FILES=( "${FASTQ_DIR}"/*"${R1_SUFFIX}" )
[[ ${#R1_FILES[@]} -gt 0 ]] || {
  echo "No R1 FASTQ matching *${R1_SUFFIX} in ${FASTQ_DIR}" >&2
  exit 1
}

RAW_FASTQ=()
for r1 in "${R1_FILES[@]}"; do
  name=$(basename "${r1}")
  sample=${name%"${R1_SUFFIX}"}
  [[ -n "${sample}" ]] || { echo "Cannot derive sample name from: ${r1}" >&2; exit 1; }
  r2="${FASTQ_DIR}/${sample}${R2_SUFFIX}"
  [[ -f "${r2}" ]] || { echo "Missing pair for ${r1}: ${r2}" >&2; exit 1; }
  RAW_FASTQ+=( "${r1}" "${r2}" )
done

R2_FILES=( "${FASTQ_DIR}"/*"${R2_SUFFIX}" )
for r2 in "${R2_FILES[@]}"; do
  name=$(basename "${r2}")
  sample=${name%"${R2_SUFFIX}"}
  r1="${FASTQ_DIR}/${sample}${R1_SUFFIX}"
  [[ -f "${r1}" ]] || { echo "R2 has no matching R1: ${r2}" >&2; exit 1; }
done

is_current_input_sample() {
  local target="$1"
  local r1 name sample
  for r1 in "${R1_FILES[@]}"; do
    name=$(basename "${r1}")
    sample=${name%"${R1_SUFFIX}"}
    [[ "${sample}" == "${target}" ]] && return 0
  done
  return 1
}

EXISTING_SPLIT_R1=(
  "${OUTDIR}"/species_split/*.host.1.fq.gz
  "${OUTDIR}"/species_split/*.graft.1.fq.gz
  "${OUTDIR}"/species_split/*.both.1.fq.gz
  "${OUTDIR}"/species_split/*.neither.1.fq.gz
  "${OUTDIR}"/species_split/*.ambiguous.1.fq.gz
)
if [[ ${#EXISTING_SPLIT_R1[@]} -gt 0 ]]; then
  if [[ "${ALLOW_OVERWRITE}" != "yes" ]]; then
    echo "Existing split FASTQ detected under ${OUTDIR}; set ALLOW_OVERWRITE=yes only for an intentional rerun" >&2
    exit 1
  fi
  for existing_fastq in "${EXISTING_SPLIT_R1[@]}"; do
    existing_name=$(basename "${existing_fastq}")
    existing_sample=${existing_name%.*.1.fq.gz}
    if ! is_current_input_sample "${existing_sample}"; then
      echo "Stale split FASTQ for sample not present in current input: ${existing_fastq}" >&2
      echo "Use a clean OUTDIR instead of mixing sample sets." >&2
      exit 1
    fi
  done
fi

echo "Preflight OK: ${#R1_FILES[@]} samples; host=${HOST_LABEL}; graft=${GRAFT_LABEL}; mode=${XENGSORT_MODE}"
if [[ "${CHECK_ONLY}" == "yes" ]]; then
  exit 0
fi

mkdir -p "${OUTDIR}/fastqc_input" "${OUTDIR}/species_split" "${OUTDIR}/logs" \
  "${OUTDIR}/qc" "${OUTDIR}/multiqc_report"

printf 'sample\tr1\tr2\n' > "${OUTDIR}/sample_manifest.tsv"
for r1 in "${R1_FILES[@]}"; do
  name=$(basename "${r1}")
  sample=${name%"${R1_SUFFIX}"}
  r2="${FASTQ_DIR}/${sample}${R2_SUFFIX}"
  printf '%s\t%s\t%s\n' "${sample}" "${r1}" "${r2}" >> "${OUTDIR}/sample_manifest.tsv"
done

if [[ "${RUN_FASTQC}" == "yes" ]]; then
  fastqc "${RAW_FASTQ[@]}" -t "${THREADS}" -o "${OUTDIR}/fastqc_input"
fi

for r1 in "${R1_FILES[@]}"; do
  name=$(basename "${r1}")
  sample=${name%"${R1_SUFFIX}"}
  r2="${FASTQ_DIR}/${sample}${R2_SUFFIX}"
  prefix="${OUTDIR}/species_split/${sample}"

  xengsort classify \
    --index "${XENGSORT_INDEX}" \
    --fastq "${r1}" \
    --pairs "${r2}" \
    --prefix "${prefix}" \
    --mode "${XENGSORT_MODE}" \
    -T "${THREADS}" \
    > "${OUTDIR}/logs/${sample}.xengsort.log" 2>&1
done

count_pairs() {
  local fastq="$1"
  local lines
  lines=$(gzip -cd -- "${fastq}" | awk 'END { print NR + 0 }')
  (( lines % 4 == 0 )) || { echo "Malformed FASTQ record count: ${fastq}" >&2; return 1; }
  echo $(( lines / 4 ))
}

printf 'sample\tinput_pairs\thost\tgraft\tboth\tneither\tambiguous\tclassified_total\n' \
  > "${OUTDIR}/qc/species_assignment.tsv"
categories=( host graft both neither ambiguous )
for r1 in "${R1_FILES[@]}"; do
  name=$(basename "${r1}")
  sample=${name%"${R1_SUFFIX}"}
  r2="${FASTQ_DIR}/${sample}${R2_SUFFIX}"
  input_pairs=$(count_pairs "${r1}")
  input_r2_pairs=$(count_pairs "${r2}")
  if [[ "${input_pairs}" -ne "${input_r2_pairs}" ]]; then
    echo "Input R1/R2 record counts differ for ${sample}: ${input_pairs} vs ${input_r2_pairs}" >&2
    exit 1
  fi

  counts=()
  total=0
  for category in "${categories[@]}"; do
    classified_r1="${OUTDIR}/species_split/${sample}.${category}.1.fq.gz"
    classified_r2="${OUTDIR}/species_split/${sample}.${category}.2.fq.gz"
    [[ -f "${classified_r1}" ]] || { echo "Missing Xengsort output: ${classified_r1}" >&2; exit 1; }
    [[ -f "${classified_r2}" ]] || { echo "Missing Xengsort output: ${classified_r2}" >&2; exit 1; }
    value=$(count_pairs "${classified_r1}")
    value_r2=$(count_pairs "${classified_r2}")
    if [[ "${value}" -ne "${value_r2}" ]]; then
      echo "Classified R1/R2 record counts differ for ${sample} ${category}: ${value} vs ${value_r2}" >&2
      exit 1
    fi
    counts+=( "${value}" )
    total=$(( total + value ))
  done

  if [[ "${total}" -ne "${input_pairs}" ]]; then
    echo "Classified total differs from input for ${sample}: ${total} vs ${input_pairs}" >&2
    exit 1
  fi

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "${sample}" "${input_pairs}" "${counts[0]}" "${counts[1]}" \
    "${counts[2]}" "${counts[3]}" "${counts[4]}" "${total}" \
    >> "${OUTDIR}/qc/species_assignment.tsv"
done

awk -F '\t' 'BEGIN { OFS="\t" }
  NR == 1 { print $0, "host_fraction", "graft_fraction", "both_fraction", "neither_fraction", "ambiguous_fraction"; next }
  {
    if ($2 == 0) { print $0, "NA", "NA", "NA", "NA", "NA" }
    else { print $0, $3/$2, $4/$2, $5/$2, $6/$2, $7/$2 }
  }' "${OUTDIR}/qc/species_assignment.tsv" > "${OUTDIR}/qc/species_assignment_with_fractions.tsv"

sha256_file() {
  local path="$1"
  if [[ ! -s "${path}" ]]; then
    echo "UNAVAILABLE"
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${path}" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "${path}" | awk '{print $1}'
  else
    echo "UNAVAILABLE"
  fi
}

cat > "${OUTDIR}/run_manifest.tsv" <<EOF
key	value
model_mode	${MODEL_MODE}
host_label	${HOST_LABEL}
graft_label	${GRAFT_LABEL}
host_reference_id	${HOST_REFERENCE_ID}
graft_reference_id	${GRAFT_REFERENCE_ID}
xengsort_index	${XENGSORT_INDEX}
xengsort_index_manifest	${INDEX_MANIFEST}
xengsort_index_manifest_sha256	$(sha256_file "${INDEX_MANIFEST}")
xengsort_mode	${XENGSORT_MODE}
xengsort_version	$(xengsort --version 2>&1 | head -n 1)
fastq_dir	${FASTQ_DIR}
r1_suffix	${R1_SUFFIX}
r2_suffix	${R2_SUFFIX}
sample_count	${#R1_FILES[@]}
config	${CONFIG}
config_sha256	$(sha256_file "${CONFIG}")
run_date	$(date -u '+%Y-%m-%dT%H:%M:%SZ')
ambiguous_policy	retain_for_qc_exclude_from_primary_counts
EOF

if [[ "${RUN_MULTIQC}" == "yes" ]]; then
  multiqc "${OUTDIR}" -o "${OUTDIR}/multiqc_report" -n multiqc_species_split
fi

echo "Species split completed."
echo "QC: ${OUTDIR}/qc/species_assignment_with_fractions.tsv"
echo "Use *.graft.1/2.fq.gz for the graft reference and *.host.1/2.fq.gz for the host reference."
