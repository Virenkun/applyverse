from __future__ import annotations

from collections.abc import Iterator

from dateutil import parser as dateparser
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company
from app.scrapers.base import BaseScraper, RawJob, infer_work_mode


class AshbyScraper(BaseScraper):
    name = "ashby"

    def fetch(self, db: Session) -> Iterator[RawJob]:
        companies = db.scalars(
            select(Company).where(Company.ats_type == self.name)
        ).all()
        for company in companies:
            data = self.get_json(
                f"https://api.ashbyhq.com/posting-api/job-board/{company.ats_board_id}",
                params={"includeCompensation": "true"},
            )
            if not data:
                continue
            for j in data.get("jobs", []):
                if not j.get("isListed", True):
                    continue
                location = j.get("location")
                tags = [t for t in (j.get("department"), j.get("team")) if t]
                published = j.get("publishedAt")
                yield RawJob(
                    source=self.name,
                    source_job_id=str(j["id"]),
                    title=j["title"],
                    company_name=company.name,
                    url=j.get("jobUrl") or j.get("applyUrl"),
                    location=location,
                    work_mode=infer_work_mode(
                        location,
                        is_remote=j.get("isRemote"),
                        workplace_type=j.get("workplaceType"),
                    ),
                    description=j.get("descriptionPlain"),
                    description_html=j.get("descriptionHtml"),
                    tags=tags,
                    posted_at=dateparser.parse(published) if published else None,
                )
