from sqlalchemy.orm import Session
from typing import Optional

from api.app import models
from api.app import schemas

# Users

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    """Create a new user in the database."""
    try:
        db_user = models.User(**user.model_dump())
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
    return db.query(models.LabRun).all()

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

def update_lab_run_status(db: Session, run_id: int, status: models.RunStatus) -> Optional[models.LabRun]:
    """Update the status of a lab run."""
    lab_run = db.query(models.LabRun).filter(models.LabRun.id == run_id).first()
    if lab_run:
        lab_run.status = status
        db.commit()
        db.refresh(lab_run)
        return lab_run
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

def delete_qc_metric(db: Session, metric_id: int) -> bool:
    """Delete a QC metric by ID. Returns True if deleted, False if not found."""
    qc_metric = db.query(models.QCMetric).filter(models.QCMetric.id == metric_id).first()
    if qc_metric:
        db.delete(qc_metric)
        db.commit()
        return True
    return False

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