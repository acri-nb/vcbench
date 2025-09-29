from sqlalchemy import (Column, Integer, String, Float, DateTime,
                        ForeignKey, Enum as SQLAlchemyEnum)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from api.app.database import Base

class RunStatus(str, enum.Enum):
    PENDING_PROCESSING = "PENDING_PROCESSING"
    PROCESSING = "PROCESSING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    FAILED = "FAILED"

class FileTypeEnum(str, enum.Enum):
    Summary              = "Summary"
    Metrics              = "Metrics"
    VC_metrics           = "VC_metrics"
    CNV_metrics          = "CNV_metrics"
    ROH_metrics          = "ROH_metrics"
    HeThom               = "HeThom"
    Ploidy               = "Ploidy"
    bed_coverage         = "bed_coverage"
    WGS_contig_mean_cov  = "WGS_contig_mean_cov"
    mapping_metrics      = "mapping_metrics"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)

class LabRun(Base):
    __tablename__ = "lab_runs"
    id = Column(Integer, primary_key=True, index=True)
    run_name = Column(String, unique=True, index=True, nullable=False)
    status = Column(SQLAlchemyEnum(RunStatus), nullable=False, default=RunStatus.PENDING_PROCESSING)
    
    created_at = Column(DateTime, server_default=func.now())
    approved_at = Column(DateTime, nullable=True)
    
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by = relationship("User")

    # Relations
    qc_metrics = relationship("QCMetric", back_populates="run")
    happy_metrics = relationship("HappyMetric", back_populates="run")

class QCMetric(Base):
    __tablename__ = "qc_metrics"
    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String, index=True, nullable=True)
    metric_value = Column(Float, nullable=True)
    file_source = Column(String, nullable=False) # ex: 'mapping_metrics.csv'
    
    run_id = Column(Integer, ForeignKey("lab_runs.id"))
    run = relationship("LabRun", back_populates="qc_metrics")

class HappyMetric(Base):
    __tablename__ = "happy_metrics"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)
    filter = Column(String, nullable=False)
    truth_total = Column(Integer, nullable=False)
    truth_tp = Column(Integer, nullable=False)
    truth_fn = Column(Integer, nullable=False)
    query_total = Column(Integer, nullable=False)
    query_fp = Column(Integer, nullable=False)
    query_unk = Column(Integer, nullable=False)
    fp_gt = Column(Float, nullable=False)
    fp_al = Column(Float, nullable=False)
    metric_recall = Column(Float, nullable=False)
    metric_precision = Column(Float, nullable=False)
    metric_frac_na = Column(Float, nullable=False)
    metric_f1_score = Column(Float, nullable=False)
    truth_titv_ratio = Column(Float, nullable=False)
    query_titv_ratio = Column(Float, nullable=False)
    truth_het_hom_ratio = Column(Float, nullable=False)
    query_het_hom_ratio = Column(Float, nullable=False)
    
    run_id = Column(Integer, ForeignKey("lab_runs.id"))
    run = relationship("LabRun", back_populates="happy_metrics")