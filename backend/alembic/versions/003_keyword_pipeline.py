"""keyword pipeline: skipped counter + ats discovery probe timestamp

Revision ID: 003
Revises: 002
Create Date: 2026-06-10

"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scrape_runs",
        sa.Column("jobs_skipped", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "companies", sa.Column("ats_probed_at", sa.DateTime(timezone=True))
    )


def downgrade() -> None:
    op.drop_column("companies", "ats_probed_at")
    op.drop_column("scrape_runs", "jobs_skipped")
