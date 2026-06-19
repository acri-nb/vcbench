import os
import shutil
import subprocess
from pathlib import Path
import argparse
import logging

from api.app import crud, schemas, settings
from api.app.database import SessionLocal
from api.tasks.parsers import reformat_csv, parse_summary, parse_summary_rows, parse_truvari_summary
from api.tasks import utils
from api.tasks.setup_reference import ensure_references

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = settings.PROJECT_ROOT
LAB_RUN_DIR = settings.LAB_RUNS_DIR
PROCESSED_DIR = settings.PROCESSED_DIR
REFERENCE_DIR = settings.REFERENCE_DIR

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
    # Extract base sample name (e.g., NA24143_Lib3_Rep1 -> NA24143)
    from api.tasks.setup_reference import extract_base_sample, GIAB_SAMPLES
    base_sample = extract_base_sample(sample)
    logger.info(f"Processing hap.py for sample={sample}, base_sample={base_sample}, run={run}")
    
    # Ensure reference files are available before processing
    logger.info(f"Checking reference files for base sample: {base_sample}")
    ready, message = ensure_references(sample, auto_download=True)
    if not ready:
        logger.error(f"Reference files not ready for {base_sample}: {message}")
        raise FileNotFoundError(
            f"Required reference files not found for {base_sample}. {message}\n"
            f"Please ensure reference files are available in: {REFERENCE_DIR}/{base_sample}/"
        )
    logger.info(f"Reference files verified for {base_sample}")
    
    # Paths to working directories
    # Use base_sample for reference directory, full sample for run directory
    ref_dir_path = REFERENCE_DIR / base_sample
    run_dir_path = LAB_RUN_DIR / f"{sample}_{run}"
    
    # Get the reference and run files with specific error messages
    missing_files = []
    
    # Check reference VCF
    ref_vcf_list = list(ref_dir_path.glob('*.vcf.gz'))
    if not ref_vcf_list:
        missing_files.append(f"Reference VCF in {ref_dir_path}")
    else:
        ref_vcf = ref_vcf_list[0]
    
    # Check reference BED
    ref_bed_list = list(ref_dir_path.glob('*.bed'))
    if not ref_bed_list:
        missing_files.append(f"Reference BED in {ref_dir_path}")
    else:
        ref_bed = ref_bed_list[0]
    
    # Check run GVCF
    run_gvcf_list = list(run_dir_path.glob('*.gvcf.gz'))
    if not run_gvcf_list:
        missing_files.append(f"Run GVCF in {run_dir_path}")
    else:
        run_gvcf = run_gvcf_list[0]
    
    # Check reference FASTA
    ref_fasta_list = list(REFERENCE_DIR.glob('*.fasta'))
    if not ref_fasta_list:
        missing_files.append(f"Reference FASTA in {REFERENCE_DIR}")
    else:
        ref_fasta = ref_fasta_list[0]
    
    # Check reference FAI
    ref_fai_list = list(REFERENCE_DIR.glob('*.fasta.fai'))
    if not ref_fai_list:
        missing_files.append(f"Reference FAI in {REFERENCE_DIR}")
    else:
        ref_fai = ref_fai_list[0]
    
    # Check SDF (required for hap.py with RTG Tools)
    # First check if any required files are missing before trying to create SDF
    if missing_files:
        raise FileNotFoundError(
            f"Required files not found in reference or run directories:\n" +
            "\n".join(f"- {f}" for f in missing_files)
        )
    
    # hap.py runs with --engine xcmp (see pipeline/happy.sh), which uses the
    # FASTA reference only and does NOT need an RTG SDF. Resolve an existing SDF
    # if one is present (kept for a possible future vcfeval engine) but never
    # create one: the previous auto-creation pulled the abandoned
    # pkrusche/hap.py:latest image (commit 24aed1c) to build an SDF that
    # happy.sh ignores, failing the whole run on a cold cache for nothing.
    ref_sdf_list = list(REFERENCE_DIR.glob('*.sdf'))
    ref_sdf_name = ref_sdf_list[0].name if ref_sdf_list else "unused.sdf"
    
    # Checksum for the gvcf file (optional - skipped if MD5 file not found)
    try:
        utils.checksum(sample, run)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"GVCF file not found: {e}")
    except ValueError as e:
        raise ValueError(f"Checksum verification failed: {e}")
    except Exception as e:
        logger.warning(f"Checksum verification skipped or failed: {e}")
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
    # Make the truth-set selection auditable and catch the classic
    # "benchmarked against the wrong GIAB truth set" footgun: the truth set is
    # chosen from the run NAME (base_sample), so log the correspondence with the
    # actual VCF sample names and warn loudly if the run VCF's own sample name
    # maps to a *different* known GIAB sample than the one selected.
    logger.info(
        f"hap.py: run VCF sample '{run_sample_name}' (truth VCF sample "
        f"'{ref_sample_name}') -> benchmarking against the GIAB truth set for "
        f"base sample '{base_sample}'"
    )
    embedded = extract_base_sample(run_sample_name) if run_sample_name else base_sample
    if embedded in GIAB_SAMPLES and embedded != base_sample:
        logger.warning(
            f"POSSIBLE TRUTH-SET MISMATCH: run name maps to '{base_sample}' but the "
            f"run VCF sample '{run_sample_name}' maps to '{embedded}'. hap.py will use "
            f"the '{base_sample}' truth set -- verify the run is labelled correctly."
        )
    # Get regions from reference FASTA index
    regions = ",".join(line.split('\t')[0] for line in open(ref_fai))
    
    # Check if GVCF file is already "hard-filtered" (from DRAGEN)
    if 'hard-filtered' in run_gvcf.name:
        logger.info(f"GVCF is already hard-filtered by DRAGEN: {run_gvcf.name}")
        filtered_gvcf = run_gvcf
        
        # Ensure the index exists
        filtered_gvcf_tbi = Path(str(filtered_gvcf) + '.tbi')
        if not filtered_gvcf_tbi.exists():
            logger.info("Creating tabix index for GVCF...")
            tabix_cmd = ['tabix', '-p', 'vcf', str(filtered_gvcf)]
            try:
                subprocess.run(tabix_cmd, check=True)
                logger.info("Tabix index created successfully")
            except Exception as e:
                raise RuntimeError(f"Failed to create tabix index: {e}")
    else:
        # Filter gvcf with bcftools
        filtered_gvcf_name = run_gvcf.name.replace('.gvcf.gz', '.filtered.gvcf.gz')
        filtered_gvcf = run_dir_path / filtered_gvcf_name
        filtered_gvcf_tbi = Path(str(filtered_gvcf) + '.tbi')
        
        # Check if filtered GVCF already exists and is valid
        if filtered_gvcf.exists() and filtered_gvcf_tbi.exists():
            logger.info(f"Filtered GVCF already exists: {filtered_gvcf.name}, skipping filtering step")
        else:
            # Remove old files if they exist but are incomplete
            if filtered_gvcf.exists():
                filtered_gvcf.unlink()
            if filtered_gvcf_tbi.exists():
                filtered_gvcf_tbi.unlink()
            
            # Filter GVCF
            logger.info(f"Filtering GVCF with bcftools to regions: {len(regions.split(','))} chromosomes")
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
                logger.info("GVCF filtering completed successfully")
            except Exception as e:
                raise RuntimeError(f"bcftools failed to filter gvcf: {e}")
    # Prepare Docker-internal paths (use base_sample for reference paths)
    docker_ref_vcf = f'/wgs/data/reference/{base_sample}/{ref_vcf.name}'
    docker_ref_sdf = f'/wgs/data/reference/{ref_sdf_name}'
    docker_run_gvcf = f'/wgs/data/lab_runs/{sample}_{run}/{filtered_gvcf.name}'
    docker_ref_bed = f'/wgs/data/reference/{base_sample}/{ref_bed.name}'
    docker_ref_fasta = f'/wgs/data/reference/{ref_fasta.name}'
    docker_out_dir = f'/wgs/data/processed/{run_dir_name}/{sample}_{run}'
    docker_logfile = f'/wgs/data/processed/{run_dir_name}/happy.{sample}.{run}.log'
    happy_script = PROJECT_ROOT / 'pipeline' / 'happy.sh'
    
    logger.info(f"Running hap.py with reference from {base_sample}")
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
            f'/wgs/data/reference/{base_sample}/GRCh38_strat/GRCh38-all-stratifications.tsv'
        ])
    # Execute the command
    try:
        subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)
        print(f"Successfully processed {run} for reference {sample}.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"hap.py failed for {run} with error: {e}")
    # Store summary data in db
    post_happy_metrics(sample, run, out_dir_path)

def post_happy_metrics(sample, run, out_dir_path):
    # Search for summary file
    summary_file = next(out_dir_path.glob('*.summary.csv'), None)
    if not summary_file:
        raise FileNotFoundError(f"No summary file found in {out_dir_path}")
    # Parse summary file
    print(f"Parsing summary file: {summary_file}")
    # Persist EVERY (Type, Filter) row hap.py emits (SNP/INDEL x ALL/PASS),
    # not just SNP/ALL: the INDEL rows are half the small-variant benchmark and
    # were previously dropped before reaching the database.
    summary_rows = parse_summary_rows(summary_file)
    if not summary_rows:
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
    # Build dict with correct keys and types (one per summary row)
    def _build_metric(row):
        metric_data = {}
        for csv_key, schema_key in key_map.items():
            val = row.get(csv_key)
            if schema_key in ["type", "filter"]:
                metric_data[schema_key] = val
            elif val is None or val == "":
                metric_data[schema_key] = 0
            elif schema_key in [
                "truth_total", "truth_tp", "truth_fn", "query_total", "query_fp", "query_unk"
            ]:
                metric_data[schema_key] = int(float(val))
            else:
                metric_data[schema_key] = float(val)
        metric_data["run_id"] = run_id
        return metric_data
    # Validate and send. Replace any existing rows for this run so a re-run is
    # idempotent instead of accumulating duplicate metric rows.
    try:
        db = SessionLocal()
        try:
            for existing in crud.get_happy_metrics(db, run_id):
                crud.delete_happy_metric(db, existing.id)
            for row in summary_rows:
                validated_metrics = schemas.HappyMetricCreate(**_build_metric(row))
                crud.create_happy_metric(db, validated_metrics)
        finally:
            db.close()
        print(f"Successfully posted {len(summary_rows)} happy metric row(s) for {run_name}.")
    except Exception as e:
        print(f"Validation error: {e}")
        raise
    
def process_truvari(sample, run):
    # Extract base sample name (e.g., NA24143_Lib3_Rep1 -> NA24143)
    from api.tasks.setup_reference import extract_base_sample
    base_sample = extract_base_sample(sample)
    logger.info(f"Processing Truvari for sample={sample}, base_sample={base_sample}, run={run}")
    
    # Ensure reference files are available before processing
    logger.info(f"Checking reference files for Truvari processing: {base_sample}")
    ready, message = ensure_references(sample, auto_download=True)
    if not ready:
        logger.error(f"Reference files not ready for {base_sample}: {message}")
        raise FileNotFoundError(
            f"Required reference files not found for {base_sample}. {message}\n"
            f"Please ensure reference files are available in: {REFERENCE_DIR}/{base_sample}/stvar/"
        )
    logger.info(f"Reference files verified for Truvari: {base_sample}")
    
    # Paths to working directories
    # Use base_sample for reference directory, full sample for run directory
    ref_dir_path = REFERENCE_DIR / base_sample / "stvar"
    run_dir_path = LAB_RUN_DIR / f"{sample}_{run}"
    
    # Get the reference and run files (use base files, not normalized ones)
    try:
        # Get the base truth VCF (not normalized)
        base_ref_vcfs = [f for f in ref_dir_path.glob('*.vcf.gz') if 'normalized' not in f.name and 'filtered' not in f.name]
        if not base_ref_vcfs:
            raise FileNotFoundError("No base reference VCF found")
        ref_vcf = base_ref_vcfs[0]
        
        # Get the base BED file (not normalized)
        base_beds = [f for f in ref_dir_path.glob('*.bed') if 'normalized' not in f.name]
        if not base_beds:
            raise FileNotFoundError("No base BED file found")
        ref_bed = base_beds[0]
        
        run_vcf = next(run_dir_path.glob('*.sv.vcf.gz'))
        ref_fasta = next(REFERENCE_DIR.glob('*.fasta'))
    except StopIteration:
        raise FileNotFoundError("Required files not found in reference or run directories.")
    # Find output directory or create if it doesnt exist
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = None
    # Anchor on the full "_{sample}_{run}" suffix (processed dirs are named
    # "{date}_{sample}_{run}") so a bare run token like "R001" cannot match a
    # *different* sample's directory and silently write this run's Truvari
    # output into it.
    run_suffix = f"_{sample}_{run}"
    for name in os.listdir(PROCESSED_DIR):
        if name.endswith(run_suffix):
            output_path = PROCESSED_DIR / name
            break
    if output_path is None:
        # Create output directory without date prefix
        output_path = PROCESSED_DIR / f"{sample}_{run}"
        output_path.mkdir(parents=True, exist_ok=True)
        print(f"No output path found for {sample}_{run} in {PROCESSED_DIR}.\nCreating directory.")
    # Filter VCFs with bcftools
    filtered_ref_vcf = ref_dir_path / ref_vcf.name.replace('.vcf.gz', '.filtered.vcf.gz')
    normalized_ref_vcf = ref_dir_path / ref_vcf.name.replace('.vcf.gz', '.normalized.vcf.gz')
    filtered_run_vcf = run_dir_path / run_vcf.name.replace('.vcf.gz', '.filtered.vcf.gz')
    
    # Ref VCF filter - add chr prefix to chromosome names
    if not normalized_ref_vcf.exists():
        # First filter out missing variants
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
            raise RuntimeError(f"bcftools failed to filter reference vcf: {e}") from e
            
        # Then normalize chromosome names (add "chr" prefix)
        annotate_cmd = [
            "bcftools", "annotate",
            "--rename-chrs", "/dev/stdin",
            "-Oz",
            "-o", normalized_ref_vcf,
            filtered_ref_vcf
        ]
        # Create chromosome mapping (1->chr1, 2->chr2, etc.)
        chrom_map = "\n".join([f"{i} chr{i}" for i in range(1, 23)] + ["X chrX", "Y chrY"])
        try:
            subprocess.run(annotate_cmd, input=chrom_map.encode(), check=True)
            subprocess.run(['tabix', '-p', 'vcf', normalized_ref_vcf], check=True)
        except Exception as e:
            raise RuntimeError(f"bcftools failed to normalize chromosome names: {e}") from e
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
        raise RuntimeError(f"bcftools failed to filter run vcf: {e}") from e
    # Normalize BED file chromosome names (add chr prefix)
    normalized_bed = ref_dir_path / ref_bed.name.replace('.bed', '.normalized.bed')
    if not normalized_bed.exists():
        try:
            with open(ref_bed, 'r') as f_in, open(normalized_bed, 'w') as f_out:
                for line in f_in:
                    if line.startswith('#'):
                        f_out.write(line)
                    else:
                        fields = line.strip().split('\t')
                        # Add chr prefix if not present
                        if not fields[0].startswith('chr'):
                            fields[0] = f'chr{fields[0]}'
                        f_out.write('\t'.join(fields) + '\n')
        except Exception as e:
            raise RuntimeError(f"Failed to normalize BED file: {e}") from e
    
    # Run Truvari
    # truvari bench refuses to run if its -o directory already exists; remove a
    # stale one so re-processing a run does not abort with a generic
    # "Truvari failed" (e.g. after a previous successful or partial run).
    truvari_out_dir = output_path / 'truvari'
    if truvari_out_dir.exists():
        shutil.rmtree(truvari_out_dir, ignore_errors=True)
    truvari_script = PROJECT_ROOT / 'pipeline' / 'truvari.sh'
    cmd = [
        str(truvari_script),
        to_container(normalized_ref_vcf),  # Use normalized reference VCF
        to_container(filtered_run_vcf),
        to_container(normalized_bed),  # Use normalized BED file
        to_container(truvari_out_dir)
    ]
    try:
        subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)
        print(f"Successfully processed truvari for {sample} {run}")
        
        # Parse and store Truvari metrics
        summary_json = output_path / 'truvari' / 'summary.json'
        if summary_json.exists():
            post_truvari_metrics(sample, run, summary_json)
        else:
            print(f"Warning: Truvari summary.json not found at {summary_json}")
            
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Truvari failed for {sample} {run} with error: {e}")

def post_truvari_metrics(sample, run, summary_json_path):
    """Parse Truvari summary.json and post metrics to API"""
    # Parse summary file
    print(f"Parsing Truvari summary file: {summary_json_path}")
    truvari_metrics = parse_truvari_summary(summary_json_path)
    if not truvari_metrics:
        print("No Truvari metrics found.")
        return
    
    run_name = f"{sample}_{run}"
    run_id = utils.get_run_id(run_name)
    truvari_metrics["run_id"] = run_id
    
    # Validate and send
    try:
        validated_metrics = schemas.TruvariMetricCreate(**truvari_metrics)
        db = SessionLocal()
        try:
            crud.create_truvari_metric(db, validated_metrics)
        finally:
            db.close()
        print(f"Successfully posted Truvari metric for {run_name}.")
    except Exception as e:
        print(f"Validation/posting error: {e}")
        raise

def to_container(p: Path) -> str:
    root = PROJECT_ROOT.resolve()
    return f"/wgs/{p.resolve().relative_to(root).as_posix()}"        

def process_csv_files(run):
    # Paths to input and output directories
    input_dir = LAB_RUN_DIR / run
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = None
    # Find output directory with prefixed date. Anchor on "_{run}" (here `run`
    # is the full "{sample}_{run}") so the match cannot land on another run's dir.
    for name in os.listdir(PROCESSED_DIR):
        if name.endswith(f"_{run}"):
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
        post_qc_metrics(output_file, run)

def post_qc_metrics(output_file, run_name):
    """
    Post a QC metric to the API.
    """
    try:
        id = utils.get_run_id(run_name)
    except Exception as e:
        print(f"Error getting run ID for {run_name}: {e}")
        raise
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
        raise
    try:
        db = SessionLocal()
        try:
            crud.create_qc_metric(db, qc_metric)
        finally:
            db.close()
        print(f"Successfully posted QC metric for {run_name}.")
    except Exception as e:
        print(f"Error posting QC metric for {run_name}: {e}")
        raise


if __name__ == "__main__":
    main()
