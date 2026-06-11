from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import Company, Job, JobSource
from app.schemas import JobDetail, JobListItem, JobListResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])

SNIPPET_LEN = 240

# Title-derived facets. Values are POSIX regex alternations matched
# case-insensitively with word boundaries (\m..\M) against the job title.
SENIORITY_PATTERNS: dict[str, str] = {
    "intern": r"\m(intern|internship|trainee|apprentice)",
    "junior": r"\m(junior|jr|entry[- ]level|graduate|grad)\M",
    "mid": r"\m(mid|ii|2)\M",
    "senior": r"\m(senior|sr|iii|3)\M",
    "staff": r"\m(staff)\M",
    "lead": r"\m(lead|principal|architect|distinguished|head)\M",
}
ROLE_PATTERNS: dict[str, str] = {
    "frontend": r"\m(frontend|front[- ]end|react|angular|vue|ui)\M",
    "backend": r"\m(backend|back[- ]end|server[- ]side)\M",
    "fullstack": r"\m(full[- ]?stack)\M",
    "mobile": r"\m(mobile|ios|android|react native|flutter|swift|kotlin)\M",
    "devops": r"\m(devops|sre|site reliability|platform|infrastructure|cloud)\M",
    "data": r"\m(data engineer|data scientist|data analyst|analytics|etl|bi)\M",
    "ml": r"\m(machine learning|ml|ai|deep learning|nlp|computer vision)\M",
    "qa": r"\m(qa|sdet|test|quality|automation)\M",
    "security": r"\m(security|appsec|infosec|cyber)\M",
    "embedded": r"\m(embedded|firmware|iot)\M",
}


def to_list_item(job: Job) -> JobListItem:
    item = JobListItem.model_validate(job)
    if job.description:
        item.description_snippet = job.description[:SNIPPET_LEN]
    return item


def _base_query():
    return select(Job).options(
        selectinload(Job.company),
        selectinload(Job.sources),
        selectinload(Job.application),
    )


@router.get("", response_model=JobListResponse)
def list_jobs(
    db: Session = Depends(get_db),
    q: str | None = None,
    location: str | None = None,
    work_mode: str | None = None,
    seniority: str | None = None,
    role: str | None = None,
    source: str | None = None,
    company_id: int | None = None,
    tag: str | None = None,
    posted_after: datetime | None = None,
    salary_min: int | None = None,
    active: bool = True,
    include_hidden: bool = False,
    saved_only: bool = False,
    sort: str = Query("posted_at", pattern="^(posted_at|scraped_at|title)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> JobListResponse:
    query = _base_query()
    filters = []
    if q:
        filters.append(Job.search_tsv.op("@@")(func.websearch_to_tsquery("english", q)))
    if location:
        filters.append(Job.location.ilike(f"%{location}%"))
    if work_mode:
        filters.append(Job.work_mode == work_mode)
    if seniority and seniority in SENIORITY_PATTERNS:
        filters.append(Job.title.op("~*")(SENIORITY_PATTERNS[seniority]))
    if role and role in ROLE_PATTERNS:
        filters.append(Job.title.op("~*")(ROLE_PATTERNS[role]))
    if company_id:
        filters.append(Job.company_id == company_id)
    if tag:
        filters.append(Job.tags.any(tag))
    if posted_after:
        filters.append(Job.posted_at >= posted_after)
    if salary_min:
        filters.append(Job.salary_max >= salary_min)
    if active:
        filters.append(Job.is_active.is_(True))
    if not include_hidden:
        filters.append(Job.is_hidden.is_(False))
    if source:
        filters.append(
            Job.id.in_(select(JobSource.job_id).where(JobSource.source == source))
        )
    if saved_only:
        filters.append(Job.application.has())

    query = query.where(*filters)
    total = db.scalar(select(func.count()).select_from(Job).where(*filters)) or 0

    sort_col = {
        "posted_at": Job.posted_at,
        "scraped_at": Job.scraped_at,
        "title": Job.title,
    }[sort]
    order = sort_col.asc() if sort == "title" else sort_col.desc().nulls_last()
    jobs = (
        db.scalars(
            query.order_by(order, Job.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .unique()
        .all()
    )
    return JobListResponse(
        items=[to_list_item(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/filters")
def filter_options(db: Session = Depends(get_db)) -> dict:
    sources = db.scalars(select(JobSource.source).distinct()).all()
    companies = db.execute(
        select(Company.id, Company.name)
        .join(Job, Job.company_id == Company.id)
        .where(Job.is_active.is_(True))
        .distinct()
        .order_by(Company.name)
    ).all()
    return {
        "sources": sorted(sources),
        "work_modes": ["remote", "hybrid", "onsite", "unknown"],
        "seniorities": list(SENIORITY_PATTERNS),
        "roles": list(ROLE_PATTERNS),
        "companies": [{"id": c.id, "name": c.name} for c in companies],
    }


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobDetail:
    job = db.scalar(_base_query().where(Job.id == job_id))
    if job is None:
        raise HTTPException(404, "job not found")
    detail = JobDetail.model_validate(job)
    if job.description:
        detail.description_snippet = job.description[:SNIPPET_LEN]
    return detail


@router.post("/{job_id}/hide")
def hide_job(job_id: int, db: Session = Depends(get_db)) -> dict:
    return _set_hidden(db, job_id, True)


@router.post("/{job_id}/unhide")
def unhide_job(job_id: int, db: Session = Depends(get_db)) -> dict:
    return _set_hidden(db, job_id, False)


def _set_hidden(db: Session, job_id: int, hidden: bool) -> dict:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    job.is_hidden = hidden
    db.commit()
    return {"id": job_id, "is_hidden": hidden}
