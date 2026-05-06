"""add truvari metrics

Revision ID: 20260501_0002
Revises: 20260501_0001
Create Date: 2026-05-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260501_0002"
down_revision = "20260501_0001"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    return inspect(bind).has_table(table_name)


def upgrade() -> None:
    if _has_table("truvari_metrics"):
        return

    op.create_table(
        "truvari_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tp_base", sa.Integer(), nullable=False),
        sa.Column("tp_comp", sa.Integer(), nullable=False),
        sa.Column("fp", sa.Integer(), nullable=False),
        sa.Column("fn", sa.Integer(), nullable=False),
        sa.Column("precision", sa.Float(), nullable=False),
        sa.Column("recall", sa.Float(), nullable=False),
        sa.Column("f1", sa.Float(), nullable=False),
        sa.Column("base_cnt", sa.Integer(), nullable=False),
        sa.Column("comp_cnt", sa.Integer(), nullable=False),
        sa.Column("gt_concordance", sa.Float(), nullable=False),
        sa.Column("tp_comp_tp_gt", sa.Integer(), nullable=False),
        sa.Column("tp_comp_fp_gt", sa.Integer(), nullable=False),
        sa.Column("tp_base_tp_gt", sa.Integer(), nullable=False),
        sa.Column("tp_base_fp_gt", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["lab_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", name="unique_run_truvari"),
    )
    op.create_index("ix_truvari_metrics_id", "truvari_metrics", ["id"])
    op.create_index("idx_truvari_metrics_run_id", "truvari_metrics", ["run_id"])


def downgrade() -> None:
    if _has_table("truvari_metrics"):
        op.drop_table("truvari_metrics")
