from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import Application, ApplicationStatus, Job
from app.schemas import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationWithJob,
)
from app.api.jobs import to_list_item

router = APIRouter(prefix="/applications", tags=["applications"])

VALID_STATUSES = {s.value for s in ApplicationStatus}


def _to_out(app_row: Application) -> ApplicationWithJob:
    out = ApplicationWithJob.model_validate(app_row)
    out.job = to_list_item(app_row.job)
    return out


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _append_history(app_row: Application, status: str) -> None:
    history = list(app_row.status_history or [])
    history.append({"status": status, "at": _now().isoformat()})
    app_row.status_history = history


@router.get("", response_model=list[ApplicationWithJob])
def list_applications(
    status: str | None = None, db: Session = Depends(get_db)
) -> list[ApplicationWithJob]:
    query = select(Application).options(
        selectinload(Application.job).selectinload(Job.company),
        selectinload(Application.job).selectinload(Job.sources),
        selectinload(Application.job).selectinload(Job.application),
    )
    if status:
        query = query.where(Application.status == status)
    rows = db.scalars(query.order_by(Application.updated_at.desc())).unique().all()
    return [_to_out(r) for r in rows]


@router.post("", response_model=ApplicationWithJob, status_code=201)
def create_application(
    payload: ApplicationCreate, db: Session = Depends(get_db)
) -> ApplicationWithJob:
    if payload.status not in VALID_STATUSES:
        raise HTTPException(422, f"invalid status: {payload.status}")
    job = db.scalar(
        select(Job)
        .options(selectinload(Job.company), selectinload(Job.sources))
        .where(Job.id == payload.job_id)
    )
    if job is None:
        raise HTTPException(404, "job not found")
    existing = db.scalar(
        select(Application).where(Application.job_id == payload.job_id)
    )
    if existing is not None:
        raise HTTPException(409, "application already exists for this job")

    app_row = Application(job_id=payload.job_id, status=payload.status)
    if payload.status == ApplicationStatus.applied.value:
        app_row.applied_at = _now()
    _append_history(app_row, payload.status)
    db.add(app_row)
    db.commit()
    db.refresh(app_row)
    return _to_out(app_row)


@router.patch("/{application_id}", response_model=ApplicationWithJob)
def update_application(
    application_id: int, payload: ApplicationUpdate, db: Session = Depends(get_db)
) -> ApplicationWithJob:
    app_row = db.scalar(
        select(Application)
        .options(
            selectinload(Application.job).selectinload(Job.company),
            selectinload(Application.job).selectinload(Job.sources),
        )
        .where(Application.id == application_id)
    )
    if app_row is None:
        raise HTTPException(404, "application not found")

    data = payload.model_dump(exclude_unset=True)
    new_status = data.pop("status", None)
    if new_status is not None and new_status != app_row.status:
        if new_status not in VALID_STATUSES:
            raise HTTPException(422, f"invalid status: {new_status}")
        app_row.status = new_status
        _append_history(app_row, new_status)
        if new_status == ApplicationStatus.applied.value and app_row.applied_at is None:
            app_row.applied_at = _now()
    for field, value in data.items():
        setattr(app_row, field, value)
    db.commit()
    db.refresh(app_row)
    return _to_out(app_row)


@router.delete("/{application_id}", status_code=204)
def delete_application(application_id: int, db: Session = Depends(get_db)) -> None:
    app_row = db.get(Application, application_id)
    if app_row is None:
        raise HTTPException(404, "application not found")
    db.delete(app_row)
    db.commit()
