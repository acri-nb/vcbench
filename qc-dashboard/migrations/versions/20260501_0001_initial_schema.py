"""initial schema

Revision ID: 20260501_0001
Revises:
Create Date: 2026-05-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect


revision = "20260501_0001"
down_revision = None
branch_labels = None
depends_on = None


RUN_STATUS_VALUES = (
    "PENDING_PROCESSING",
    "PROCESSING",
    "AWAITING_APPROVAL",
    "APPROVED",
    "FAILED",
)


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    return inspect(bind).has_table(table_name)


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    return {column["name"] for column in inspect(bind).get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def _create_runstatus_type() -> sa.Enum:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        run_status = postgresql.ENUM(*RUN_STATUS_VALUES, name="runstatus", create_type=True)
        run_status.create(bind, checkfirst=True)
        return postgresql.ENUM(*RUN_STATUS_VALUES, name="runstatus", create_type=False)
    return sa.Enum(*RUN_STATUS_VALUES, name="runstatus")


def upgrade() -> None:
    run_status = _create_runstatus_type()

    if not _has_table("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("username", sa.String(), nullable=False),
            sa.Column("full_name", sa.String(), nullable=True),
            sa.Column("hashed_password", sa.String(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("username"),
        )
        op.create_index("ix_users_id", "users", ["id"])
        op.create_index("ix_users_username", "users", ["username"], unique=True)

    if not _has_table("lab_runs"):
        op.create_table(
            "lab_runs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("run_name", sa.String(), nullable=False),
            sa.Column("status", run_status, nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("processing_started_at", sa.DateTime(), nullable=True),
            sa.Column("processing_completed_at", sa.DateTime(), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("approved_by_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["approved_by_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("run_name"),
        )
        op.create_index("ix_lab_runs_id", "lab_runs", ["id"])
        op.create_index("ix_lab_runs_run_name", "lab_runs", ["run_name"], unique=True)
    else:
        _add_column_if_missing("lab_runs", sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True))
        _add_column_if_missing("lab_runs", sa.Column("processing_started_at", sa.DateTime(), nullable=True))
        _add_column_if_missing("lab_runs", sa.Column("processing_completed_at", sa.DateTime(), nullable=True))
        _add_column_if_missing("lab_runs", sa.Column("error_message", sa.Text(), nullable=True))

    if not _has_table("qc_metrics"):
        op.create_table(
            "qc_metrics",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("metric_name", sa.String(), nullable=True),
            sa.Column("metric_value", sa.Float(), nullable=True),
            sa.Column("file_source", sa.String(), nullable=False),
            sa.Column("run_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["run_id"], ["lab_runs.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_qc_metrics_id", "qc_metrics", ["id"])
        op.create_index("ix_qc_metrics_metric_name", "qc_metrics", ["metric_name"])

    if not _has_table("happy_metrics"):
        op.create_table(
            "happy_metrics",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("type", sa.String(), nullable=False),
            sa.Column("filter", sa.String(), nullable=False),
            sa.Column("truth_total", sa.Integer(), nullable=False),
            sa.Column("truth_tp", sa.Integer(), nullable=False),
            sa.Column("truth_fn", sa.Integer(), nullable=False),
            sa.Column("query_total", sa.Integer(), nullable=False),
            sa.Column("query_fp", sa.Integer(), nullable=False),
            sa.Column("query_unk", sa.Integer(), nullable=False),
            sa.Column("fp_gt", sa.Float(), nullable=False),
            sa.Column("fp_al", sa.Float(), nullable=False),
            sa.Column("metric_recall", sa.Float(), nullable=False),
            sa.Column("metric_precision", sa.Float(), nullable=False),
            sa.Column("metric_frac_na", sa.Float(), nullable=False),
            sa.Column("metric_f1_score", sa.Float(), nullable=False),
            sa.Column("truth_titv_ratio", sa.Float(), nullable=False),
            sa.Column("query_titv_ratio", sa.Float(), nullable=False),
            sa.Column("truth_het_hom_ratio", sa.Float(), nullable=False),
            sa.Column("query_het_hom_ratio", sa.Float(), nullable=False),
            sa.Column("run_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["run_id"], ["lab_runs.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_happy_metrics_id", "happy_metrics", ["id"])


def downgrade() -> None:
    for table_name in ("happy_metrics", "qc_metrics", "lab_runs", "users"):
        if _has_table(table_name):
            op.drop_table(table_name)

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        postgresql.ENUM(*RUN_STATUS_VALUES, name="runstatus").drop(bind, checkfirst=True)
