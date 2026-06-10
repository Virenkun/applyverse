"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

TSV_EXPR = (
    "to_tsvector('english', coalesce(title, '') || ' ' || "
    "coalesce(immutable_array_to_string(tags, ' '), '') || ' ' || "
    "coalesce(location, '') || ' ' || coalesce(description, ''))"
)


def upgrade() -> None:
    # array_to_string is only STABLE, generated columns need IMMUTABLE
    op.execute(
        "CREATE OR REPLACE FUNCTION immutable_array_to_string(text[], text) "
        "RETURNS text AS $$ SELECT array_to_string($1, $2) $$ "
        "LANGUAGE sql IMMUTABLE"
    )

    op.create_table(
        "companies",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("website", sa.String(500)),
        sa.Column("logo_url", sa.String(1000)),
        sa.Column("ats_type", sa.String(50)),
        sa.Column("ats_board_id", sa.String(200)),
        sa.Column("glassdoor_rating", sa.Float()),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column(
            "company_id", sa.BigInteger(), sa.ForeignKey("companies.id"), nullable=False
        ),
        sa.Column("location", sa.String(300)),
        sa.Column("work_mode", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("salary_min", sa.BigInteger()),
        sa.Column("salary_max", sa.BigInteger()),
        sa.Column("currency", sa.String(10)),
        sa.Column("description", sa.Text()),
        sa.Column("tags", ARRAY(sa.String())),
        sa.Column("canonical_url", sa.String(1000)),
        sa.Column("posted_at", sa.DateTime(timezone=True)),
        sa.Column(
            "scraped_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("dedupe_hash", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("search_tsv", TSVECTOR(), sa.Computed(TSV_EXPR, persisted=True)),
    )
    op.create_index("ix_jobs_dedupe_hash", "jobs", ["dedupe_hash"], unique=True)
    op.create_index("ix_jobs_search_tsv", "jobs", ["search_tsv"], postgresql_using="gin")
    op.create_index("ix_jobs_posted_at", "jobs", ["posted_at"])
    op.create_index("ix_jobs_active_hidden", "jobs", ["is_active", "is_hidden"])

    op.create_table(
        "job_sources",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "job_id",
            sa.BigInteger(),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("source_job_id", sa.String(300), nullable=False),
        sa.Column("url", sa.String(1000)),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("source", "source_job_id", name="uq_job_sources_source_id"),
    )
    op.create_index("ix_job_sources_source", "job_sources", ["source"])
    op.create_index("ix_job_sources_job_id", "job_sources", ["job_id"])

    op.create_table(
        "applications",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "job_id",
            sa.BigInteger(),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="saved"),
        sa.Column("applied_at", sa.DateTime(timezone=True)),
        sa.Column("resume_version", sa.String(200)),
        sa.Column(
            "cover_letter_used", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("notes", sa.Text()),
        sa.Column("next_followup_at", sa.DateTime(timezone=True)),
        sa.Column("status_history", JSONB(), nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_applications_status", "applications", ["status"])

    op.create_table(
        "scrape_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("jobs_found", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("jobs_new", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("jobs_updated", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("error", sa.Text()),
    )
    op.create_index("ix_scrape_runs_source", "scrape_runs", ["source"])


def downgrade() -> None:
    op.drop_table("scrape_runs")
    op.drop_table("applications")
    op.drop_table("job_sources")
    op.drop_table("jobs")
    op.drop_table("companies")
    op.execute("DROP FUNCTION IF EXISTS immutable_array_to_string(text[], text)")
