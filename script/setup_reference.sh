#!/bin/bash

set -euo pipefail

# ==============================================================================
# Script: setup_reference.sh
# Description: Automatically download and setup reference files for a given sample
# Usage: ./setup_reference.sh <sample_name> [--check-only]
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REFERENCE_DIR="${PROJECT_DIR}/data/reference"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration file for known samples
CONFIG_FILE="${SCRIPT_DIR}/reference_config.json"

# Parse arguments
SAMPLE_NAME="${1:-}"
CHECK_ONLY=false
if [[ "${2:-}" == "--check-only" ]]; then
    CHECK_ONLY=true
fi

# ==============================================================================
# Functions
# ==============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Extract base sample name (remove suffixes like _Lib3_Rep1)
extract_base_sample() {
    local full_name="$1"
    
    # Known GIAB samples mapping
    case "$full_name" in
        NA12878*|HG001*)
            echo "NA12878"
            ;;
        NA24385*|HG002*)
            echo "NA24385"
            ;;
        NA24149*|HG003*)
            echo "NA24149"
            ;;
        NA24143*|HG004*)
            echo "NA24143"
            ;;
        NA24631*|HG005*)
            echo "NA24631"
            ;;
        NA24694*|HG006*)
            echo "NA24694"
            ;;
        NA24695*|HG007*)
            echo "NA24695"
            ;;
        *)
            # Return the first part before underscore or the full name
            echo "${full_name%%_*}"
            ;;
    esac
}

# Get GIAB identifiers for known samples
get_giab_id() {
    local sample="$1"
    case "$sample" in
        NA12878|HG001) echo "HG001" ;;
        NA24385|HG002) echo "HG002" ;;
        NA24149|HG003) echo "HG003" ;;
        NA24143|HG004) echo "HG004" ;;
        NA24631|HG005) echo "HG005" ;;
        NA24694|HG006) echo "HG006" ;;
        NA24695|HG007) echo "HG007" ;;
        *) echo "" ;;
    esac
}

# Check if sample is a known GIAB sample
is_giab_sample() {
    local sample="$1"
    local giab_id=$(get_giab_id "$sample")
    [[ -n "$giab_id" ]]
}

# Check if genome reference files exist
check_genome_reference() {
    local fasta="${REFERENCE_DIR}/GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta"
    local fai="${fasta}.fai"
    local sdf="${REFERENCE_DIR}/GRCh38.sdf"
    
    local missing=()
    [[ ! -f "$fasta" ]] && missing+=("FASTA")
    [[ ! -f "$fai" ]] && missing+=("FAI")
    [[ ! -d "$sdf" ]] && missing+=("SDF")
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_warning "Missing genome reference files: ${missing[*]}"
        return 1
    fi
    
    log_success "Genome reference files exist"
    return 0
}

# Check if sample reference files exist
check_sample_reference() {
    local sample="$1"
    local sample_dir="${REFERENCE_DIR}/${sample}"
    
    local missing=()
    [[ ! -d "$sample_dir" ]] && missing+=("Sample directory")
    
    # Check for VCF files using a different approach
    if ! compgen -G "$sample_dir/*.vcf.gz" > /dev/null 2>&1; then
        missing+=("Truth VCF")
    fi
    
    # Check for BED files
    if ! compgen -G "$sample_dir/*.bed" > /dev/null 2>&1; then
        missing+=("Confident regions BED")
    fi
    
    # Check for structural variants (optional but recommended)
    if [[ ! -d "$sample_dir/stvar" ]] || \
       ! compgen -G "$sample_dir/stvar/*.vcf.gz" > /dev/null 2>&1 || \
       ! compgen -G "$sample_dir/stvar/*.bed" > /dev/null 2>&1; then
        missing+=("SV reference files")
    fi
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_warning "Missing sample reference files for ${sample}: ${missing[*]}"
        return 1
    fi
    
    log_success "Sample reference files exist for ${sample}"
    return 0
}

# Download genome reference
download_genome_reference() {
    log_info "Downloading GRCh38 genome reference..."
    
    mkdir -p "${REFERENCE_DIR}"
    cd "${REFERENCE_DIR}"
    
    local fasta="GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta"
    
    # Download FASTA if missing
    if [[ ! -f "$fasta" ]]; then
        log_info "Downloading FASTA file..."
        wget -q --show-progress \
            "https://ftp.ncbi.nlm.nih.gov/genomes/all/GCA/000/001/405/GCA_000001405.15_GRCh38/seqs_for_alignment_pipelines.ucsc_ids/GCA_000001405.15_GRCh38_no_alt_analysis_set.fna.gz"
        
        log_info "Extracting FASTA..."
        gunzip GCA_000001405.15_GRCh38_no_alt_analysis_set.fna.gz
        mv GCA_000001405.15_GRCh38_no_alt_analysis_set.fna "$fasta"
    fi
    
    # Generate FAI index if missing
    if [[ ! -f "${fasta}.fai" ]]; then
        log_info "Generating FASTA index..."
        if command -v samtools &> /dev/null; then
            samtools faidx "$fasta"
        else
            log_error "samtools not found. Please install samtools to generate FAI index."
            return 1
        fi
    fi
    
    # Generate SDF format if missing
    if [[ ! -d "GRCh38.sdf" ]]; then
        log_info "Generating SDF format for RTG Tools..."
        if command -v rtg &> /dev/null; then
            rtg format -o GRCh38.sdf "$fasta"
        else
            log_warning "RTG Tools not found. SDF format not generated. hap.py may fail."
            log_warning "Please install RTG Tools or use Docker container."
        fi
    fi
    
    log_success "Genome reference setup complete"
    return 0
}

# Download GIAB sample reference
download_giab_reference() {
    local sample="$1"
    local giab_id=$(get_giab_id "$sample")
    
    if [[ -z "$giab_id" ]]; then
        log_error "Not a known GIAB sample: ${sample}"
        return 1
    fi
    
    log_info "Downloading GIAB reference for ${sample} (${giab_id})..."
    
    local sample_dir="${REFERENCE_DIR}/${sample}"
    mkdir -p "${sample_dir}/stvar"
    mkdir -p "${sample_dir}/GRCh38_strat"
    
    cd "${sample_dir}"
    
    # Determine the latest version URLs based on GIAB ID
    local release_url="https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/giab/release"
    
    # Download small variants truth set
    log_info "Downloading small variants truth set..."
    case "$giab_id" in
        HG001)
            wget -O "${sample}_truth.vcf.gz" \
                "${release_url}/NA12878_HG001/NISTv4.2.1/GRCh38/HG001_GRCh38_1_22_v4.2.1_benchmark.vcf.gz" || true
            wget -O "${sample}_confident_regions.bed" \
                "${release_url}/NA12878_HG001/NISTv4.2.1/GRCh38/HG001_GRCh38_1_22_v4.2.1_benchmark_noinconsistent.bed" || true
            ;;
        HG002)
            wget -O "${sample}_truth.vcf.gz" \
                "${release_url}/AshkenazimTrio/HG002_NA24385_son/NISTv4.2.1/GRCh38/HG002_GRCh38_1_22_v4.2.1_benchmark.vcf.gz" || true
            wget -O "${sample}_confident_regions.bed" \
                "${release_url}/AshkenazimTrio/HG002_NA24385_son/NISTv4.2.1/GRCh38/HG002_GRCh38_1_22_v4.2.1_benchmark_noinconsistent.bed" || true
            ;;
        HG003)
            wget -O "${sample}_truth.vcf.gz" \
                "${release_url}/AshkenazimTrio/HG003_NA24149_father/NISTv4.2.1/GRCh38/HG003_GRCh38_1_22_v4.2.1_benchmark.vcf.gz" || true
            wget -O "${sample}_confident_regions.bed" \
                "${release_url}/AshkenazimTrio/HG003_NA24149_father/NISTv4.2.1/GRCh38/HG003_GRCh38_1_22_v4.2.1_benchmark_noinconsistent.bed" || true
            ;;
        HG004)
            wget -O "${sample}_truth.vcf.gz" \
                "${release_url}/AshkenazimTrio/HG004_NA24143_mother/NISTv4.2.1/GRCh38/HG004_GRCh38_1_22_v4.2.1_benchmark.vcf.gz" || true
            wget -O "${sample}_confident_regions.bed" \
                "${release_url}/AshkenazimTrio/HG004_NA24143_mother/NISTv4.2.1/GRCh38/HG004_GRCh38_1_22_v4.2.1_benchmark_noinconsistent.bed" || true
            ;;
        HG005|HG006|HG007)
            log_warning "GIAB truth sets for ${giab_id} may have different versions. Please check GIAB FTP."
            ;;
    esac
    
    # Download structural variants (if available)
    log_info "Downloading structural variants truth set..."
    cd "${sample_dir}/stvar"
    
    case "$giab_id" in
        HG002|HG003|HG004)
            wget -O "${sample}_sv_truth.vcf.gz" \
                "${base_url}/AshkenazimTrio/analysis/NIST_SVs_Integration_v0.6/${giab_id}_GRCh38_CMRG_SV_v1.00.vcf.gz" || true
            wget -O "${sample}_sv_confident_regions.bed" \
                "${base_url}/AshkenazimTrio/analysis/NIST_SVs_Integration_v0.6/${giab_id}_GRCh38_CMRG_SV_v1.00.bed" || true
            ;;
    esac
    
    # Index VCF files
    log_info "Indexing VCF files..."
    cd "${sample_dir}"
    for vcf in *.vcf.gz; do
        if [[ -f "$vcf" ]] && [[ ! -f "${vcf}.tbi" ]]; then
            if command -v tabix &> /dev/null; then
                tabix -p vcf "$vcf"
            else
                log_warning "tabix not found. VCF files not indexed."
            fi
        fi
    done
    
    cd "${sample_dir}/stvar"
    for vcf in *.vcf.gz; do
        if [[ -f "$vcf" ]] && [[ ! -f "${vcf}.tbi" ]]; then
            if command -v tabix &> /dev/null; then
                tabix -p vcf "$vcf"
            else
                log_warning "tabix not found. VCF files not indexed."
            fi
        fi
    done
    
    log_success "GIAB reference downloaded for ${sample}"
    return 0
}

# ==============================================================================
# Main Logic
# ==============================================================================

main() {
    if [[ -z "$SAMPLE_NAME" ]]; then
        log_error "Usage: $0 <sample_name> [--check-only]"
        exit 1
    fi
    
    log_info "Processing sample: ${SAMPLE_NAME}"
    
    # Extract base sample name
    BASE_SAMPLE=$(extract_base_sample "$SAMPLE_NAME")
    log_info "Base sample identified: ${BASE_SAMPLE}"
    
    # Create reference directory if it doesn't exist
    mkdir -p "${REFERENCE_DIR}"
    
    # Check genome reference
    if ! check_genome_reference; then
        if [[ "$CHECK_ONLY" == true ]]; then
            log_error "Genome reference missing (check-only mode)"
            exit 1
        fi
        download_genome_reference
    fi
    
    # Check if this is a known GIAB sample
    if is_giab_sample "$BASE_SAMPLE"; then
        log_info "${BASE_SAMPLE} is a known GIAB sample"
        
        # Check sample reference
        if ! check_sample_reference "$BASE_SAMPLE"; then
            if [[ "$CHECK_ONLY" == true ]]; then
                log_error "Sample reference missing (check-only mode)"
                exit 1
            fi
            download_giab_reference "$BASE_SAMPLE"
        fi
    else
        log_warning "${BASE_SAMPLE} is not a known GIAB sample"
        log_warning "Please manually provide reference files in: ${REFERENCE_DIR}/${BASE_SAMPLE}/"
        log_warning "Required files:"
        log_warning "  - ${BASE_SAMPLE}_truth.vcf.gz"
        log_warning "  - ${BASE_SAMPLE}_confident_regions.bed"
        log_warning "  - stvar/${BASE_SAMPLE}_sv_truth.vcf.gz (optional)"
        log_warning "  - stvar/${BASE_SAMPLE}_sv_confident_regions.bed (optional)"
        
        if [[ "$CHECK_ONLY" == false ]]; then
            mkdir -p "${REFERENCE_DIR}/${BASE_SAMPLE}/stvar"
            log_info "Created directory structure for manual reference files"
        fi
        
        exit 2  # Exit code 2 = unknown sample
    fi
    
    log_success "Reference setup complete for ${SAMPLE_NAME}"
}

# Run main
main

