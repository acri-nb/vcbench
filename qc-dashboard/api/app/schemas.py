from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from api.app.models import (
    FileTypeEnum,
    RunStatus,
    TransferEventLevel,
    TransferJobPhase,
    TransferJobStatus,
    TransferJobType,
)

# User

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    full_name: Optional[str] = None
    password: str

class UserResponse(UserBase):
    id: int
    full_name: Optional[str] = None

    class Config:
        from_attributes = True

# Lab Run

class LabRunBase(BaseModel):
    run_name: str
    status: RunStatus

class LabRunCreate(LabRunBase):
    pass

class LabRunResponse(LabRunBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    approved_by_id: Optional[int] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

class LabRunUpdate(BaseModel):
    status: Optional[RunStatus] = None
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    error_message: Optional[str] = None

# QC Metric

class QCMetricBase(BaseModel):
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    file_source: str
    run_id: int

class QCMetricCreate(QCMetricBase):
    pass

class QCMetricResponse(QCMetricBase):
    id: int

    class Config:
        from_attributes = True

# Happy Metric

class HappyMetricBase(BaseModel):
    type: str
    filter: str
    truth_total: int
    truth_tp: int
    truth_fn: int
    query_total: int
    query_fp: int
    query_unk: int
    fp_gt: float
    fp_al: float
    metric_recall: float
    metric_precision: float
    metric_frac_na: float
    metric_f1_score: float
    truth_titv_ratio: float
    query_titv_ratio: float
    truth_het_hom_ratio: float
    query_het_hom_ratio: float

class HappyMetricCreate(HappyMetricBase):
    run_id: int

class HappyMetricResponse(HappyMetricBase):
    id: int
    run_id: int

    class Config:
        from_attributes = True


# Truvari Metric

class TruvariMetricBase(BaseModel):
    tp_base: int
    tp_comp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float
    base_cnt: int
    comp_cnt: int
    gt_concordance: float
    tp_comp_tp_gt: int
    tp_comp_fp_gt: int
    tp_base_tp_gt: int
    tp_base_fp_gt: int

class TruvariMetricCreate(TruvariMetricBase):
    run_id: int

class TruvariMetricResponse(TruvariMetricBase):
    id: int
    run_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Transfer Jobs

class TransferJobBase(BaseModel):
    type: TransferJobType
    subject_id: str
    status: TransferJobStatus
    phase: Optional[TransferJobPhase] = None
    source_uri: Optional[str] = None
    destination_path: Optional[str] = None
    bytes_total: Optional[int] = None
    bytes_done: int = 0
    rate_bps: Optional[int] = None
    eta_seconds: Optional[int] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    cancel_requested: bool = False
    metadata_json: Optional[dict] = None


class TransferJobResponse(TransferJobBase):
    id: str
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TransferEventResponse(BaseModel):
    id: int
    job_id: str
    sequence: int
    timestamp: Optional[datetime] = None
    level: TransferEventLevel
    phase: Optional[TransferJobPhase] = None
    message: str
    bytes_done: Optional[int] = None
    bytes_total: Optional[int] = None
    rate_bps: Optional[int] = None
    metadata_json: Optional[dict] = None

    class Config:
        from_attributes = True


class TransferJobSummary(BaseModel):
    active_jobs: int
    queued_jobs: int
    failed_24h: int
    total_rate_bps: int
    disk_free_bytes: int
