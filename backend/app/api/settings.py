from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings as app_settings
from app.db import get_db
from app.models import ScrapeRun, SourceSetting
from app.schemas import ScrapeRunOut, SourceSettingOut, SourceSettingUpdate

router = APIRouter(prefix="/settings", tags=["settings"])

ALL_SOURCES = [
    "greenhouse",
    "lever",
    "ashby",
    "smartrecruiters",
    "recruitee",
    "workable",
    "remoteok",
    "weworkremotely",
    "naukri",
    "wellfound",
]


def _is_available(source: str) -> bool:
    if source == "naukri":
        return app_settings.enable_naukri
    if source == "wellfound":
        return app_settings.enable_wellfound
    return True


@router.get("/sources", response_model=list[SourceSettingOut])
def list_sources(db: Session = Depends(get_db)) -> list[SourceSettingOut]:
    toggles = {s.source: s.enabled for s in db.scalars(select(SourceSetting)).all()}
    result = []
    for source in ALL_SOURCES:
        last_run = db.scalar(
            select(ScrapeRun)
            .where(ScrapeRun.source == source)
            .order_by(ScrapeRun.started_at.desc())
            .limit(1)
        )
        result.append(
            SourceSettingOut(
                source=source,
                enabled=toggles.get(source, True),
                available=_is_available(source),
                last_run=ScrapeRunOut.model_validate(last_run) if last_run else None,
            )
        )
    return result


@router.patch("/sources/{source}", response_model=SourceSettingOut)
def update_source(
    source: str, payload: SourceSettingUpdate, db: Session = Depends(get_db)
) -> SourceSettingOut:
    if source not in ALL_SOURCES:
        raise HTTPException(404, f"unknown source: {source}")
    row = db.get(SourceSetting, source)
    if row is None:
        row = SourceSetting(source=source)
        db.add(row)
    row.enabled = payload.enabled
    db.commit()
    return SourceSettingOut(
        source=source, enabled=row.enabled, available=_is_available(source)
    )
