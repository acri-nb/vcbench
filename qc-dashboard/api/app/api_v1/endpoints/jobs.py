from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.app import job_service, models, schemas
from api.app.database import get_db
from api.app.security import Role, require_role

router = APIRouter()


def _parse_status(value: str | None) -> models.TransferJobStatus | None:
    if not value:
        return None
    try:
        return models.TransferJobStatus(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid job status: {value}") from exc


def _parse_type(value: str | None) -> models.TransferJobType | None:
    if not value:
        return None
    try:
        return models.TransferJobType(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid job type: {value}") from exc


@router.get("/jobs", response_model=list[schemas.TransferJobResponse])
def list_jobs(
    status: str | None = Query(default=None),
    type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return job_service.list_jobs(
        db,
        status=_parse_status(status),
        job_type=_parse_type(type),
        limit=limit,
    )


@router.get("/jobs/summary", response_model=schemas.TransferJobSummary)
def get_jobs_summary(db: Session = Depends(get_db)):
    return job_service.get_job_summary(db)


@router.get("/jobs/{job_id}", response_model=schemas.TransferJobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Transfer job not found")
    return job


@router.get("/jobs/{job_id}/events")
def get_job_events(
    job_id: str,
    since: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    job = job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Transfer job not found")
    events = job_service.list_events(db, job_id, since=since)
    total_events = job_service.count_events(db, job_id)
    return {
        "job_id": job_id,
        "events": [
            schemas.TransferEventResponse.model_validate(event).model_dump(mode="json")
            for event in events
        ],
        "total_events": total_events,
        "status": job.status.value,
        "has_more": since < total_events,
    }


@router.post("/jobs/{job_id}/cancel", response_model=schemas.TransferJobResponse)
def cancel_job(
    job_id: str,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_role(Role.OPERATOR)),
):
    try:
        return job_service.request_cancel(db, job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/jobs/{job_id}/retry", response_model=schemas.TransferJobResponse)
def retry_job(
    job_id: str,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_role(Role.OPERATOR)),
):
    try:
        return job_service.retry_job(db, job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
