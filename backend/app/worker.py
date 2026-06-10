"""Scrape worker.

Usage:
    python -m app.worker                     # scheduler mode (runs forever)
    python -m app.worker --once              # run all enabled sources once
    python -m app.worker --once --source greenhouse
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import text

from app.config import settings
from app.db import SessionLocal
from app.models import Company, ScrapeRun, SourceSetting
from app.scrapers import registry
from app.services.dedupe import get_or_create_company, upsert_job
from app.services.discover import discover_ats_boards
from app.services.filtering import keyword_list, matches_keywords
from app.services.freshness import mark_stale_jobs_inactive

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger(__name__)

COMMIT_EVERY = 50


def run_source(source_name: str) -> dict:
    with SessionLocal() as check_db:
        toggle = check_db.get(SourceSetting, source_name)
        if toggle is not None and not toggle.enabled:
            logger.info("scrape skipped (disabled): %s", source_name)
            return {"source": source_name, "status": "skipped"}

    # Advisory lock so a concurrent run of the same source (second trigger
    # click, overlapping schedule, second worker) skips. Session-level locks
    # live on the connection, so hold a dedicated one for the whole run —
    # an ORM session would return its connection to the pool on commit and
    # leak the lock.
    from app.db import engine

    lock_conn = engine.connect()
    locked = lock_conn.execute(
        text("select pg_try_advisory_lock(hashtext('scrape'), hashtext(:src))"),
        {"src": source_name},
    ).scalar()
    if not locked:
        lock_conn.close()
        logger.info("scrape skipped (already running): %s", source_name)
        return {"source": source_name, "status": "skipped"}

    logger.info("scrape start: %s", source_name)
    scraper = registry.build_scraper(source_name)

    run_db = SessionLocal()
    run = ScrapeRun(source=source_name)
    run_db.add(run)
    run_db.commit()

    found = new = updated = skipped = 0
    keywords = keyword_list()
    db = SessionLocal()
    company_cache: dict[str, Company] = {}
    try:
        for raw in scraper.fetch(db):
            if not matches_keywords(raw, keywords):
                skipped += 1
                continue
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
        run.jobs_skipped = skipped
        run_db.commit()

    if run.status == "ok":
        deactivated = mark_stale_jobs_inactive(db, source_name)
        db.commit()
    else:
        deactivated = 0
    db.close()
    run_db.close()
    lock_conn.execute(
        text("select pg_advisory_unlock(hashtext('scrape'), hashtext(:src))"),
        {"src": source_name},
    )
    lock_conn.close()

    stats = {
        "source": source_name,
        "status": run.status,
        "found": found,
        "new": new,
        "updated": updated,
        "skipped": skipped,
        "deactivated": deactivated,
    }
    logger.info("scrape done: %s", stats)
    return stats


def run_all() -> list[dict]:
    return [run_source(name) for name in registry.enabled_sources()]


def run_discovery() -> dict:
    """Keyword-driven company discovery: web search first, optional LLM
    suggestions, then ATS probes for companies surfaced by scrapers."""
    from app.services.llm_discover import discover_companies_via_llm
    from app.services.web_discover import discover_companies_via_search

    results: dict = {}
    with SessionLocal() as db:
        try:
            results["web_search"] = discover_companies_via_search(db)
        except Exception:
            logger.exception("web search discovery failed")
        try:
            results["llm"] = discover_companies_via_llm(db)
        except Exception:
            logger.exception("llm discovery failed")
        results["probe"] = discover_ats_boards(db)
    logger.info("discovery summary: %s", results)
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="run once and exit")
    parser.add_argument("--source", help="limit to one source")
    parser.add_argument(
        "--discover", action="store_true", help="probe companies for ATS boards"
    )
    args = parser.parse_args()

    if args.discover:
        run_discovery()
        return
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
    scheduler.add_job(
        run_discovery,
        "interval",
        hours=24,
        jitter=600,
        id="ats_discovery",
        next_run_time=datetime.now(timezone.utc) + timedelta(minutes=15),
        max_instances=1,
        coalesce=True,
    )
    logger.info(
        "scheduler started: easy every %sh, hard every %sh, discovery daily",
        easy_hours,
        hard_hours,
    )
    scheduler.start()


if __name__ == "__main__":
    main()
