from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Application, Company, Job
from app.schemas import CompanyWithCounts, JobListItem
from app.api.jobs import _base_query, to_list_item

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanyWithCounts])
def list_companies(
    db: Session = Depends(get_db), applied_only: bool = False
) -> list[CompanyWithCounts]:
    open_jobs = (
        select(Job.company_id, func.count(Job.id).label("open_jobs"))
        .where(Job.is_active.is_(True), Job.is_hidden.is_(False))
        .group_by(Job.company_id)
        .subquery()
    )
    apps = (
        select(Job.company_id, func.count(Application.id).label("applications"))
        .join(Application, Application.job_id == Job.id)
        .group_by(Job.company_id)
        .subquery()
    )
    query = (
        select(
            Company,
            func.coalesce(open_jobs.c.open_jobs, 0),
            func.coalesce(apps.c.applications, 0),
        )
        .outerjoin(open_jobs, open_jobs.c.company_id == Company.id)
        .outerjoin(apps, apps.c.company_id == Company.id)
        .order_by(func.coalesce(open_jobs.c.open_jobs, 0).desc(), Company.name)
    )
    if applied_only:
        query = query.where(func.coalesce(apps.c.applications, 0) > 0)
    rows = db.execute(query).all()
    result = []
    for company, open_count, app_count in rows:
        out = CompanyWithCounts.model_validate(company)
        out.open_jobs = open_count
        out.applications = app_count
        result.append(out)
    return result


@router.get("/{company_id}/jobs", response_model=list[JobListItem])
def company_jobs(company_id: int, db: Session = Depends(get_db)) -> list[JobListItem]:
    if db.get(Company, company_id) is None:
        raise HTTPException(404, "company not found")
    jobs = (
        db.scalars(
            _base_query()
            .where(Job.company_id == company_id, Job.is_active.is_(True))
            .order_by(Job.posted_at.desc().nulls_last())
        )
        .unique()
        .all()
    )
    return [to_list_item(j) for j in jobs]
