from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ScrapeRun
from app.schemas import ScrapeRunOut

router = APIRouter(prefix="/scrape", tags=["scrape"])


@router.post("/trigger")
def trigger_scrape(
    background: BackgroundTasks, source: str | None = None
) -> dict:
    # Imported here so the API process only loads scraper deps when used
    from app.scrapers import registry
    from app.worker import run_all, run_source

    if source is not None:
        if source not in registry.SCRAPERS and source not in ("naukri", "wellfound"):
            raise HTTPException(404, f"unknown source: {source}")
        background.add_task(run_source, source)
        return {"started": [source]}
    background.add_task(run_all)
    return {"started": "all"}


@router.get("/runs", response_model=list[ScrapeRunOut])
def recent_runs(limit: int = 20, db: Session = Depends(get_db)) -> list[ScrapeRunOut]:
    runs = db.scalars(
        select(ScrapeRun).order_by(ScrapeRun.started_at.desc()).limit(min(limit, 100))
    ).all()
    return [ScrapeRunOut.model_validate(r) for r in runs]
