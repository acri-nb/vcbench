from sqlalchemy import (BigInteger, Boolean, Column, Integer, String, Float, DateTime,
                        Text, UniqueConstraint, ForeignKey, Enum as SQLAlchemyEnum,
                        JSON)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid

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


def enum_values(enum_class):
    return [item.value for item in enum_class]


class TransferJobType(str, enum.Enum):
    UPLOAD_ZIP = "upload_zip"
    AWS_IMPORT = "aws_import"
    PIPELINE = "pipeline"


class TransferJobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class TransferJobPhase(str, enum.Enum):
    UPLOAD = "upload"
    DOWNLOAD = "download"
    VALIDATE = "validate"
    EXTRACT = "extract"
    REFERENCE_SETUP = "reference_setup"
    PROCESS = "process"
    COMPLETE = "complete"


class TransferEventLevel(str, enum.Enum):
    INFO = "info"
    PROGRESS = "progress"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

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
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by = relationship("User")

    # Relations
    qc_metrics = relationship("QCMetric", back_populates="run", cascade="all, delete-orphan")
    happy_metrics = relationship("HappyMetric", back_populates="run", cascade="all, delete-orphan")
    truvari_metrics = relationship("TruvariMetric", back_populates="run", cascade="all, delete-orphan")


class TransferJob(Base):
    __tablename__ = "transfer_jobs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    type = Column(
        SQLAlchemyEnum(
            TransferJobType,
            values_callable=enum_values,
            name="transferjobtype",
        ),
        nullable=False,
        index=True,
    )
    subject_id = Column(String, nullable=False, index=True)
    status = Column(
        SQLAlchemyEnum(
            TransferJobStatus,
            values_callable=enum_values,
            name="transferjobstatus",
        ),
        nullable=False,
        default=TransferJobStatus.QUEUED,
        index=True,
    )
    phase = Column(
        SQLAlchemyEnum(
            TransferJobPhase,
            values_callable=enum_values,
            name="transferjobphase",
        ),
        nullable=True,
        index=True,
    )
    source_uri = Column(String, nullable=True)
    destination_path = Column(String, nullable=True)
    bytes_total = Column(BigInteger, nullable=True)
    bytes_done = Column(BigInteger, nullable=False, default=0)
    rate_bps = Column(BigInteger, nullable=True)
    eta_seconds = Column(Integer, nullable=True)
    started_at = Column(DateTime, server_default=func.now(), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_code = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    cancel_requested = Column(Boolean, nullable=False, default=False)
    metadata_json = Column("metadata", JSON, nullable=True)

    events = relationship(
        "TransferEvent",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="TransferEvent.sequence",
    )


class TransferEvent(Base):
    __tablename__ = "transfer_events"
    __table_args__ = (UniqueConstraint("job_id", "sequence", name="unique_transfer_event_sequence"),)
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, ForeignKey("transfer_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    timestamp = Column(DateTime, server_default=func.now(), nullable=True)
    level = Column(
        SQLAlchemyEnum(
            TransferEventLevel,
            values_callable=enum_values,
            name="transfereventlevel",
        ),
        nullable=False,
        default=TransferEventLevel.INFO,
    )
    phase = Column(
        SQLAlchemyEnum(
            TransferJobPhase,
            values_callable=enum_values,
            name="transferjobphase",
        ),
        nullable=True,
    )
    message = Column(Text, nullable=False)
    bytes_done = Column(BigInteger, nullable=True)
    bytes_total = Column(BigInteger, nullable=True)
    rate_bps = Column(BigInteger, nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True)

    job = relationship("TransferJob", back_populates="events")

class QCMetric(Base):
    __tablename__ = "qc_metrics"
    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String, index=True, nullable=True)
    metric_value = Column(Float, nullable=True)
    file_source = Column(String, nullable=False) # ex: 'mapping_metrics.csv'
    
    run_id = Column(Integer, ForeignKey("lab_runs.id", ondelete="CASCADE"))
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
    
    run_id = Column(Integer, ForeignKey("lab_runs.id", ondelete="CASCADE"))
    run = relationship("LabRun", back_populates="happy_metrics")


class TruvariMetric(Base):
    __tablename__ = "truvari_metrics"
    __table_args__ = (UniqueConstraint("run_id", name="unique_run_truvari"),)
    id = Column(Integer, primary_key=True, index=True)

    tp_base = Column(Integer, nullable=False)
    tp_comp = Column(Integer, nullable=False)
    fp = Column(Integer, nullable=False)
    fn = Column(Integer, nullable=False)
    precision = Column(Float, nullable=False)
    recall = Column(Float, nullable=False)
    f1 = Column(Float, nullable=False)
    base_cnt = Column(Integer, nullable=False)
    comp_cnt = Column(Integer, nullable=False)
    gt_concordance = Column(Float, nullable=False)
    tp_comp_tp_gt = Column(Integer, nullable=False)
    tp_comp_fp_gt = Column(Integer, nullable=False)
    tp_base_tp_gt = Column(Integer, nullable=False)
    tp_base_fp_gt = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    run_id = Column(Integer, ForeignKey("lab_runs.id", ondelete="CASCADE"), nullable=False)
    run = relationship("LabRun", back_populates="truvari_metrics")
