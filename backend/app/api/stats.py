from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Application, Job
from app.schemas import StatsOverview, TimelinePoint

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview", response_model=StatsOverview)
def overview(db: Session = Depends(get_db)) -> StatsOverview:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())

    jobs_new_today = (
        db.scalar(select(func.count()).select_from(Job).where(Job.scraped_at >= today_start))
        or 0
    )
    jobs_active = (
        db.scalar(
            select(func.count())
            .select_from(Job)
            .where(Job.is_active.is_(True), Job.is_hidden.is_(False))
        )
        or 0
    )
    applications_total = db.scalar(select(func.count()).select_from(Application)) or 0
    applied_this_week = (
        db.scalar(
            select(func.count())
            .select_from(Application)
            .where(Application.applied_at >= week_start)
        )
        or 0
    )
    interviewing = (
        db.scalar(
            select(func.count())
            .select_from(Application)
            .where(Application.status == "interviewing")
        )
        or 0
    )
    offers = (
        db.scalar(
            select(func.count())
            .select_from(Application)
            .where(Application.status == "offer")
        )
        or 0
    )
    beyond_saved = (
        db.scalar(
            select(func.count())
            .select_from(Application)
            .where(Application.status != "saved")
        )
        or 0
    )
    responded = (
        db.scalar(
            select(func.count())
            .select_from(Application)
            .where(Application.status.in_(["interviewing", "offer", "rejected"]))
        )
        or 0
    )
    followups_due = (
        db.scalar(
            select(func.count())
            .select_from(Application)
            .where(Application.next_followup_at <= now)
        )
        or 0
    )
    return StatsOverview(
        jobs_new_today=jobs_new_today,
        jobs_active=jobs_active,
        applications_total=applications_total,
        applied_this_week=applied_this_week,
        interviewing=interviewing,
        offers=offers,
        response_rate=round(responded / beyond_saved, 3) if beyond_saved else None,
        followups_due=followups_due,
    )


@router.get("/timeline", response_model=list[TimelinePoint])
def timeline(days: int = 30, db: Session = Depends(get_db)) -> list[TimelinePoint]:
    start = (
        datetime.now(timezone.utc) - timedelta(days=days - 1)
    ).replace(hour=0, minute=0, second=0, microsecond=0)

    app_rows = dict(
        db.execute(
            select(
                func.date(Application.applied_at).label("d"), func.count()
            )
            .where(Application.applied_at >= start)
            .group_by("d")
        ).all()
    )
    job_rows = dict(
        db.execute(
            select(func.date(Job.scraped_at).label("d"), func.count())
            .where(Job.scraped_at >= start)
            .group_by("d")
        ).all()
    )
    points = []
    for i in range(days):
        day = (start + timedelta(days=i)).date()
        points.append(
            TimelinePoint(
                date=day.isoformat(),
                applications=app_rows.get(day, 0),
                jobs_scraped=job_rows.get(day, 0),
            )
        )
    return points
