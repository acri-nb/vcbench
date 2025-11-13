import os
import subprocess
import requests
from pathlib import Path
import argparse
import subprocess
import logging

from api.app import schemas
from api.tasks.parsers import reformat_csv, parse_summary
from api.tasks import utils
from api.tasks.setup_reference import ensure_references

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LAB_RUN_DIR = PROJECT_ROOT / 'data' / 'lab_runs'
PROCESSED_DIR = PROJECT_ROOT / 'data' / 'processed'
REFERENCE_DIR = PROJECT_ROOT / 'data' / 'reference'

# Main wrapper function to run the processing script
def main():
    args = parse_arguments()
    sample = args.sample
    run = args.run
    run_pipeline(sample, run, args.happy, args.stratified, args.csv_reformat, args.truvari)
        
def run_pipeline(sample, run, happy=False, stratified=False, truvari=False, csv_reformat=False):
    """ Run the processing pipeline for a given sample / run and options. """
    if happy:
        process_happy(sample, run, stratified)
    if truvari:
        process_truvari(sample, run)
    if csv_reformat:
        process_csv_files(f"{sample}_{run}")
        

def parse_arguments():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description="Process a sequencing run.")
    # Required arguments
    parser.add_argument('--sample', required=True, help='Sample name')
    parser.add_argument('--run', required=True, help='Run name')
    # Optional flags
    parser.add_argument('--happy', action='store_true', help='Enable hap.py processing')
    parser.add_argument('--stratified', action='store_true', help='Enable hap.py stratified mode')
    parser.add_argument('--csv-reformat', action='store_true', help='Reformat CSV files')
    parser.add_argument('--truvari', action='store_true', help='Enable truvari processing')
    return parser.parse_args()

def is_processed(sample, run):
    """
    Check if the run has already been processed by looking for run name 
    in the processed directory, ignoring prefixed date.
    """
    path = PROCESSED_DIR / sample
    if not path.exists():
        return False
    for name in os.listdir(path):
        if run in name:
            return True
    return False

def process_happy(sample, run, stratified=False):
    """
    Process hap.py for a given reference and run.
    """
    # Ensure reference files are available before processing
    logger.info(f"Checking reference files for sample: {sample}")
    ready, message = ensure_references(sample, auto_download=True)
    if not ready:
        logger.error(f"Reference files not ready for {sample}: {message}")
        raise FileNotFoundError(
            f"Required reference files not found for {sample}. {message}\n"
            f"Please ensure reference files are available in: {REFERENCE_DIR}/{sample}/"
        )
    logger.info(f"Reference files verified for {sample}")
    
    # Paths to working directories
    ref_dir_path = REFERENCE_DIR / sample
    run_dir_path = LAB_RUN_DIR / f"{sample}_{run}"
    # Get the reference and run files
    try:
        ref_vcf = next(ref_dir_path.glob('*.vcf.gz'))
        ref_sdf = next(REFERENCE_DIR.glob('*.sdf'))
        ref_bed = next(ref_dir_path.glob('*.bed'))
        run_gvcf = next(run_dir_path.glob('*.gvcf.gz'))
        ref_fasta = next(REFERENCE_DIR.glob('*.fasta'))
        ref_fai = next(REFERENCE_DIR.glob('*.fasta.fai'))
    except StopIteration:
        raise FileNotFoundError("Required files not found in reference or run directories.")
    # Checksum for the gvcf file
    try:
        utils.checksum(sample, run)
    except Exception as e:
        raise ValueError(f"Error verifying checksum: {e}")
    # Get gvcf creation date with bcftools to get output path
    try:
        creation_date = utils.get_gvcf_date(run_gvcf)
        run_dir_name = f"{creation_date}_{sample}_{run}"
        out_dir_path = PROCESSED_DIR / run_dir_name
    except Exception as e:
        raise ValueError(f"Error getting file creation date: {run_gvcf}")
    # Create output directory if it doesn't exist
    out_dir_path.mkdir(parents=True, exist_ok=True)
    # Get sample names with bcftools query
    try:
        ref_sample_name = utils.get_sample_name(ref_vcf)
        run_sample_name = utils.get_sample_name(run_gvcf)
    except Exception as e:
        raise ValueError(f"Error getting sample names: {e}")
    # Get regions from reference FASTA index
    regions = ",".join(line.split('\t')[0] for line in open(ref_fai))
    # Filter gvcf with bcftools
    filtered_gvcf_name = run_gvcf.name.replace('.gvcf.gz', '.filtered.gvcf.gz')
    filtered_gvcf = run_dir_path / filtered_gvcf_name
    bcftools_cmd = [
        'bcftools', 'view',
        '--regions', f'{regions}',
        '-O', 'z',
        '-o', f"{filtered_gvcf}",
        f"{run_gvcf}",
    ]
    tabix_cmd = ['tabix', '-p', 'vcf', str(filtered_gvcf)]
    try:
        subprocess.run(bcftools_cmd, check=True)
        subprocess.run(tabix_cmd, check=True)
    except Exception as e:
        raise RuntimeError(f"bcftools failed to filter gvcf: {e}")
    # Prepare Docker-internal paths
    docker_ref_vcf = f'/wgs/data/reference/{sample}/{ref_vcf.name}'
    docker_ref_sdf = f'/wgs/data/reference/{ref_sdf.name}'
    docker_run_gvcf = f'/wgs/data/lab_runs/{sample}_{run}/{filtered_gvcf.name}'
    docker_ref_bed = f'/wgs/data/reference/{sample}/{ref_bed.name}'
    docker_ref_fasta = f'/wgs/data/reference/{ref_fasta.name}'
    docker_out_dir = f'/wgs/data/lab_runs/{sample}_{run}/{sample}_{run}'
    docker_logfile = f'/wgs/data/lab_runs/{sample}_{run}/happy.{sample}.{run}.log'
    happy_script = PROJECT_ROOT / 'pipeline' / 'happy.sh'
    # TODO: Switch to docker compose <--------------------------------------------------------
    cmd = [
        str(happy_script),
        docker_ref_vcf,
        docker_ref_sdf,
        docker_run_gvcf,
        docker_ref_bed,
        docker_ref_fasta,
        docker_out_dir,
        docker_logfile
    ]
    # Add stratification if requested
    if stratified:
        cmd.extend([
            '--stratification',
            f'/wgs/data/reference/{sample}/GRCh38_strat/GRCh38-all-stratifications.tsv'
        ])
    # Execute the command
    try:
        subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)
        print(f"Successfully processed {run} for reference {sample}.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"hap.py failed for {run} with error: {e}")
    # Store summary data in db
    #post_happy_metrics(sample, run, out_dir_path)

def post_happy_metrics(sample, run, out_dir_path):
    # Search for summary file
    summary_file = next(out_dir_path.glob('*.summary.csv'), None)
    if not summary_file:
        raise FileNotFoundError(f"No summary file found in {out_dir_path}")
    # Parse summary file
    print(f"Parsing summary file: {summary_file}") #debug ************
    summary_metrics = parse_summary(summary_file)
    if not summary_metrics:
        print("No summary metrics found.")
        return
    run_name = f"{sample}_{run}"
    run_id = utils.get_run_id(run_name)
    # Map CSV keys to schema keys
    key_map = {
        "Type": "type",
        "Filter": "filter",
        "TRUTH.TOTAL": "truth_total",
        "TRUTH.TP": "truth_tp",
        "TRUTH.FN": "truth_fn",
        "QUERY.TOTAL": "query_total",
        "QUERY.FP": "query_fp",
        "QUERY.UNK": "query_unk",
        "FP.gt": "fp_gt",
        "FP.al": "fp_al",
        "METRIC.Recall": "metric_recall",
        "METRIC.Precision": "metric_precision",
        "METRIC.Frac_NA": "metric_frac_na",
        "METRIC.F1_Score": "metric_f1_score",
        "TRUTH.TOTAL.TiTv_ratio": "truth_titv_ratio",
        "QUERY.TOTAL.TiTv_ratio": "query_titv_ratio",
        "TRUTH.TOTAL.het_hom_ratio": "truth_het_hom_ratio",
        "QUERY.TOTAL.het_hom_ratio": "query_het_hom_ratio",
    }
    # Build dict with correct keys and types
    metric_data = {}
    for csv_key, schema_key in key_map.items():
        val = summary_metrics.get(csv_key)
        if schema_key in ["type", "filter"]:
            metric_data[schema_key] = val
        elif val is None or val == "":
            metric_data[schema_key] = None
        elif schema_key in [
            "truth_total", "truth_tp", "truth_fn", "query_total", "query_fp", "query_unk"
        ]:
            metric_data[schema_key] = int(float(val))
        else:
            metric_data[schema_key] = float(val)
    metric_data["run_id"] = run_id
    # Validate and send
    try:
        print("Validating metric data") #debug ************
        validated_metrics = schemas.HappyMetricCreate(**metric_data)
        print("Posting happy metric") #debug ************
        response = requests.post(
            f"http://localhost:8000/api/v1/runs/{run_name}/happy_metrics",
            json=validated_metrics.model_dump()
        )
        response.raise_for_status()
        print(f"Successfully posted happy metric for {run_name}.")
    except Exception as e:
        print(f"Validation error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print("Response content:", e.response.text)
    
def process_truvari(sample, run):
    # Ensure reference files are available before processing
    logger.info(f"Checking reference files for Truvari processing: {sample}")
    ready, message = ensure_references(sample, auto_download=True)
    if not ready:
        logger.error(f"Reference files not ready for {sample}: {message}")
        raise FileNotFoundError(
            f"Required reference files not found for {sample}. {message}\n"
            f"Please ensure reference files are available in: {REFERENCE_DIR}/{sample}/stvar/"
        )
    logger.info(f"Reference files verified for Truvari: {sample}")
    
    # Paths to working directories
    ref_dir_path = REFERENCE_DIR / sample / "stvar"
    run_dir_path = LAB_RUN_DIR / f"{sample}_{run}"
    # Get the reference and run files
    try:
        ref_vcf = next(ref_dir_path.glob('*.vcf.gz'))
        ref_bed = next(ref_dir_path.glob('*.bed'))
        run_vcf = next(run_dir_path.glob('*.sv.vcf.gz'))
        ref_fasta = next(REFERENCE_DIR.glob('*.fasta'))
    except StopIteration:
        raise FileNotFoundError("Required files not found in reference or run directories.")
    # Find output directory or create if it doesnt exist
    output_path = None
    for name in os.listdir(PROCESSED_DIR):
        if run in name:
            output_path = PROCESSED_DIR / name
            break
    if output_path is None:
        # Create output directory without date prefix
        output_path = PROCESSED_DIR / run
        output_path.mkdir(parents=True, exist_ok=True)
        print(f"No output path found for {run} in {PROCESSED_DIR}.\nCreating directory.")
    # Filter VCFs with bcftools
    filtered_ref_vcf = ref_dir_path / ref_vcf.name.replace('.vcf.gz', '.filtered.vcf.gz')
    filtered_run_vcf = run_dir_path / run_vcf.name.replace('.vcf.gz', '.filtered.vcf.gz')
    # Ref VCF filter
    if not filtered_ref_vcf.exists():
        bcftools_cmd = [
        "bcftools", "view",
        "-e", 'ALT="."',
        "-Oz",
        "-o", filtered_ref_vcf,
        ref_vcf
        ]
        tabix_cmd = ['tabix', '-p', 'vcf', filtered_ref_vcf]
        try:
            subprocess.run(bcftools_cmd, check=True)
            subprocess.run(tabix_cmd, check=True)
        except Exception as e:
            print(f"bcftools failed to filter reference vcf.")
    # Run VCF filter
    bcftools_cmd = [
        "bcftools", "view",
        "-e", 'ALT="<DUP:TANDEM>"',
        "-Oz",
        "-o", filtered_run_vcf,
        run_vcf
    ]
    tabix_cmd = ['tabix', '-p', 'vcf', filtered_run_vcf]
    try:
        subprocess.run(bcftools_cmd, check=True)
        subprocess.run(tabix_cmd, check=True)
    except Exception as e:
        print(f"bcftools failed to filter run vcf.")
    # Run Truvari
    truvari_script = PROJECT_ROOT / 'pipeline' / 'truvari.sh'
    cmd = [
        str(truvari_script),
        to_container(filtered_ref_vcf),
        to_container(filtered_run_vcf),
        to_container(ref_bed),
        to_container(output_path / 'truvari')
    ]
    try:
        subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)
        print("Successfully processed truvari for {sample} {run}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Truvari failed for {sample} {run} with error: {e}")

def to_container(p: Path) -> str:
    root = PROJECT_ROOT.resolve()
    return f"/wgs/{p.resolve().relative_to(root).as_posix()}"        

def process_csv_files(run):
    # Paths to input and output directories
    input_dir = LAB_RUN_DIR / run
    output_path = None
    # Find output directory with prefixed date
    for name in os.listdir(PROCESSED_DIR):
        if run in name:
            output_path = PROCESSED_DIR / name
            break
    if output_path is None:
        # Create output directory without date prefix
        output_path = PROCESSED_DIR / run
        output_path.mkdir(parents=True, exist_ok=True)
        print(f"No output path found for {run} in {PROCESSED_DIR}")
    # Find and reformat all CSV files in the input directory
    csv_files = list(input_dir.glob('*.csv'))
    if not csv_files:
        print(f"No CSV files found in {input_dir}.")
        return
    for csv_file in csv_files:
        output_file = output_path / csv_file.name
        reformat_csv(csv_file, output_file)
        #post_qc_metrics(output_file, f"{sample}_{run}")

def post_qc_metrics(output_file, run_name):
    """
    Post a QC metric to the API.
    """
    try:
        id = utils.get_run_id(run_name)
        url = f"http://localhost:8000/api/v1/qc_metrics/{id}"
    except Exception as e:
        print(f"Error getting run ID for {run_name}: {e}")
        return
    # Create qc metric from schema
    try:
        qc_metric = schemas.QCMetricCreate(
            metric_name=None,
            metric_value=None,
            file_source=output_file.name,
            run_id=id
        )
    except Exception as e:
        print(f"Error creating QC metric for {output_file}: {e}")
        return
    try: 
        response = requests.post(url, json=qc_metric.model_dump())
        response.raise_for_status()
        print(f"Successfully posted QC metric for {run_name}.")
    except requests.RequestException as e:
        print(f"Error posting QC metric for {run_name}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print("Response content:", e.response.text)


if __name__ == "__main__":
    main()