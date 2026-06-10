from __future__ import annotations

import logging

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import Job, JobSource, ScrapeRun

logger = logging.getLogger(__name__)


def mark_stale_jobs_inactive(db: Session, source: str) -> int:
    """Deactivate jobs not seen in the last 2 successful runs of `source`.

    Only jobs whose every source row is stale go inactive; a job still being
    served by another board stays active.
    """
    runs = db.scalars(
        select(ScrapeRun.started_at)
        .where(ScrapeRun.source == source, ScrapeRun.status == "ok")
        .order_by(ScrapeRun.started_at.desc())
        .limit(2)
    ).all()
    if len(runs) < 2:
        return 0
    threshold = runs[-1]

    stale_job_ids = db.scalars(
        select(JobSource.job_id).where(
            JobSource.source == source, JobSource.last_seen_at < threshold
        )
    ).all()
    if not stale_job_ids:
        return 0

    # Keep jobs that some other source has seen recently
    fresh_job_ids = set(
        db.scalars(
            select(JobSource.job_id).where(
                JobSource.job_id.in_(stale_job_ids),
                JobSource.last_seen_at >= threshold,
            )
        ).all()
    )
    to_deactivate = [jid for jid in stale_job_ids if jid not in fresh_job_ids]
    if not to_deactivate:
        return 0

    result = db.execute(
        update(Job)
        .where(Job.id.in_(to_deactivate), Job.is_active.is_(True))
        .values(is_active=False)
    )
    if result.rowcount:
        logger.info("%s: marked %s jobs inactive", source, result.rowcount)
    return result.rowcount or 0
