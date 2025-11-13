import os
from pathlib import Path
import zipfile
from shutil import rmtree

PROJECT_ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
TEMP_RUN_DIR = PROJECT_ROOT / "qc-dashboard" / "api" / "app" / "tmp" / "uploads"
LAB_RUN_DIR = PROJECT_ROOT / 'data' / 'lab_runs'

def upload_run():
    """
    Upload a sequencing run.
    """
    # Parse command line arguments
    decompress_zip(TEMP_RUN_DIR)
    # Get all runs in uploads lab run directory
    for item in TEMP_RUN_DIR.iterdir():
        if not item.is_dir():
            continue
        sample, run = get_run_info(item)
        # Move the decompressed lab runs to the LAB_RUN_DIR
        move_lab_runs(sample, run)
    delete_temp_dir(TEMP_RUN_DIR.parent)
    return sample, run
    
def decompress_zip(dir_path):
    """
    Decompress all zip files in the given directory.
    """
    for zip_file in Path(dir_path).glob('*.zip'):
        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(TEMP_RUN_DIR)
                return zip_file.stem
        except Exception as e:
            print(f"Failed to decompress {zip_file}: {e}")
            raise e
        
def get_run_info(item):
    """
    Extract sample and run information from the item name.
    Assumes the item name is in the format 'sample_run_name'.
    """
    parts = item.name.split('_')
    if len(parts) != 3:
        raise ValueError(f"Unexpected item name format: {item.name}")
    sample_name = parts[0]
    run_name = '_'.join(parts[1:])
    return sample_name, run_name

def move_lab_runs(sample, run):
    """
    Move lab runs from the source directory to the destination directory.
    """
    src_dir = TEMP_RUN_DIR / f"{sample}_{run}"
    if not src_dir.exists():
        print(f"Source directory {src_dir} does not exist.")
        return
    dest_dir = LAB_RUN_DIR / f"{sample}_{run}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for item in src_dir.iterdir():
        if item.is_dir():
            continue
        target_path = dest_dir / item.name
        if target_path.exists():
            continue
        try:
            item.rename(target_path)
        except Exception as e:
            print(f"Failed to move {item} to {target_path}: {e}")
            
def delete_temp_dir(temp_dir: Path):
    """
    Delete the temporary directory.
    """
    if not temp_dir.exists():
        return
    try:
        rmtree(temp_dir)
    except Exception as e:
        print(f"Failed to delete temporary directory {temp_dir}: {e}")