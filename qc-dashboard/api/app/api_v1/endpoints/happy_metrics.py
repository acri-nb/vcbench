from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.app import crud, schemas
from api.app.database import get_db
from api.tasks.utils import get_metric

router = APIRouter()

@router.post("/api/v1/runs/{run_name}/happy_metrics", response_model=schemas.HappyMetricResponse)
def store_happy_metrics(run_name: str, data: schemas.HappyMetricCreate, db: Session = Depends(get_db)):
    """Store happy metrics for a specific run."""
    try:
        metric = crud.create_happy_metric(db, data)
    except Exception as e:
        # Optionally log the error here
        raise HTTPException(status_code=400, detail=str(e))
    return metric

# File read GET for happy metrics
@router.get("/api/v1/runs/{run_name}/happy_metrics", response_model=schemas.HappyMetricBase)
def get_happy_metrics(run_name: str):
    """Get happy metrics for a specific run."""
    try:
        metric = get_metric(run_name, "summary.csv")
        return schemas.HappyMetricBase(**metric)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Happy metrics not found.")
