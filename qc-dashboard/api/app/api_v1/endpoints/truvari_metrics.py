from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from api.app import schemas, crud
from api.app.database import get_db

router = APIRouter()

@router.post("/runs/{run_name}/truvari_metrics", response_model=schemas.TruvariMetricResponse)
def store_truvari_metrics(
    run_name: str,
    data: schemas.TruvariMetricCreate,
    db: Session = Depends(get_db)
):
    """Store Truvari benchmarking metrics for a run."""
    # Verify the run exists
    lab_run = crud.get_lab_run_by_name(db, run_name)
    if not lab_run:
        raise HTTPException(status_code=404, detail=f"Run {run_name} not found")
    
    # Create metric
    try:
        metric = crud.create_truvari_metric(db, data)
        return metric
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error storing Truvari metrics: {str(e)}")

@router.get("/runs/{run_name}/truvari_metrics", response_model=schemas.TruvariMetricResponse)
def get_truvari_metrics(run_name: str, db: Session = Depends(get_db)):
    """Get Truvari benchmarking metrics for a run."""
    metric = crud.get_truvari_metric_by_run_name(db, run_name)
    if not metric:
        raise HTTPException(
            status_code=404,
            detail=f"No Truvari metrics found for run {run_name}"
        )
    return metric

@router.get("/runs/{run_id}/truvari_metrics/all", response_model=List[schemas.TruvariMetricResponse])
def get_all_truvari_metrics(run_id: int, db: Session = Depends(get_db)):
    """Get all Truvari metrics for a specific run ID."""
    metrics = crud.get_truvari_metrics(db, run_id)
    return metrics

