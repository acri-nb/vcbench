"""
Module for managing reference genome and truth set files.

This module handles:
- Detection of missing reference files
- Automatic download of GIAB reference data
- Validation of reference file structure
"""

import subprocess
from pathlib import Path
from typing import Tuple, Optional, Dict, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
REFERENCE_DIR = PROJECT_ROOT / 'data' / 'reference'
SETUP_SCRIPT = PROJECT_ROOT / 'script' / 'setup_reference.sh'

# Known GIAB samples mapping
GIAB_SAMPLES = {
    'NA12878': 'HG001',
    'HG001': 'HG001',
    'NA24385': 'HG002',
    'HG002': 'HG002',
    'NA24149': 'HG003',
    'HG003': 'HG003',
    'NA24143': 'HG004',
    'HG004': 'HG004',
    'NA24631': 'HG005',
    'HG005': 'HG005',
    'NA24694': 'HG006',
    'HG006': 'HG006',
    'NA24695': 'HG007',
    'HG007': 'HG007',
}


def extract_base_sample(sample_name: str) -> str:
    """
    Extract base sample name from full sample identifier.
    
    Examples:
        NA24143_Lib3_Rep1 -> NA24143
        HG004_run1 -> HG004
        NA12878 -> NA12878
    
    Args:
        sample_name: Full sample identifier
        
    Returns:
        Base sample name
    """
    # First, take the first part before underscore (or full name if no underscore)
    base_name = sample_name.split('_')[0]
    
    # Check if the base name is a known GIAB sample
    if base_name in GIAB_SAMPLES:
        return base_name
    
    # Also check if the full sample_name starts with a known GIAB sample
    for known_sample in GIAB_SAMPLES.keys():
        if sample_name.startswith(known_sample):
            return known_sample
    
    # Return the base name
    return base_name


def is_giab_sample(sample_name: str) -> bool:
    """
    Check if a sample is a known GIAB sample.
    
    Args:
        sample_name: Sample identifier
        
    Returns:
        True if sample is in GIAB catalog
    """
    base_sample = extract_base_sample(sample_name)
    return base_sample in GIAB_SAMPLES


def get_giab_id(sample_name: str) -> Optional[str]:
    """
    Get GIAB identifier (HG00X) for a sample.
    
    Args:
        sample_name: Sample identifier
        
    Returns:
        GIAB ID (e.g., 'HG004') or None if not a GIAB sample
    """
    base_sample = extract_base_sample(sample_name)
    return GIAB_SAMPLES.get(base_sample)


def check_genome_reference() -> Tuple[bool, List[str]]:
    """
    Check if genome reference files exist.
    
    Returns:
        Tuple of (all_exist, missing_files)
    """
    required_files = {
        'FASTA': REFERENCE_DIR / 'GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta',
        'FAI': REFERENCE_DIR / 'GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta.fai',
        'SDF': REFERENCE_DIR / 'GRCh38.sdf',
    }
    
    missing = []
    for name, path in required_files.items():
        if not path.exists():
            missing.append(name)
    
    return len(missing) == 0, missing


def check_sample_reference(sample_name: str) -> Tuple[bool, List[str]]:
    """
    Check if sample reference files exist.
    
    Args:
        sample_name: Sample identifier
        
    Returns:
        Tuple of (all_exist, missing_files)
    """
    base_sample = extract_base_sample(sample_name)
    sample_dir = REFERENCE_DIR / base_sample
    
    missing = []
    
    # Check directory exists
    if not sample_dir.exists():
        missing.append('Sample directory')
        return False, missing
    
    # Check for VCF truth set
    vcf_files = list(sample_dir.glob('*.vcf.gz'))
    if not vcf_files:
        missing.append('Truth VCF')
    
    # Check for BED confident regions
    bed_files = list(sample_dir.glob('*.bed'))
    if not bed_files:
        missing.append('Confident regions BED')
    
    # Check for SV reference (optional but recommended)
    stvar_dir = sample_dir / 'stvar'
    if not stvar_dir.exists():
        missing.append('SV directory')
    else:
        sv_vcf = list(stvar_dir.glob('*.vcf.gz'))
        sv_bed = list(stvar_dir.glob('*.bed'))
        if not sv_vcf or not sv_bed:
            missing.append('SV reference files')
    
    return len(missing) == 0, missing


def check_references(sample_name: str) -> Dict[str, any]:
    """
    Comprehensive check of all required reference files.
    
    Args:
        sample_name: Sample identifier
        
    Returns:
        Dictionary with check results
    """
    base_sample = extract_base_sample(sample_name)
    
    genome_ok, genome_missing = check_genome_reference()
    sample_ok, sample_missing = check_sample_reference(sample_name)
    
    return {
        'sample_name': sample_name,
        'base_sample': base_sample,
        'is_giab': is_giab_sample(sample_name),
        'giab_id': get_giab_id(sample_name),
        'genome_reference': {
            'complete': genome_ok,
            'missing': genome_missing
        },
        'sample_reference': {
            'complete': sample_ok,
            'missing': sample_missing
        },
        'ready_for_processing': genome_ok and sample_ok
    }


def setup_reference(sample_name: str, check_only: bool = False) -> Tuple[bool, str]:
    """
    Setup reference files for a sample using the bash script.
    
    Args:
        sample_name: Sample identifier
        check_only: Only check if files exist, don't download
        
    Returns:
        Tuple of (success, message)
    """
    if not SETUP_SCRIPT.exists():
        error_msg = f"Setup script not found: {SETUP_SCRIPT}"
        logger.error(error_msg)
        return False, error_msg
    
    try:
        cmd = [str(SETUP_SCRIPT), sample_name]
        if check_only:
            cmd.append('--check-only')
        
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info(f"Reference setup successful for {sample_name}")
            return True, result.stdout
        elif result.returncode == 2:
            # Exit code 2 = unknown sample, manual setup required
            msg = f"Unknown sample {sample_name}. Manual reference setup required."
            logger.warning(msg)
            return False, msg
        else:
            error_msg = f"Reference setup failed: {result.stderr}"
            logger.error(error_msg)
            return False, error_msg
            
    except Exception as e:
        error_msg = f"Error running setup script: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def ensure_references(sample_name: str, auto_download: bool = True) -> Tuple[bool, str]:
    """
    Ensure all required reference files exist, downloading if necessary.
    
    Args:
        sample_name: Sample identifier
        auto_download: Automatically download missing files if True
        
    Returns:
        Tuple of (ready, message)
    """
    logger.info(f"Checking references for {sample_name}...")
    
    # Check current state
    check_result = check_references(sample_name)
    
    if check_result['ready_for_processing']:
        logger.info(f"All reference files present for {sample_name}")
        return True, "All reference files present"
    
    # Log what's missing
    missing_info = []
    if not check_result['genome_reference']['complete']:
        missing_info.append(f"Genome: {', '.join(check_result['genome_reference']['missing'])}")
    if not check_result['sample_reference']['complete']:
        missing_info.append(f"Sample: {', '.join(check_result['sample_reference']['missing'])}")
    
    logger.warning(f"Missing reference files: {'; '.join(missing_info)}")
    
    # If auto_download is disabled, return error
    if not auto_download:
        return False, f"Missing reference files: {'; '.join(missing_info)}"
    
    # If not a GIAB sample, can't auto-download
    if not check_result['is_giab']:
        msg = (
            f"Sample {sample_name} is not a known GIAB sample. "
            f"Please manually provide reference files in: {REFERENCE_DIR}/{check_result['base_sample']}/"
        )
        logger.error(msg)
        return False, msg
    
    # Attempt to download
    logger.info(f"Attempting to download GIAB references for {sample_name}...")
    success, message = setup_reference(sample_name, check_only=False)
    
    if success:
        # Verify again
        check_result = check_references(sample_name)
        if check_result['ready_for_processing']:
            return True, "Reference files downloaded successfully"
        else:
            return False, "Download completed but some files still missing"
    else:
        return False, message


def get_reference_status(sample_name: str) -> Dict[str, any]:
    """
    Get detailed status of reference files for a sample.
    
    Args:
        sample_name: Sample identifier
        
    Returns:
        Dictionary with detailed status information
    """
    check_result = check_references(sample_name)
    base_sample = check_result['base_sample']
    sample_dir = REFERENCE_DIR / base_sample
    
    # Get detailed file information
    files_info = {
        'genome': {},
        'sample': {},
        'sv': {}
    }
    
    # Genome files
    genome_files = {
        'fasta': REFERENCE_DIR / 'GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta',
        'fai': REFERENCE_DIR / 'GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta.fai',
        'sdf': REFERENCE_DIR / 'GRCh38.sdf',
    }
    for name, path in genome_files.items():
        files_info['genome'][name] = {
            'exists': path.exists(),
            'path': str(path) if path.exists() else None
        }
    
    # Sample files
    if sample_dir.exists():
        vcf_files = list(sample_dir.glob('*.vcf.gz'))
        bed_files = list(sample_dir.glob('*.bed'))
        files_info['sample']['vcf'] = {
            'exists': len(vcf_files) > 0,
            'path': str(vcf_files[0]) if vcf_files else None
        }
        files_info['sample']['bed'] = {
            'exists': len(bed_files) > 0,
            'path': str(bed_files[0]) if bed_files else None
        }
        
        # SV files
        stvar_dir = sample_dir / 'stvar'
        if stvar_dir.exists():
            sv_vcf = list(stvar_dir.glob('*.vcf.gz'))
            sv_bed = list(stvar_dir.glob('*.bed'))
            files_info['sv']['vcf'] = {
                'exists': len(sv_vcf) > 0,
                'path': str(sv_vcf[0]) if sv_vcf else None
            }
            files_info['sv']['bed'] = {
                'exists': len(sv_bed) > 0,
                'path': str(sv_bed[0]) if sv_bed else None
            }
    
    return {
        **check_result,
        'files': files_info
    }


# Main function for CLI usage
if __name__ == '__main__':
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python setup_reference.py <sample_name> [--status|--check|--setup]")
        sys.exit(1)
    
    sample = sys.argv[1]
    action = sys.argv[2] if len(sys.argv) > 2 else '--status'
    
    if action == '--status':
        status = get_reference_status(sample)
        print(json.dumps(status, indent=2))
    elif action == '--check':
        result = check_references(sample)
        print(json.dumps(result, indent=2))
    elif action == '--setup':
        success, message = ensure_references(sample, auto_download=True)
        print(f"Success: {success}")
        print(f"Message: {message}")
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)

