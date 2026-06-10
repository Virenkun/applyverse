from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, Job, JobSource
from app.scrapers.base import RawJob


def slugify(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def dedupe_hash(title: str, company_name: str, location: str | None) -> str:
    key = f"{slugify(title)}|{slugify(company_name)}|{slugify(location)}"
    return hashlib.sha256(key.encode()).hexdigest()


def get_or_create_company(db: Session, name: str) -> Company:
    company = db.scalar(select(Company).where(Company.name == name))
    if company is None:
        company = Company(name=name)
        db.add(company)
        db.flush()
    return company


def upsert_job(db: Session, raw: RawJob, company: Company | None = None) -> str:
    """Insert or refresh one scraped job.

    Returns "new" (job created), "updated" (same source seen again) or
    "linked" (job already known from another source).
    """
    now = datetime.now(timezone.utc)

    existing_source = db.scalar(
        select(JobSource).where(
            JobSource.source == raw.source,
            JobSource.source_job_id == raw.source_job_id,
        )
    )
    if existing_source is not None:
        existing_source.last_seen_at = now
        existing_source.url = raw.url or existing_source.url
        job = existing_source.job
        job.last_seen_at = now
        job.is_active = True
        # Refresh mutable fields that boards edit in place
        job.title = raw.title or job.title
        job.location = raw.location or job.location
        job.description = raw.description or job.description
        job.description_html = raw.description_html or job.description_html
        job.salary_min = raw.salary_min if raw.salary_min is not None else job.salary_min
        job.salary_max = raw.salary_max if raw.salary_max is not None else job.salary_max
        job.currency = raw.currency or job.currency
        return "updated"

    if company is None:
        company = get_or_create_company(db, raw.company_name)

    job_hash = dedupe_hash(raw.title, company.name, raw.location)
    existing_job = db.scalar(select(Job).where(Job.dedupe_hash == job_hash))
    if existing_job is not None:
        # Same job already known from another board — just link the source
        existing_job.last_seen_at = now
        existing_job.is_active = True
        db.add(
            JobSource(
                job_id=existing_job.id,
                source=raw.source,
                source_job_id=raw.source_job_id,
                url=raw.url,
                last_seen_at=now,
            )
        )
        return "linked"

    job = Job(
        title=raw.title,
        company_id=company.id,
        location=raw.location,
        work_mode=raw.work_mode,
        salary_min=raw.salary_min,
        salary_max=raw.salary_max,
        currency=raw.currency,
        description=raw.description,
        description_html=raw.description_html,
        tags=raw.tags or None,
        canonical_url=raw.url,
        posted_at=raw.posted_at,
        last_seen_at=now,
        dedupe_hash=job_hash,
    )
    db.add(job)
    db.flush()
    db.add(
        JobSource(
            job_id=job.id,
            source=raw.source,
            source_job_id=raw.source_job_id,
            url=raw.url,
            last_seen_at=now,
        )
    )
    return "new"
