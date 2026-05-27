from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy import func

from api.app import models
from api.app import schemas
from api.app.security import hash_password

# Users

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    """Create a new user in the database."""
    try:
        db_user = models.User(
            username=user.username,
            full_name=user.full_name,
            hashed_password=hash_password(user.password),
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        raise e

def get_user(db: Session, id: int) -> Optional[models.User]:
    """Get a user by ID."""
    return db.query(models.User).filter(models.User.id == id).first()

def delete_user(db: Session, id: int) -> Optional[models.User]:
    """Delete a user by ID. Returns the deleted user object, or None if not found."""
    user = db.query(models.User).filter(models.User.id == id).first()
    if user:
        db.delete(user)
        db.commit()
    return user

# Lab Runs

def create_lab_run(db: Session, lab_run: schemas.LabRunCreate) -> models.LabRun:
    """Create a new lab run."""
    try:
        db_lab_run = models.LabRun(
            run_name=lab_run.run_name,
            status=lab_run.status
        )
        db.add(db_lab_run)
        db.commit()
        db.refresh(db_lab_run)
        return db_lab_run
    except Exception as e:
        db.rollback()
        raise e

def get_lab_runs(db: Session) -> list[models.LabRun]:
    """Get all lab runs."""
    return db.query(models.LabRun).order_by(models.LabRun.created_at.desc()).all()

def get_lab_run(db: Session, run_id: int) -> Optional[models.LabRun]:
    """Get a lab run by ID."""
    return db.query(models.LabRun).filter(models.LabRun.id == run_id).first()

def get_lab_run_by_name(db: Session, run_name: str) -> Optional[models.LabRun]:
    """Get a lab run by its name."""
    return db.query(models.LabRun).filter(models.LabRun.run_name == run_name).first()

def delete_lab_run(db: Session, run_id: int) -> bool:
    """Delete a lab run by ID. Returns True if deleted, False if not found."""
    lab_run = db.query(models.LabRun).filter(models.LabRun.id == run_id).first()
    if lab_run:
        db.delete(lab_run)
        db.commit()
        return True
    return False

def update_lab_run_status(
    db: Session,
    run_id: int,
    status: models.RunStatus,
    error_message: Optional[str] = None,
) -> Optional[models.LabRun]:
    """Update the status of a lab run."""
    lab_run = db.query(models.LabRun).filter(models.LabRun.id == run_id).first()
    if lab_run:
        try:
            lab_run.status = status
            lab_run.error_message = error_message
            now = datetime.utcnow()
            if status == models.RunStatus.PROCESSING:
                lab_run.processing_started_at = now
            if status in {
                models.RunStatus.AWAITING_APPROVAL,
                models.RunStatus.APPROVED,
                models.RunStatus.FAILED,
            }:
                lab_run.processing_completed_at = now
            if status == models.RunStatus.APPROVED:
                lab_run.approved_at = now
            db.commit()
            db.refresh(lab_run)
            return lab_run
        except Exception:
            db.rollback()
            raise
    return None


def update_lab_run_name(db: Session, run_id: int, run_name: str) -> Optional[models.LabRun]:
    lab_run = db.query(models.LabRun).filter(models.LabRun.id == run_id).first()
    if lab_run:
        try:
            lab_run.run_name = run_name
            db.commit()
            db.refresh(lab_run)
            return lab_run
        except Exception:
            db.rollback()
            raise
    return None

# QC Metrics

def create_qc_metric(db: Session, qc_metric: schemas.QCMetricCreate) -> models.QCMetric:
    """Create a new QC metric."""
    try:
        db_qc_metric = models.QCMetric(
            metric_name=qc_metric.metric_name,
            metric_value=qc_metric.metric_value,
            file_source=qc_metric.file_source,
            run_id=qc_metric.run_id
        )
        db.add(db_qc_metric)
        db.commit()
        db.refresh(db_qc_metric)
        return db_qc_metric
    except Exception as e:
        db.rollback()
        raise e

def get_qc_metrics(db: Session, run_id: int) -> list[models.QCMetric]:
    """Get all QC metrics for a run."""
    return db.query(models.QCMetric).filter(models.QCMetric.run_id == run_id).all()


def get_qc_metric_by_name(db: Session, run_id: int, metric_name: str) -> Optional[models.QCMetric]:
    return (
        db.query(models.QCMetric)
        .filter(models.QCMetric.run_id == run_id, models.QCMetric.metric_name == metric_name)
        .first()
    )

def delete_qc_metric(db: Session, metric_id: int) -> bool:
    """Delete a QC metric by ID. Returns True if deleted, False if not found."""
    qc_metric = db.query(models.QCMetric).filter(models.QCMetric.id == metric_id).first()
    if qc_metric:
        db.delete(qc_metric)
        db.commit()
        return True
    return False


# Transfer Jobs

def create_transfer_job(
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
    job = models.TransferJob(
        type=job_type,
        subject_id=subject_id,
        status=status,
        phase=phase,
        source_uri=source_uri,
        destination_path=destination_path,
        bytes_total=bytes_total,
        bytes_done=0,
        metadata_json=metadata_json,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_transfer_job(db: Session, job_id: str) -> Optional[models.TransferJob]:
    return db.query(models.TransferJob).filter(models.TransferJob.id == job_id).first()


def list_transfer_jobs(
    db: Session,
    *,
    status: models.TransferJobStatus | None = None,
    job_type: models.TransferJobType | None = None,
    limit: int = 100,
) -> list[models.TransferJob]:
    query = db.query(models.TransferJob)
    if status is not None:
        query = query.filter(models.TransferJob.status == status)
    if job_type is not None:
        query = query.filter(models.TransferJob.type == job_type)
    return (
        query.order_by(models.TransferJob.updated_at.desc(), models.TransferJob.started_at.desc())
        .limit(limit)
        .all()
    )


def next_transfer_event_sequence(db: Session, job_id: str) -> int:
    current = (
        db.query(func.max(models.TransferEvent.sequence))
        .filter(models.TransferEvent.job_id == job_id)
        .scalar()
    )
    return (current or 0) + 1


def create_transfer_event(
    db: Session,
    *,
    job_id: str,
    message: str,
    level: models.TransferEventLevel = models.TransferEventLevel.INFO,
    phase: models.TransferJobPhase | None = None,
    bytes_done: int | None = None,
    bytes_total: int | None = None,
    rate_bps: int | None = None,
    metadata_json: dict | None = None,
) -> models.TransferEvent:
    event = models.TransferEvent(
        job_id=job_id,
        sequence=next_transfer_event_sequence(db, job_id),
        message=message,
        level=level,
        phase=phase,
        bytes_done=bytes_done,
        bytes_total=bytes_total,
        rate_bps=rate_bps,
        metadata_json=metadata_json,
    )
    job = get_transfer_job(db, job_id)
    if job:
        job.updated_at = datetime.utcnow()
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_transfer_events(db: Session, job_id: str, since: int = 0) -> list[models.TransferEvent]:
    query = db.query(models.TransferEvent).filter(models.TransferEvent.job_id == job_id)
    if since:
        query = query.filter(models.TransferEvent.sequence > since)
    return query.order_by(models.TransferEvent.sequence.asc()).all()


def count_transfer_events(db: Session, job_id: str) -> int:
    return db.query(models.TransferEvent).filter(models.TransferEvent.job_id == job_id).count()


def update_transfer_job(
    db: Session,
    job_id: str,
    **values,
) -> Optional[models.TransferJob]:
    job = get_transfer_job(db, job_id)
    if not job:
        return None
    for key, value in values.items():
        setattr(job, key, value)
    job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(job)
    return job


def count_transfer_jobs(
    db: Session,
    *,
    status: models.TransferJobStatus | None = None,
    failed_since: datetime | None = None,
) -> int:
    query = db.query(models.TransferJob)
    if status is not None:
        query = query.filter(models.TransferJob.status == status)
    if failed_since is not None:
        query = query.filter(
            models.TransferJob.status == models.TransferJobStatus.FAILED,
            models.TransferJob.completed_at >= failed_since,
        )
    return query.count()


def total_active_rate_bps(db: Session) -> int:
    total = (
        db.query(func.coalesce(func.sum(models.TransferJob.rate_bps), 0))
        .filter(models.TransferJob.status == models.TransferJobStatus.RUNNING)
        .scalar()
    )
    return int(total or 0)


def failed_jobs_last_24h(db: Session) -> int:
    return count_transfer_jobs(db, failed_since=datetime.utcnow() - timedelta(hours=24))

# Happy Metrics

def create_happy_metric(db: Session, happy_metric: schemas.HappyMetricCreate) -> models.HappyMetric:
    """Create a new Happy metric."""
    try:
        db_happy_metric = models.HappyMetric(
            type=happy_metric.type,
            filter=happy_metric.filter,
            truth_total=happy_metric.truth_total,
            truth_tp=happy_metric.truth_tp,
            truth_fn=happy_metric.truth_fn,
            query_total=happy_metric.query_total,
            query_fp=happy_metric.query_fp,
            query_unk=happy_metric.query_unk,
            fp_gt=happy_metric.fp_gt,
            fp_al=happy_metric.fp_al,
            metric_recall=happy_metric.metric_recall,
            metric_precision=happy_metric.metric_precision,
            metric_frac_na=happy_metric.metric_frac_na,
            metric_f1_score=happy_metric.metric_f1_score,
            truth_titv_ratio=happy_metric.truth_titv_ratio,
            query_titv_ratio=happy_metric.query_titv_ratio,
            truth_het_hom_ratio=happy_metric.truth_het_hom_ratio,
            query_het_hom_ratio=happy_metric.query_het_hom_ratio,
            run_id=happy_metric.run_id
        )
        db.add(db_happy_metric)
        db.commit()
        db.refresh(db_happy_metric)
        return db_happy_metric
    except Exception as e:
        db.rollback()
        raise e

def get_happy_metrics(db: Session, run_id: int) -> list[models.HappyMetric]:
    """Get all Happy metrics for a run."""
    return db.query(models.HappyMetric).filter(models.HappyMetric.run_id == run_id).all()

def delete_happy_metric(db: Session, metric_id: int) -> bool:
    """Delete a Happy metric by ID. Returns True if deleted, False if not found."""
    happy_metric = db.query(models.HappyMetric).filter(models.HappyMetric.id == metric_id).first()
    if happy_metric:
        db.delete(happy_metric)
        db.commit()
        return True
    return False


# Truvari Metrics

def create_truvari_metric(db: Session, truvari_metric: schemas.TruvariMetricCreate) -> models.TruvariMetric:
    """Create or replace the Truvari metric row for a run."""
    try:
        existing = (
            db.query(models.TruvariMetric)
            .filter(models.TruvariMetric.run_id == truvari_metric.run_id)
            .first()
        )
        values = truvari_metric.model_dump()
        if existing:
            for field, value in values.items():
                setattr(existing, field, value)
            db.commit()
            db.refresh(existing)
            return existing

        db_truvari_metric = models.TruvariMetric(**values)
        db.add(db_truvari_metric)
        db.commit()
        db.refresh(db_truvari_metric)
        return db_truvari_metric
    except Exception as e:
        db.rollback()
        raise e


def get_truvari_metrics(db: Session, run_id: int) -> list[models.TruvariMetric]:
    """Get all Truvari metrics for a run."""
    return db.query(models.TruvariMetric).filter(models.TruvariMetric.run_id == run_id).all()


def get_truvari_metric_by_run_name(db: Session, run_name: str) -> Optional[models.TruvariMetric]:
    """Get Truvari metric by run name."""
    lab_run = get_lab_run_by_name(db, run_name)
    if not lab_run:
        return None
    return db.query(models.TruvariMetric).filter(models.TruvariMetric.run_id == lab_run.id).first()


def delete_truvari_metric(db: Session, metric_id: int) -> bool:
    """Delete a Truvari metric by ID. Returns True if deleted, False if not found."""
    truvari_metric = db.query(models.TruvariMetric).filter(models.TruvariMetric.id == metric_id).first()
    if truvari_metric:
        db.delete(truvari_metric)
        db.commit()
        return True
    return False
