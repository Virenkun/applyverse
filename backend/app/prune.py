"""Delete stored jobs that don't match the configured keywords.

Jobs with an application (saved/applied/...) are always kept. Run after
tightening SEARCH_KEYWORDS to clean out previously scraped noise:

    python -m app.prune            # show what would be deleted
    python -m app.prune --execute  # delete
"""

from __future__ import annotations

import argparse

from sqlalchemy import delete, func, select

from app.db import SessionLocal
from app.models import Application, Job
from app.scrapers.base import RawJob
from app.services.filtering import keyword_list, matches_keywords


def find_prunable(db) -> list[int]:
    keywords = keyword_list()
    if not keywords:
        return []
    applied_ids = set(db.scalars(select(Application.job_id)).all())
    prunable = []
    for job_id, title, tags in db.execute(select(Job.id, Job.title, Job.tags)):
        if job_id in applied_ids:
            continue
        raw = RawJob(
            source="", source_job_id="", title=title or "", company_name="",
            tags=list(tags or []),
        )
        if not matches_keywords(raw, keywords):
            prunable.append(job_id)
    return prunable


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="actually delete")
    args = parser.parse_args()

    with SessionLocal() as db:
        total = db.scalar(select(func.count()).select_from(Job)) or 0
        prunable = find_prunable(db)
        print(f"jobs total: {total}, not matching keywords: {len(prunable)}")
        if not args.execute:
            print("dry run — pass --execute to delete")
            return
        if prunable:
            # job_sources rows cascade via FK ondelete
            db.execute(delete(Job).where(Job.id.in_(prunable)))
            db.commit()
        print(f"deleted {len(prunable)} jobs")


if __name__ == "__main__":
    main()
