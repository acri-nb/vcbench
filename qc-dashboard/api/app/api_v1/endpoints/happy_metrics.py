from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.app import crud, schemas
from api.app.database import get_db
from api.app.security import Role, require_role
from api.tasks.utils import get_metric

router = APIRouter()

@router.post("/runs/{run_name}/happy_metrics", response_model=schemas.HappyMetricResponse)
def store_happy_metrics(
    run_name: str,
    data: schemas.HappyMetricCreate,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_role(Role.OPERATOR)),
):
    """Store happy metrics for a specific run."""
    lab_run = crud.get_lab_run_by_name(db, run_name)
    if not lab_run:
        raise HTTPException(status_code=404, detail=f"Run {run_name} not found")
    if data.run_id != lab_run.id:
        raise HTTPException(status_code=400, detail="Payload run_id does not match run_name")
    try:
        metric = crud.create_happy_metric(db, data)
    except Exception as e:
        # Optionally log the error here
        raise HTTPException(status_code=400, detail=str(e))
    return metric

# File read GET for happy metrics
@router.get("/runs/{run_name}/happy_metrics", response_model=schemas.HappyMetricBase)
def get_happy_metrics(run_name: str):
    """Get happy metrics for a specific run."""
    try:
        metric = get_metric(run_name, "summary.csv")
        return schemas.HappyMetricBase(**map_summary_metric(metric))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Happy metrics not found.")


def map_summary_metric(metric: dict) -> dict:
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
    converted = {}
    for csv_key, schema_key in key_map.items():
        value = metric.get(csv_key)
        if schema_key in {"type", "filter"}:
            converted[schema_key] = value or ""
        elif schema_key in {
            "truth_total", "truth_tp", "truth_fn", "query_total", "query_fp", "query_unk"
        }:
            converted[schema_key] = int(float(value or 0))
        else:
            converted[schema_key] = float(value or 0)
    return converted
