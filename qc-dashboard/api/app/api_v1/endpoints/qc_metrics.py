from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.app import crud, schemas
from api.app.database import get_db

router = APIRouter()

# DB ----------------------------------------------------------------------------------------------

@router.post("/api/v1/qc_metrics/{run_id}")
def create_qc_metric(run_id: int, qc_metric: schemas.QCMetricCreate, db: Session = Depends(get_db)):
    db_run = crud.get_lab_run(db, run_id)
    if not db_run:
        raise HTTPException(status_code=404, detail="Run not found")
    try:
        created_metric = crud.create_qc_metric(
            db=db,
            qc_metric=qc_metric
        )
        return created_metric
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.get("/api/v1/qc_metrics/{run_id}/{metric_name}", response_model=schemas.QCMetricResponse)
def get_qc_metric(run_id: int, metric_name: str, db: Session = Depends(get_db)):
    db_run = crud.get_lab_run(db, run_id)
    if not db_run:
        raise HTTPException(status_code=404, detail="Run not found")
    metric = crud.get_qc_metric_by_name(db, run_id, metric_name)
    if not metric:
        raise HTTPException(status_code=404, detail="QC Metric not found")
    return metric