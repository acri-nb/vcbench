"""add transfer jobs

Revision ID: 20260527_0003
Revises: 20260501_0002
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "20260527_0003"
down_revision = "20260501_0002"
branch_labels = None
depends_on = None


JOB_TYPE_VALUES = ("upload_zip", "aws_import", "pipeline")
JOB_STATUS_VALUES = ("queued", "running", "completed", "failed", "canceled")
JOB_PHASE_VALUES = ("upload", "download", "validate", "extract", "reference_setup", "process", "complete")
EVENT_LEVEL_VALUES = ("info", "progress", "success", "warning", "error")


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    return inspect(bind).has_table(table_name)


def _enum(name: str, values: tuple[str, ...]) -> sa.Enum:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        enum_type = postgresql.ENUM(*values, name=name, create_type=True)
        enum_type.create(bind, checkfirst=True)
        return postgresql.ENUM(*values, name=name, create_type=False)
    return sa.Enum(*values, name=name)


def upgrade() -> None:
    job_type = _enum("transferjobtype", JOB_TYPE_VALUES)
    job_status = _enum("transferjobstatus", JOB_STATUS_VALUES)
    job_phase = _enum("transferjobphase", JOB_PHASE_VALUES)
    event_level = _enum("transfereventlevel", EVENT_LEVEL_VALUES)

    if not _has_table("transfer_jobs"):
        op.create_table(
            "transfer_jobs",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("type", job_type, nullable=False),
            sa.Column("subject_id", sa.String(), nullable=False),
            sa.Column("status", job_status, nullable=False),
            sa.Column("phase", job_phase, nullable=True),
            sa.Column("source_uri", sa.String(), nullable=True),
            sa.Column("destination_path", sa.String(), nullable=True),
            sa.Column("bytes_total", sa.BigInteger(), nullable=True),
            sa.Column("bytes_done", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("rate_bps", sa.BigInteger(), nullable=True),
            sa.Column("eta_seconds", sa.Integer(), nullable=True),
            sa.Column("started_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("error_code", sa.String(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("metadata", sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_transfer_jobs_id", "transfer_jobs", ["id"])
        op.create_index("ix_transfer_jobs_type", "transfer_jobs", ["type"])
        op.create_index("ix_transfer_jobs_subject_id", "transfer_jobs", ["subject_id"])
        op.create_index("ix_transfer_jobs_status", "transfer_jobs", ["status"])
        op.create_index("ix_transfer_jobs_phase", "transfer_jobs", ["phase"])

    if not _has_table("transfer_events"):
        op.create_table(
            "transfer_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("job_id", sa.String(), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("timestamp", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("level", event_level, nullable=False),
            sa.Column("phase", job_phase, nullable=True),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("bytes_done", sa.BigInteger(), nullable=True),
            sa.Column("bytes_total", sa.BigInteger(), nullable=True),
            sa.Column("rate_bps", sa.BigInteger(), nullable=True),
            sa.Column("metadata", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(["job_id"], ["transfer_jobs.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("job_id", "sequence", name="unique_transfer_event_sequence"),
        )
        op.create_index("ix_transfer_events_id", "transfer_events", ["id"])
        op.create_index("ix_transfer_events_job_id", "transfer_events", ["job_id"])


def downgrade() -> None:
    for table_name in ("transfer_events", "transfer_jobs"):
        if _has_table(table_name):
            op.drop_table(table_name)

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for name, values in (
            ("transfereventlevel", EVENT_LEVEL_VALUES),
            ("transferjobphase", JOB_PHASE_VALUES),
            ("transferjobstatus", JOB_STATUS_VALUES),
            ("transferjobtype", JOB_TYPE_VALUES),
        ):
            postgresql.ENUM(*values, name=name).drop(bind, checkfirst=True)
