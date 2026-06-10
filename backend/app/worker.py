"""Scrape worker.

Usage:
    python -m app.worker                     # scheduler mode (runs forever)
    python -m app.worker --once              # run all enabled sources once
    python -m app.worker --once --source greenhouse
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.blocking import BlockingScheduler

from app.config import settings
from app.db import SessionLocal
from app.models import Company, ScrapeRun
from app.scrapers import registry
from app.services.dedupe import get_or_create_company, upsert_job
from app.services.freshness import mark_stale_jobs_inactive

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger(__name__)

COMMIT_EVERY = 50


def run_source(source_name: str) -> dict:
    logger.info("scrape start: %s", source_name)
    scraper = registry.build_scraper(source_name)

    run_db = SessionLocal()
    run = ScrapeRun(source=source_name)
    run_db.add(run)
    run_db.commit()

    found = new = updated = 0
    db = SessionLocal()
    company_cache: dict[str, Company] = {}
    try:
        for raw in scraper.fetch(db):
            company = company_cache.get(raw.company_name)
            if company is None:
                company = get_or_create_company(db, raw.company_name)
                company_cache[raw.company_name] = company
            result = upsert_job(db, raw, company=company)
            found += 1
            if result == "new":
                new += 1
            else:
                updated += 1
            if found % COMMIT_EVERY == 0:
                db.commit()
        db.commit()
        run.status = "ok"
    except Exception as exc:  # noqa: BLE001 — one bad source must not kill the rest
        db.rollback()
        run.status = "error"
        run.error = repr(exc)[:2000]
        logger.exception("scrape failed: %s", source_name)
    finally:
        scraper.close()
        run.finished_at = datetime.now(timezone.utc)
        run.jobs_found = found
        run.jobs_new = new
        run.jobs_updated = updated
        run_db.commit()

    if run.status == "ok":
        deactivated = mark_stale_jobs_inactive(db, source_name)
        db.commit()
    else:
        deactivated = 0
    db.close()
    run_db.close()

    stats = {
        "source": source_name,
        "status": run.status,
        "found": found,
        "new": new,
        "updated": updated,
        "deactivated": deactivated,
    }
    logger.info("scrape done: %s", stats)
    return stats


def run_all() -> list[dict]:
    return [run_source(name) for name in registry.enabled_sources()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="run once and exit")
    parser.add_argument("--source", help="limit to one source")
    args = parser.parse_args()

    if args.once:
        if args.source:
            run_source(args.source)
        else:
            run_all()
        return

    scheduler = BlockingScheduler(timezone="UTC")
    easy_hours = settings.scrape_interval_easy_hours
    hard_hours = settings.scrape_interval_hard_hours
    for name in registry.enabled_sources():
        hours = hard_hours if name in registry.HARD_SOURCES else easy_hours
        scheduler.add_job(
            run_source,
            "interval",
            args=[name],
            hours=hours,
            jitter=600,
            id=name,
            next_run_time=datetime.now(timezone.utc),
            max_instances=1,
            coalesce=True,
        )
    logger.info(
        "scheduler started: easy every %sh, hard every %sh", easy_hours, hard_hours
    )
    scheduler.start()


if __name__ == "__main__":
    main()
