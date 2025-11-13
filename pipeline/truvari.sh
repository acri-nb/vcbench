#!/bin/bash
set -e
set -x

echo "truvari"

docker_ref_vcf="$1"
docker_run_vcf="$2"
docker_ref_bed="$3"
docker_out_dir="$4"

docker run \
    --rm \
    --user "$(id -u):$(id -g)" \
    -v "$(pwd):/wgs" \
    quay.io/biocontainers/truvari:4.0.0--pyhdfd78af_0 \
    truvari bench \
    -b "${docker_ref_vcf}" \
    -c "${docker_run_vcf}" \
    -o "${docker_out_dir}" \
    --includebed "${docker_ref_bed}" \
    --refdist=2000 \
    --pctseq=0.3 \
    --pctsize=0.3 \
    --pctovl=0.0 \
    --passonly \
    --sizemin=50 \
    --sizefilt=30 \
    --sizemax=50000 \
    --pick=ac \
    --chunksize=5000 \
    > ./truvari.log 2>&1
