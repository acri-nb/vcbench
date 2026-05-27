from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from pathlib import Path
from typing import Optional

from api.app import crud, job_service, schemas, models
from api.app.database import get_db
from api.app.security import Role, require_role
from api.app import settings
from api.tasks.process_run import run_pipeline
from api.tasks.upload_run import upload_run, unique_upload_path, sanitize_upload_filename
from api.tasks.utils import split_run_name

router = APIRouter()

LAB_RUNS_DIR = settings.LAB_RUNS_DIR
PROCESSED_DIR = settings.PROCESSED_DIR
UPLOAD_DIR = settings.UPLOAD_DIR

# DB ---------------------------------------------------------------------------------------

@router.post("/runs/upload", response_model=schemas.LabRunResponse)
async def upload_lab_run(
    benchmarking: Optional[str] = Query(default=""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _role: Role = Depends(require_role(Role.OPERATOR)),
):
    """Upload a lab run file."""
    try:
        filename = sanitize_upload_filename(file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = unique_upload_path(filename)
    with open(temp_path, "wb") as buffer:
        bytes_written = 0
        while True:
            chunk = await file.read(8 * 1024 * 1024)
            if not chunk:
                break
            bytes_written += len(chunk)
            if bytes_written > settings.MAX_UPLOAD_BYTES:
                if temp_path.exists():
                    temp_path.unlink()
                raise HTTPException(status_code=413, detail="Upload exceeds configured size limit")
            buffer.write(chunk)
    lab_run_create = schemas.LabRunCreate(
        run_name=Path(filename).stem,
        status=models.RunStatus.PENDING_PROCESSING
    )
    try:
        lab_run = crud.create_lab_run(db, lab_run_create)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        crud.update_lab_run_status(db, lab_run.id, models.RunStatus.PROCESSING)
        sample, run = upload_run(temp_path)
        crud.update_lab_run_name(db, lab_run.id, f"{sample}_{run}")
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
        crud.update_lab_run_status(db, lab_run.id, models.RunStatus.FAILED, error_message=str(e))
        raise HTTPException(status_code=500, detail=f"Error processing run: {str(e)}")
    return lab_run

@router.post("/runs/{run_id}/approve")
def approve_lab_run(
    run_id: int,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_role(Role.REVIEWER)),
):
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
def delete_lab_run(
    run_id: int,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_role(Role.ADMIN)),
):
    deleted = crud.delete_lab_run(db, run_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Lab run not found")
    return {"message": f"Lab run '{run_id}' deleted"}

# FILES -------------------------------------------------------------------------------------------

@router.get("/runs")
def list_lab_runs(db: Session = Depends(get_db)):
    """List all lab runs."""
    try:
        runs_by_name = {}
        try:
            for run in crud.get_lab_runs(db):
                runs_by_name[run.run_name] = {
                    "id": run.id,
                    "run_name": run.run_name,
                    "status": run.status.value,
                    "created_at": run.created_at,
                    "updated_at": run.updated_at,
                    "approved_at": run.approved_at,
                    "error_message": run.error_message,
                }
        except Exception:
            db.rollback()

        if not LAB_RUNS_DIR.exists():
            return list(runs_by_name.values())
        
        for run in LAB_RUNS_DIR.iterdir():
            if run.is_dir():
                # Check if it's been processed
                status = (
                    models.RunStatus.AWAITING_APPROVAL.value
                    if find_processed_run_dir(run.name)
                    else models.RunStatus.PENDING_PROCESSING.value
                )
                runs_by_name.setdefault(run.name, {
                    "id": None,
                    "run_name": run.name,
                    "status": status,
                    "created_at": None,
                    "updated_at": None,
                    "approved_at": None,
                    "error_message": None,
                })
        return list(runs_by_name.values())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing runs: {str(e)}")
    
@router.get("/runs/{run_name}/benchmarking")
def get_run_benchmarking(run_name: str, db: Session = Depends(get_db)):
    run_dir = find_processed_run_dir(run_name)
    if not run_dir:
        raise HTTPException(status_code=404, detail="Run not found")
    benchmarks = {}
    benchmarks["truvari"] = any(run_dir.rglob("summary.json"))
    benchmarks["happy"] = any(run_dir.rglob("*.summary.csv"))
    benchmarks["stratified"] = any(run_dir.glob("*.extended.csv"))
    benchmarks["csv"] = any(run_dir.glob("*.csv"))
    return benchmarks

@router.post("/runs/{run_name}/benchmarking")
async def process_run_benchmarking(
    run_name: str,
    benchmarking: str,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_role(Role.OPERATOR)),
):
    lab_run = None
    job = None
    try:
        sample, run = split_run_name(run_name)
        job = job_service.create_job(
            db,
            job_type=models.TransferJobType.PIPELINE,
            subject_id=run_name,
            phase=models.TransferJobPhase.PROCESS,
            source_uri=str(LAB_RUNS_DIR / run_name),
            destination_path=str(PROCESSED_DIR),
            metadata_json={"benchmarking": benchmarking},
        )
        job_service.append_event(
            db,
            job.id,
            f"Starting benchmarking for {run_name}",
            level=models.TransferEventLevel.INFO,
            phase=models.TransferJobPhase.PROCESS,
        )
        try:
            lab_run = crud.get_lab_run_by_name(db, run_name)
        except Exception:
            db.rollback()
        if lab_run is None:
            lab_run = crud.create_lab_run(
                db,
                schemas.LabRunCreate(
                    run_name=run_name,
                    status=models.RunStatus.PENDING_PROCESSING,
                ),
            )
        crud.update_lab_run_status(db, lab_run.id, models.RunStatus.PROCESSING)
        run_pipeline(
            sample,
            run,
            happy="happy" in benchmarking,
            stratified="stratified" in benchmarking,
            csv_reformat="csv" in benchmarking,
            truvari="truvari" in benchmarking
        )
        crud.update_lab_run_status(db, lab_run.id, models.RunStatus.AWAITING_APPROVAL)
        job_service.complete_job(db, job.id, "Benchmarking completed successfully")
        return {"ok": True, "run_name": run_name, "benchmarking": benchmarking, "job_id": job.id}
    except Exception as e:
        if lab_run:
            try:
                crud.update_lab_run_status(db, lab_run.id, models.RunStatus.FAILED, error_message=str(e))
            except Exception:
                db.rollback()
        if job:
            try:
                job_service.fail_job(db, job.id, str(e), error_code="pipeline_failed")
            except Exception:
                db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing run: {str(e)}")


def find_processed_run_dir(run_name: str) -> Optional[Path]:
    if not PROCESSED_DIR.exists():
        return None
    exact = PROCESSED_DIR / run_name
    if exact.exists() and exact.is_dir():
        return exact
    matching_dirs = [
        run for run in PROCESSED_DIR.iterdir()
        if run.is_dir() and run.name.endswith(f"_{run_name}")
    ]
    return matching_dirs[0] if matching_dirs else None
