#!/bin/bash
set -e
set -x

docker_ref_vcf="$1"
docker_ref_sdf="$2"
docker_run_gvcf="$3"
docker_ref_bed="$4"
docker_ref_fasta="$5"
docker_out_dir="$6"
docker_logfile="$7"
shift 7  # shift the first 7 positional args so "$@" becomes remaining args (e.g., --stratification ...)

# Image bioconda (pkrusche/hap.py:latest a un manifest Docker v1 retiré).
# Override via HAPPY_IMAGE si une autre image est nécessaire.
HAPPY_IMAGE="${HAPPY_IMAGE:-quay.io/biocontainers/hap.py:0.3.15--py27hcb73b3d_0}"

# Limites ressources — sensibles pour WGS humain entier. Override pour dev/CI
# où la machine est plus petite (ex. HAPPY_MEMORY=8g sur un Mac dev).
HAPPY_CPUS="${HAPPY_CPUS:-6}"
HAPPY_MEMORY="${HAPPY_MEMORY:-48g}"
HAPPY_MEMORY_SWAP="${HAPPY_MEMORY_SWAP:-56g}"

# Plateforme : forcer linux/amd64 sur Apple Silicon (l'image est x86 only).
HAPPY_PLATFORM="${HAPPY_PLATFORM:-linux/amd64}"

# Run hap.py with proper Docker settings
docker run \
    --rm \
    --platform "$HAPPY_PLATFORM" \
    --cpus="$HAPPY_CPUS" \
    --memory="$HAPPY_MEMORY" \
    --memory-swap="$HAPPY_MEMORY_SWAP" \
    -e HGREF="${docker_ref_fasta}" \
    -v "$(pwd):/wgs" \
    "$HAPPY_IMAGE" \
    hap.py \
    "${docker_ref_vcf}" \
    "${docker_run_gvcf}" \
    --engine xcmp \
    --pass-only \
    --logfile "${docker_logfile}" \
    --threads "$HAPPY_CPUS" \
    -f "${docker_ref_bed}" \
    -r "${docker_ref_fasta}" \
    -o "${docker_out_dir}" \
    "$@"  # <- pass remaining args like --stratification if any
