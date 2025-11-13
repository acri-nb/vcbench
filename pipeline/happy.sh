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

docker run \
    --cpus=6 \
    --memory=48g \
    --memory-swap=56g \
    -e RTG_MEM=24g \
    -e HGREF=wgs/data/reference/GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta \
    -it \
    -v "$(pwd):/wgs" \
    hap.py \
    /opt/hap.py/bin/hap.py \
    "${docker_ref_vcf}" \
    "${docker_run_gvcf}" \
    --engine xcmp \
    --gender male \
    --convert-gvcf-query \
    --logfile "${docker_logfile}" \
    --threads 6 \
    -f "${docker_ref_bed}" \
    -r wgs/data/reference/GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta \
    -o "${docker_out_dir}" \
    "$@"  # <- pass remaining args like --stratification if any
