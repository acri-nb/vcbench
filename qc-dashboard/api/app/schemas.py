from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from api.app.models import RunStatus, FileTypeEnum

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
