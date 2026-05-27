from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from api.app import crud, models, settings


def create_job(
    db: Session,
    *,
    job_type: models.TransferJobType,
    subject_id: str,
    phase: models.TransferJobPhase | None = None,
    status: models.TransferJobStatus = models.TransferJobStatus.RUNNING,
    source_uri: str | None = None,
    destination_path: str | None = None,
    bytes_total: int | None = None,
    metadata_json: dict | None = None,
) -> models.TransferJob:
    job = crud.create_transfer_job(
        db,
        job_type=job_type,
        subject_id=subject_id,
        phase=phase,
        status=status,
        source_uri=source_uri,
        destination_path=destination_path,
        bytes_total=bytes_total,
        metadata_json=metadata_json,
    )
    return job


def get_job(db: Session, job_id: str) -> models.TransferJob | None:
    return crud.get_transfer_job(db, job_id)


def list_jobs(
    db: Session,
    *,
    status: models.TransferJobStatus | None = None,
    job_type: models.TransferJobType | None = None,
    limit: int = 100,
) -> list[models.TransferJob]:
    return crud.list_transfer_jobs(db, status=status, job_type=job_type, limit=limit)


def append_event(
    db: Session,
    job_id: str,
    message: str,
    *,
    level: models.TransferEventLevel = models.TransferEventLevel.INFO,
    phase: models.TransferJobPhase | None = None,
    bytes_done: int | None = None,
    bytes_total: int | None = None,
    rate_bps: int | None = None,
    metadata_json: dict | None = None,
) -> models.TransferEvent:
    event = crud.create_transfer_event(
        db,
        job_id=job_id,
        message=message,
        level=level,
        phase=phase,
        bytes_done=bytes_done,
        bytes_total=bytes_total,
        rate_bps=rate_bps,
        metadata_json=metadata_json,
    )
    return event


def list_events(db: Session, job_id: str, since: int = 0) -> list[models.TransferEvent]:
    return crud.list_transfer_events(db, job_id, since=since)


def count_events(db: Session, job_id: str) -> int:
    return crud.count_transfer_events(db, job_id)


def update_progress(
    db: Session,
    job_id: str,
    *,
    bytes_done: int,
    bytes_total: int | None = None,
    rate_bps: int | None = None,
    eta_seconds: int | None = None,
    message: str | None = None,
) -> models.TransferJob:
    job = crud.get_transfer_job(db, job_id)
    if not job:
        raise ValueError(f"Transfer job not found: {job_id}")

    total = bytes_total if bytes_total is not None else job.bytes_total
    if eta_seconds is None and rate_bps and total:
        remaining = max(total - bytes_done, 0)
        eta_seconds = int(remaining / rate_bps) if rate_bps > 0 else None

    updated = crud.update_transfer_job(
        db,
        job_id,
        bytes_done=bytes_done,
        bytes_total=total,
        rate_bps=rate_bps,
        eta_seconds=eta_seconds,
        status=models.TransferJobStatus.RUNNING,
    )
    append_event(
        db,
        job_id,
        message or _progress_message(bytes_done, total),
        level=models.TransferEventLevel.PROGRESS,
        phase=updated.phase if updated else None,
        bytes_done=bytes_done,
        bytes_total=total,
        rate_bps=rate_bps,
    )
    return updated


def mark_phase(
    db: Session,
    job_id: str,
    phase: models.TransferJobPhase,
    message: str | None = None,
) -> models.TransferJob:
    job = crud.update_transfer_job(
        db,
        job_id,
        phase=phase,
        status=models.TransferJobStatus.RUNNING,
    )
    if not job:
        raise ValueError(f"Transfer job not found: {job_id}")
    append_event(
        db,
        job_id,
        message or f"Phase changed to {phase.value}",
        level=models.TransferEventLevel.INFO,
        phase=phase,
    )
    return job


def complete_job(db: Session, job_id: str, message: str = "Job completed") -> models.TransferJob:
    job = crud.update_transfer_job(
        db,
        job_id,
        status=models.TransferJobStatus.COMPLETED,
        phase=models.TransferJobPhase.COMPLETE,
        completed_at=datetime.utcnow(),
        error_code=None,
        error_message=None,
        eta_seconds=0,
    )
    if not job:
        raise ValueError(f"Transfer job not found: {job_id}")
    append_event(
        db,
        job_id,
        message,
        level=models.TransferEventLevel.SUCCESS,
        phase=models.TransferJobPhase.COMPLETE,
    )
    return job


def fail_job(
    db: Session,
    job_id: str,
    message: str,
    *,
    error_code: str | None = None,
) -> models.TransferJob:
    job = crud.update_transfer_job(
        db,
        job_id,
        status=models.TransferJobStatus.FAILED,
        completed_at=datetime.utcnow(),
        error_code=error_code,
        error_message=message,
    )
    if not job:
        raise ValueError(f"Transfer job not found: {job_id}")
    append_event(
        db,
        job_id,
        message,
        level=models.TransferEventLevel.ERROR,
        phase=job.phase,
    )
    return job


def request_cancel(db: Session, job_id: str) -> models.TransferJob:
    job = crud.update_transfer_job(db, job_id, cancel_requested=True)
    if not job:
        raise ValueError(f"Transfer job not found: {job_id}")
    append_event(
        db,
        job_id,
        "Cancellation requested",
        level=models.TransferEventLevel.WARNING,
        phase=job.phase,
    )
    return job


def retry_job(db: Session, job_id: str) -> models.TransferJob:
    original = crud.get_transfer_job(db, job_id)
    if not original:
        raise ValueError(f"Transfer job not found: {job_id}")
    return create_job(
        db,
        job_type=original.type,
        subject_id=original.subject_id,
        phase=original.phase,
        status=models.TransferJobStatus.QUEUED,
        source_uri=original.source_uri,
        destination_path=original.destination_path,
        bytes_total=original.bytes_total,
        metadata_json={"retry_of": original.id},
    )


def get_job_summary(db: Session, data_dir: Path | None = None) -> dict:
    data_path = data_dir or settings.DATA_DIR
    try:
        disk_free = shutil.disk_usage(data_path).free
    except FileNotFoundError:
        disk_free = shutil.disk_usage(settings.PROJECT_ROOT).free

    return {
        "active_jobs": crud.count_transfer_jobs(db, status=models.TransferJobStatus.RUNNING),
        "queued_jobs": crud.count_transfer_jobs(db, status=models.TransferJobStatus.QUEUED),
        "failed_24h": crud.failed_jobs_last_24h(db),
        "total_rate_bps": crud.total_active_rate_bps(db),
        "disk_free_bytes": disk_free,
    }


def _progress_message(bytes_done: int, bytes_total: int | None) -> str:
    if bytes_total:
        pct = min(max((bytes_done / bytes_total) * 100, 0), 100)
        return f"Progress {bytes_done} / {bytes_total} bytes ({pct:.1f}%)"
    return f"Progress {bytes_done} bytes"
