#!/usr/bin/env bash

set -euo pipefail
shopt -s nullglob

usage() {
  cat <<'EOF'
Usage:
  run_bulk_rnaseq_hisat2.sh config.env [--check-only]

Required variables:
  THREADS
  REFERENCE_DIR       Versioned, read-only reference bundle
  REFERENCE_ID
  ANNOTATION_ID
  FASTQ_DIR
  OUTDIR
  HISAT2_STRANDNESS    none | FR | RF
  FEATURECOUNTS_STRAND 0 | 1 | 2
  DO_TRIM              yes | no

Required model variable:
  MODEL_MODE           single_species | same_species_mixture |
                       cross_species_component | custom_combined | spike_in

Optional variables:
  TRIMMOMATIC_ADAPTERS
  INDEX_BASENAME       Default: genome_hisat2_index
  R1_SUFFIX / R2_SUFFIX
  RUN_FASTQC=yes|no
  RUN_MULTIQC=yes|no
  ALLOW_OVERWRITE=yes|no

Unsplit cross-species and host-pathogen FASTQ are intentionally rejected.
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

for var in THREADS REFERENCE_DIR REFERENCE_ID ANNOTATION_ID FASTQ_DIR OUTDIR HISAT2_STRANDNESS FEATURECOUNTS_STRAND DO_TRIM MODEL_MODE; do
  [[ -n "${!var:-}" ]] || { echo "Missing config variable: ${var}" >&2; exit 1; }
done

TRIMMOMATIC_ADAPTERS="${TRIMMOMATIC_ADAPTERS:-}"
INDEX_BASENAME="${INDEX_BASENAME:-genome_hisat2_index}"
R1_SUFFIX="${R1_SUFFIX:-_R1.fastq.gz}"
R2_SUFFIX="${R2_SUFFIX:-_R2.fastq.gz}"
RUN_FASTQC="${RUN_FASTQC:-yes}"
RUN_MULTIQC="${RUN_MULTIQC:-yes}"
ALLOW_OVERWRITE="${ALLOW_OVERWRITE:-no}"

[[ "${THREADS}" =~ ^[1-9][0-9]*$ ]] || { echo "THREADS must be a positive integer" >&2; exit 1; }
[[ "${INDEX_BASENAME}" != */* && -n "${INDEX_BASENAME}" ]] || {
  echo "INDEX_BASENAME must be a basename, not a path" >&2
  exit 1
}
[[ -n "${R1_SUFFIX}" && -n "${R2_SUFFIX}" && "${R1_SUFFIX}" != "${R2_SUFFIX}" ]] || {
  echo "R1_SUFFIX and R2_SUFFIX must be non-empty and different" >&2
  exit 1
}

case "${MODEL_MODE}" in
  single_species|same_species_mixture|cross_species_component|custom_combined|spike_in) ;;
  cross_species)
    echo "Unsplit cross_species FASTQ must run through split_xenograft_xengsort.sh first" >&2
    exit 1
    ;;
  host_pathogen)
    echo "host_pathogen requires a dedicated dual-RNA workflow; this script is not appropriate" >&2
    exit 1
    ;;
  *)
    echo "Invalid MODEL_MODE: ${MODEL_MODE}" >&2
    exit 1
    ;;
esac

case "${HISAT2_STRANDNESS}:${FEATURECOUNTS_STRAND}" in
  none:0|FR:1|RF:2) ;;
  *)
    echo "Inconsistent strandedness: use none/0, FR/1, or RF/2" >&2
    exit 1
    ;;
esac

for value_name in DO_TRIM RUN_FASTQC RUN_MULTIQC ALLOW_OVERWRITE; do
  value="${!value_name}"
  case "${value}" in yes|no) ;; *) echo "${value_name} must be yes or no" >&2; exit 1 ;; esac
done

REFERENCE_DIR="${REFERENCE_DIR%/}"
GTF="${REFERENCE_DIR}/genes.gtf"
INDEX="${REFERENCE_DIR}/hisat2_index/${INDEX_BASENAME}"
REFERENCE_META="${REFERENCE_DIR}/reference.meta.tsv"

[[ -d "${FASTQ_DIR}" ]] || { echo "FASTQ_DIR not found: ${FASTQ_DIR}" >&2; exit 1; }
[[ -d "${REFERENCE_DIR}" ]] || { echo "REFERENCE_DIR not found: ${REFERENCE_DIR}" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/check_reference_layout.sh" "${REFERENCE_DIR}" "${INDEX}"

if [[ -s "${REFERENCE_META}" ]]; then
  meta_reference_id=$(awk -F '\t' '$1 == "reference_id" {print $2; exit}' "${REFERENCE_META}")
  meta_annotation_id=$(awk -F '\t' '$1 == "annotation_id" {print $2; exit}' "${REFERENCE_META}")
  [[ -z "${meta_reference_id}" || "${meta_reference_id}" == "${REFERENCE_ID}" ]] || {
    echo "REFERENCE_ID does not match ${REFERENCE_META}: ${REFERENCE_ID} vs ${meta_reference_id}" >&2
    exit 1
  }
  [[ -z "${meta_annotation_id}" || "${meta_annotation_id}" == "${ANNOTATION_ID}" ]] || {
    echo "ANNOTATION_ID does not match ${REFERENCE_META}: ${ANNOTATION_ID} vs ${meta_annotation_id}" >&2
    exit 1
  }
else
  echo "WARN: reference.meta.tsv is missing; relying on config-provided reference IDs" >&2
fi

for cmd in hisat2 samtools featureCounts; do
  command -v "${cmd}" >/dev/null 2>&1 || { echo "Missing command: ${cmd}" >&2; exit 1; }
done
if [[ "${RUN_FASTQC}" == "yes" ]]; then
  command -v fastqc >/dev/null 2>&1 || { echo "Missing command: fastqc" >&2; exit 1; }
fi
if [[ "${RUN_MULTIQC}" == "yes" ]]; then
  command -v multiqc >/dev/null 2>&1 || { echo "Missing command: multiqc" >&2; exit 1; }
fi
if [[ "${DO_TRIM}" == "yes" ]]; then
  command -v trimmomatic >/dev/null 2>&1 || { echo "Missing command: trimmomatic" >&2; exit 1; }
  [[ -n "${TRIMMOMATIC_ADAPTERS}" ]] || { echo "TRIMMOMATIC_ADAPTERS is required when DO_TRIM=yes" >&2; exit 1; }
  [[ -f "${TRIMMOMATIC_ADAPTERS}" ]] || { echo "Adapter FASTA not found: ${TRIMMOMATIC_ADAPTERS}" >&2; exit 1; }
fi

RAW_R1=( "${FASTQ_DIR}"/*"${R1_SUFFIX}" )
[[ ${#RAW_R1[@]} -gt 0 ]] || {
  echo "No R1 FASTQ matching *${R1_SUFFIX} in ${FASTQ_DIR}" >&2
  exit 1
}

RAW_FASTQ=()
for r1 in "${RAW_R1[@]}"; do
  name=$(basename "${r1}")
  sample=${name%"${R1_SUFFIX}"}
  [[ -n "${sample}" ]] || { echo "Cannot derive sample name from: ${r1}" >&2; exit 1; }
  r2="${FASTQ_DIR}/${sample}${R2_SUFFIX}"
  [[ -f "${r2}" ]] || { echo "Missing pair for ${r1}: ${r2}" >&2; exit 1; }
  RAW_FASTQ+=( "${r1}" "${r2}" )
done

RAW_R2=( "${FASTQ_DIR}"/*"${R2_SUFFIX}" )
for r2 in "${RAW_R2[@]}"; do
  name=$(basename "${r2}")
  sample=${name%"${R2_SUFFIX}"}
  r1="${FASTQ_DIR}/${sample}${R1_SUFFIX}"
  [[ -f "${r1}" ]] || { echo "R2 has no matching R1: ${r2}" >&2; exit 1; }
done

is_current_raw_sample() {
  local target="$1"
  local r1 name sample
  for r1 in "${RAW_R1[@]}"; do
    name=$(basename "${r1}")
    sample=${name%"${R1_SUFFIX}"}
    [[ "${sample}" == "${target}" ]] && return 0
  done
  return 1
}

EXISTING_BAMS=( "${OUTDIR}"/hisat2/*.sorted.bam )
if [[ "${ALLOW_OVERWRITE}" != "yes" ]]; then
  if [[ -e "${OUTDIR}/counts/gene_counts.txt" || ${#EXISTING_BAMS[@]} -gt 0 ]]; then
    echo "Existing alignment/count outputs detected under ${OUTDIR}" >&2
    echo "Use a new OUTDIR, or set ALLOW_OVERWRITE=yes for an intentional rerun." >&2
    exit 1
  fi
else
  for existing_bam in "${EXISTING_BAMS[@]}"; do
    existing_sample=$(basename "${existing_bam}" .sorted.bam)
    if ! is_current_raw_sample "${existing_sample}"; then
      echo "Stale BAM for sample not present in current FASTQ input: ${existing_bam}" >&2
      echo "Use a clean OUTDIR instead of mixing sample sets." >&2
      exit 1
    fi
  done
fi

if [[ "${MODEL_MODE}" == "same_species_mixture" ]]; then
  echo "WARN: same-species bulk cannot assign reads to constituent cell types" >&2
fi

echo "Preflight OK: ${#RAW_R1[@]} samples; model=${MODEL_MODE}; reference=${REFERENCE_ID}; annotation=${ANNOTATION_ID}"
if [[ "${CHECK_ONLY}" == "yes" ]]; then
  exit 0
fi

mkdir -p \
  "${OUTDIR}/fastqc_raw" \
  "${OUTDIR}/trimmed" \
  "${OUTDIR}/fastqc_trimmed" \
  "${OUTDIR}/hisat2" \
  "${OUTDIR}/counts" \
  "${OUTDIR}/multiqc_report" \
  "${OUTDIR}/provenance"

printf 'sample\tr1\tr2\n' > "${OUTDIR}/provenance/sample_manifest.tsv"
for r1 in "${RAW_R1[@]}"; do
  name=$(basename "${r1}")
  sample=${name%"${R1_SUFFIX}"}
  r2="${FASTQ_DIR}/${sample}${R2_SUFFIX}"
  printf '%s\t%s\t%s\n' "${sample}" "${r1}" "${r2}" >> "${OUTDIR}/provenance/sample_manifest.tsv"
done

config_sha256="UNAVAILABLE"
if command -v sha256sum >/dev/null 2>&1; then
  config_sha256=$(sha256sum "${CONFIG}" | awk '{print $1}')
elif command -v shasum >/dev/null 2>&1; then
  config_sha256=$(shasum -a 256 "${CONFIG}" | awk '{print $1}')
fi

reference_meta_sha256="UNAVAILABLE"
if [[ -s "${REFERENCE_META}" ]]; then
  if command -v sha256sum >/dev/null 2>&1; then
    reference_meta_sha256=$(sha256sum "${REFERENCE_META}" | awk '{print $1}')
  elif command -v shasum >/dev/null 2>&1; then
    reference_meta_sha256=$(shasum -a 256 "${REFERENCE_META}" | awk '{print $1}')
  fi
fi

cat > "${OUTDIR}/provenance/run_manifest.tsv" <<EOF
key	value
model_mode	${MODEL_MODE}
reference_id	${REFERENCE_ID}
annotation_id	${ANNOTATION_ID}
reference_dir	${REFERENCE_DIR}
reference_meta	${REFERENCE_META}
reference_meta_sha256	${reference_meta_sha256}
index_prefix	${INDEX}
gtf	${GTF}
fastq_dir	${FASTQ_DIR}
r1_suffix	${R1_SUFFIX}
r2_suffix	${R2_SUFFIX}
sample_count	${#RAW_R1[@]}
hisat2_strandness	${HISAT2_STRANDNESS}
featurecounts_strand	${FEATURECOUNTS_STRAND}
do_trim	${DO_TRIM}
config	${CONFIG}
config_sha256	${config_sha256}
run_date	$(date -u '+%Y-%m-%dT%H:%M:%SZ')
EOF

{
  printf 'tool\tversion\n'
  printf 'hisat2\t%s\n' "$(hisat2 --version 2>&1 | head -n 1)"
  printf 'samtools\t%s\n' "$(samtools --version 2>&1 | head -n 1)"
  printf 'featureCounts\t%s\n' "$(featureCounts -v 2>&1 | head -n 1)"
  if [[ "${RUN_FASTQC}" == "yes" ]]; then
    printf 'fastqc\t%s\n' "$(fastqc --version 2>&1 | head -n 1)"
  fi
  if [[ "${RUN_MULTIQC}" == "yes" ]]; then
    printf 'multiqc\t%s\n' "$(multiqc --version 2>&1 | head -n 1)"
  fi
  if [[ "${DO_TRIM}" == "yes" ]]; then
    printf 'trimmomatic\t%s\n' "$(trimmomatic -version 2>&1 | head -n 1)"
  fi
} > "${OUTDIR}/provenance/tool_versions.tsv"

if [[ "${RUN_FASTQC}" == "yes" ]]; then
  echo "=== 1. FastQC on input FASTQ ==="
  fastqc "${RAW_FASTQ[@]}" -t "${THREADS}" -o "${OUTDIR}/fastqc_raw"
fi

if [[ "${DO_TRIM}" == "yes" ]]; then
  echo "=== 2. Trimmomatic ==="
  for r1 in "${RAW_R1[@]}"; do
    name=$(basename "${r1}")
    sample=${name%"${R1_SUFFIX}"}
    r2="${FASTQ_DIR}/${sample}${R2_SUFFIX}"

    trimmomatic PE -threads "${THREADS}" -phred33 \
      "${r1}" "${r2}" \
      "${OUTDIR}/trimmed/${sample}_R1_paired.fastq.gz" "${OUTDIR}/trimmed/${sample}_R1_unpaired.fastq.gz" \
      "${OUTDIR}/trimmed/${sample}_R2_paired.fastq.gz" "${OUTDIR}/trimmed/${sample}_R2_unpaired.fastq.gz" \
      ILLUMINACLIP:"${TRIMMOMATIC_ADAPTERS}":2:30:10 \
      LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:36
  done

  ALIGN_R1=( "${OUTDIR}"/trimmed/*_R1_paired.fastq.gz )
  ALIGN_R1_SUFFIX="_R1_paired.fastq.gz"
  ALIGN_R2_SUFFIX="_R2_paired.fastq.gz"
  if [[ "${RUN_FASTQC}" == "yes" ]]; then
    TRIMMED_FASTQ=( "${OUTDIR}"/trimmed/*_R1_paired.fastq.gz "${OUTDIR}"/trimmed/*_R2_paired.fastq.gz )
    fastqc "${TRIMMED_FASTQ[@]}" -t "${THREADS}" -o "${OUTDIR}/fastqc_trimmed"
  fi
else
  ALIGN_R1=( "${RAW_R1[@]}" )
  ALIGN_R1_SUFFIX="${R1_SUFFIX}"
  ALIGN_R2_SUFFIX="${R2_SUFFIX}"
fi

echo "=== 3. HISAT2 alignment ==="
BAMS=()
for r1 in "${ALIGN_R1[@]}"; do
  name=$(basename "${r1}")
  sample=${name%"${ALIGN_R1_SUFFIX}"}
  r2="$(dirname "${r1}")/${sample}${ALIGN_R2_SUFFIX}"
  [[ -f "${r2}" ]] || { echo "Missing pair for ${r1}: ${r2}" >&2; exit 1; }
  bam="${OUTDIR}/hisat2/${sample}.sorted.bam"

  hisat_args=( hisat2 -p "${THREADS}" )
  if [[ "${HISAT2_STRANDNESS}" != "none" ]]; then
    hisat_args+=( --rna-strandness "${HISAT2_STRANDNESS}" )
  fi
  hisat_args+=(
    -x "${INDEX}"
    -1 "${r1}"
    -2 "${r2}"
    --new-summary
    --summary-file "${OUTDIR}/hisat2/${sample}.hisat2.log"
  )

  "${hisat_args[@]}" \
    | samtools view -b - \
    | samtools sort -@ "${THREADS}" -o "${bam}" -

  samtools index "${bam}"
  samtools flagstat -@ "${THREADS}" "${bam}" \
    > "${OUTDIR}/hisat2/${sample}.flagstat.txt"
  BAMS+=( "${bam}" )
done

echo "=== 4. featureCounts quantification ==="
featureCounts \
  -T "${THREADS}" \
  -p \
  --countReadPairs \
  -B \
  -C \
  -s "${FEATURECOUNTS_STRAND}" \
  -a "${GTF}" \
  -F GTF \
  -t exon \
  -g gene_id \
  -o "${OUTDIR}/counts/gene_counts.txt" \
  "${BAMS[@]}"

if [[ "${RUN_MULTIQC}" == "yes" ]]; then
  echo "=== 5. MultiQC ==="
  multiqc "${OUTDIR}" -o "${OUTDIR}/multiqc_report" -n multiqc_report
fi

[[ -s "${OUTDIR}/counts/gene_counts.txt" ]] || {
  echo "featureCounts output is missing or empty" >&2
  exit 1
}

echo "Pipeline finished successfully."
echo "Counts: ${OUTDIR}/counts/gene_counts.txt"
echo "Manifest: ${OUTDIR}/provenance/run_manifest.tsv"
if [[ "${RUN_MULTIQC}" == "yes" ]]; then
  echo "Report: ${OUTDIR}/multiqc_report/multiqc_report.html"
fi
