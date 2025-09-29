from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from api.app.models import RunStatus, FileTypeEnum

# User

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    full_name: Optional[str] = None
    hashed_password: str

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
    approved_at: Optional[datetime] = None
    approved_by_id: Optional[int] = None

    class Config:
        from_attributes = True

class LabRunUpdate(BaseModel):
    status: Optional[RunStatus] = None
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None

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
    recall: float
    precision: float
    frac_na: float
    f1_score: float

class HappyMetricCreate(HappyMetricBase):
    run_id: int

class HappyMetricResponse(HappyMetricBase):
    id: int
    run_id: int

    class Config:
        from_attributes = True
