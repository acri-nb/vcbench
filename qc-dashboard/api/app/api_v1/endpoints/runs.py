from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from pathlib import Path
from typing import Optional
import shutil

from api.app import crud, schemas, models
from api.app.database import get_db
from api.tasks.process_run import run_pipeline
from api.tasks.upload_run import upload_run

router = APIRouter()

# Get absolute path to this file's directory
APP_DIR = Path(__file__).parent.parent.parent
PROJECT_ROOT = APP_DIR.parent.parent.parent
LAB_RUNS_DIR = PROJECT_ROOT / "data" / "lab_runs"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# Temporary directory for uploads
UPLOAD_DIR = PROJECT_ROOT / "qc-dashboard" / "api" / "app" / "tmp" / "uploads"

# DB ---------------------------------------------------------------------------------------

@router.post("/runs/upload", response_model=schemas.LabRunResponse)
async def upload_lab_run(
    benchmarking: Optional[str] = Query(default=""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a lab run file."""
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only .zip files are allowed")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = UPLOAD_DIR / file.filename
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    lab_run_create = schemas.LabRunCreate(
        run_name=file.filename[:-4],  # Remove .zip extension
        status="PENDING_PROCESSING"
    )
    try:
        lab_run = crud.create_lab_run(db, lab_run_create)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        sample, run = upload_run()
        run_pipeline(
            sample,
            run,
            happy="happy" in benchmarking,
            stratified="stratified" in benchmarking,
            csv_reformat="csv" in benchmarking,
            truvari="truvari" in benchmarking
        )
        # Update lab run status to AWAITING_APPROVAL
        crud.update_lab_run_status(db, lab_run.id, models.RunStatus.AWAITING_APPROVAL)
    except Exception as e:
        # Update lab run status to FAILED
        crud.update_lab_run_status(db, lab_run.id, models.RunStatus.FAILED)
        raise HTTPException(status_code=500, detail=f"Error processing run: {str(e)}")
    return lab_run

@router.post("/runs/{run_id}/approve")
def approve_lab_run(run_id: int, db: Session = Depends(get_db)):
    """Approve a lab run."""
    lab_run = crud.get_lab_run(db, run_id)
    if not lab_run:
        raise HTTPException(status_code=404, detail="Lab run not found")
    crud.update_lab_run_status(db, run_id, models.RunStatus.APPROVED)
    return {"message": f"Lab run '{run_id}' approved"}

@router.get("/runs/{run_id}", response_model=schemas.LabRunResponse)
def get_run_by_id(run_id: int, db: Session = Depends(get_db)):
    lab_run = crud.get_lab_run(db, run_id)
    if not lab_run:
        raise HTTPException(status_code=404, detail="Lab run not found")
    return lab_run

@router.get("/runs/by-name/{run_name}", response_model=schemas.LabRunResponse)
def get_run_by_name(run_name: str, db: Session = Depends(get_db)):
    lab_run = crud.get_lab_run_by_name(db, run_name)
    if not lab_run:
        raise HTTPException(status_code=404, detail="Lab run not found")
    return lab_run

@router.delete("/runs/{run_id}")
def delete_lab_run(run_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_lab_run(db, run_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Lab run not found")
    return {"message": f"Lab run '{run_id}' deleted"}

# FILES -------------------------------------------------------------------------------------------

@router.get("/runs")
def list_lab_runs(db: Session = Depends(get_db)):
    """List all lab runs."""
    try:
        if not LAB_RUNS_DIR.exists():
            return []
        
        runs_data = []
        for run in LAB_RUNS_DIR.iterdir():
            if run.is_dir():
                # Check if it's been processed
                status = "COMPLETED" if (PROCESSED_DIR / run.name).exists() else "PENDING"
                runs_data.append({
                    "run_name": run.name,
                    "status": status,
                    "approved_at": None  # Add this field for the frontend
                })
        return runs_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing runs: {str(e)}")
    
@router.get("/runs/{metric_name}")
def get_run_metrics(metric_name: str, db: Session = Depends(get_db)):
    samples = list_lab_runs(db)
    
@router.get("/runs/{run_name}/benchmarking")
def get_run_benchmarking(run_name: str, db: Session = Depends(get_db)):
    print(run_name)
    run_dir = None
    for run in PROCESSED_DIR.iterdir():
        if run_name in run.name:
            run_dir = run
            break
    if not run_dir:
        raise HTTPException(status_code=404, detail="Run not found")
    benchmarks = {}
    benchmarks["truvari"] = any(run_dir.rglob("summary.json"))
    benchmarks["happy"] = any(run_dir.rglob("*.summary.csv"))
    benchmarks["stratified"] = any(run_dir.glob("*.extended.csv"))
    return benchmarks

@router.post("/runs/{run_name}/benchmarking")
async def process_run_benchmarking(run_name: str, benchmarking: str):
    try:
        sample, run = run_name.split("_", 1)
        run_pipeline(
            sample,
            run,
            happy="happy" in benchmarking,
            stratified="stratified" in benchmarking,
            csv_reformat="csv" in benchmarking,
            truvari="truvari" in benchmarking
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing run: {str(e)}")