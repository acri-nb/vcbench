import hashlib
import subprocess
import re
import csv
import requests
from pathlib import Path
from datetime import datetime
import subprocess

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LAB_RUN_DIR = PROJECT_ROOT / 'data' / 'lab_runs'
PROCESSED_DIR = PROJECT_ROOT / 'data' / 'processed'
REFERENCE_DIR = PROJECT_ROOT / 'data' / 'reference'

def get_run_id(run_name) -> int:
    """
    Query the FastAPI API to get the run_id for a given run_name.
    Returns the run_id as an integer.
    Raises ValueError if not found.
    """
    url = f"http://localhost:8002/api/v1/runs/by-name/{run_name}"
    response = requests.get(url)
    if response.status_code == 200:
        run_info = response.json()
        return run_info["id"]
    else:
        raise ValueError(f"Run ID not found for run_name: {run_name}")

def checksum(sample, run):
    """
    Verify the MD5 checksum of the gvcf file for a given reference and run.
    Uses the flat directory structure: LAB_RUN_DIR / "{sample}_{run}"
    """
    # Use the flat directory structure
    run_path = LAB_RUN_DIR / f"{sample}_{run}"
    
    # Find the GVCF file (could have different naming patterns)
    gvcf_files = list(run_path.glob('*.gvcf.gz'))
    if not gvcf_files:
        raise FileNotFoundError(f"No GVCF file found in {run_path}")
    
    # Use the first GVCF file found (typically there's only one)
    gvcf_path = gvcf_files[0]
    
    # Check for MD5 checksum file (optional - skip if not present)
    md5_path = run_path / f"{gvcf_path.name}.md5sum"
    if not md5_path.exists():
        # Also try alternative MD5 naming patterns
        md5_alt1 = run_path / f"{gvcf_path.name}.md5"
        md5_alt2 = run_path / f"{gvcf_path.stem}.md5sum"
        if md5_alt1.exists():
            md5_path = md5_alt1
        elif md5_alt2.exists():
            md5_path = md5_alt2
        else:
            # MD5 file not found - skip checksum verification
            print(f"Warning: MD5 checksum file not found for {gvcf_path.name}. Skipping checksum verification.")
            return
    
    # Read the MD5 checksum
    with open(md5_path, 'r') as f:
        md5_content = f.read().strip()
        # Handle different MD5 file formats (MD5 hash only, or "hash filename")
        expected_md5 = md5_content.split()[0] if md5_content else md5_content
    
    # Calculate the MD5 checksum of the gvcf file
    with open(gvcf_path, 'rb') as f:
        file_md5 = hashlib.md5(f.read()).hexdigest()
    
    # Compare the checksums
    if file_md5 != expected_md5:
        raise ValueError(f"MD5 checksum mismatch for {gvcf_path.name}. Expected: {expected_md5}, Got: {file_md5}")

def get_gvcf_date(run_gvcf) -> str:
    """
    Get creation date of a gvcf file 
    """
    cmd = ['bcftools', 'view', '-h', run_gvcf]
    try:
        result = subprocess.run(cmd, capture_output=True, check=True, text=True)
    except subprocess.CalledProcessError as e:
        print("bcftools failed to get date: ", e.stderr)
    # Search for the DRAGENCommandLine header line
    for line in result.stdout.splitlines():
        if "##DRAGENCommandLine=" in line:
            match = re.search(r'Date="([^"]+)"', line)
            if match:
                try:
                    date = str(parse_dragen_date(match.group(1)))
                    return date
                except ValueError as e:
                    raise ValueError("Failed to get date from gvcf: ", e.stderr)
    raise ValueError("Missing date from gvcf")

def parse_dragen_date(date):
    """
    Parse the date from the DRAGENCommandLine header.
    """
    try:
        date = datetime.strptime(date, "%a %b %d %H:%M:%S %Z %Y")
        return date.strftime("%Y%m%d")
    except Exception as e:
        raise ValueError(f"Failed to parse date: {str(e)}")
    
def get_sample_name(vcf_file):
    """
    Get the sample name from a VCF file using bcftools query.
    """
    cmd = ['bcftools', 'query', '-l', str(vcf_file)]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get sample name from {vcf_file}: {e}")

def get_metric(run_name: str, metric_name: str):
    """
    Get the processed run directory for a given sample and run name.
    """
    pattern = f"*_{run_name}"
    matching_dirs = list(PROCESSED_DIR.glob(pattern))
    if not matching_dirs:
        raise FileNotFoundError(f"Processed run not found.")
    if len(matching_dirs) > 1:
        print(f"Warning: Multiple directories found for {run_name}.")
    run = matching_dirs[0]
    for metric_file in run.iterdir():
        if metric_file.is_file() and metric_name in metric_file.name:
            # Read csv into a dict
            with open(metric_file, 'r') as f:
                reader = csv.DictReader(f)
                metric_list = [row for row in reader]
                if len(metric_list) >= 1:
                    return metric_list[0]
    raise FileNotFoundError(f"Metric file not found: {metric_name}")