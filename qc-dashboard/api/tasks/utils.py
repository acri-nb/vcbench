import hashlib
import re
import csv
from pathlib import Path
from datetime import datetime
import subprocess

from api.app import crud
from api.app.database import SessionLocal
from api.app import settings

PROJECT_ROOT = settings.PROJECT_ROOT
LAB_RUN_DIR = settings.LAB_RUNS_DIR
PROCESSED_DIR = settings.PROCESSED_DIR
REFERENCE_DIR = settings.REFERENCE_DIR

def get_run_id(run_name) -> int:
    """
    Query the FastAPI API to get the run_id for a given run_name.
    Returns the run_id as an integer.
    Raises ValueError if not found.
    """
    db = SessionLocal()
    try:
        run = crud.get_lab_run_by_name(db, run_name)
        if run:
            return run.id
        raise ValueError(f"Run ID not found for run_name: {run_name}")
    finally:
        db.close()

def checksum(sample, run):
    """
    Verify the MD5 checksum of the gvcf file for a given reference and run.
    """
    run_path = LAB_RUN_DIR / f"{sample}_{run}"
    gvcf_files = list(run_path.glob("*.gvcf.gz"))
    if not gvcf_files:
        raise FileNotFoundError(f"No GVCF file found in {run_path}")

    gvcf_path = gvcf_files[0]
    md5_candidates = [
        run_path / f"{gvcf_path.name}.md5sum",
        run_path / f"{gvcf_path.name}.md5",
        run_path / f"{gvcf_path.stem}.md5sum",
    ]
    md5_path = next((path for path in md5_candidates if path.exists()), None)
    if md5_path is None:
        print(f"Warning: MD5 checksum file not found for {gvcf_path.name}. Skipping checksum verification.")
        return

    with open(md5_path, 'r') as f:
        expected_md5 = f.read().strip().split()[0]

    digest = hashlib.md5()
    with open(gvcf_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    file_md5 = digest.hexdigest()
    if file_md5 != expected_md5:
        raise ValueError(f"MD5 checksum mismatch for {gvcf_path.name}. Expected: {expected_md5}, Got: {file_md5}")


def split_run_name(run_name: str) -> tuple[str, str]:
    """Split sample/run names like NA24143_Lib3_Rep1_R001 into sample and run."""
    parts = run_name.split("_")
    if len(parts) < 2:
        raise ValueError(f"Invalid run name format: {run_name}")

    for index in range(len(parts) - 1, -1, -1):
        part = parts[index]
        if part.startswith("R") and part[1:].isdigit():
            sample = "_".join(parts[:index])
            run = "_".join(parts[index:])
            if sample and run:
                return sample, run

    return "_".join(parts[:-1]), parts[-1]

def get_gvcf_date(run_gvcf) -> str:
    """
    Get creation date of a gvcf file 
    """
    cmd = ['bcftools', 'view', '-h', run_gvcf]
    try:
        result = subprocess.run(cmd, capture_output=True, check=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"bcftools failed to get date: {e.stderr}") from e
    # Search for the DRAGENCommandLine header line
    for line in result.stdout.splitlines():
        if "##DRAGENCommandLine=" in line:
            match = re.search(r'Date="([^"]+)"', line)
            if match:
                try:
                    date = str(parse_dragen_date(match.group(1)))
                    return date
                except ValueError as e:
                    raise ValueError(f"Failed to get date from gvcf: {e}")
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
