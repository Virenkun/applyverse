from __future__ import annotations

import html
from collections.abc import Iterator

from dateutil import parser as dateparser
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company
from app.scrapers.base import BaseScraper, RawJob, infer_work_mode, strip_html


class GreenhouseScraper(BaseScraper):
    name = "greenhouse"

    def fetch(self, db: Session) -> Iterator[RawJob]:
        companies = db.scalars(
            select(Company).where(Company.ats_type == self.name)
        ).all()
        for company in companies:
            data = self.get_json(
                f"https://boards-api.greenhouse.io/v1/boards/{company.ats_board_id}/jobs",
                params={"content": "true"},
            )
            if not data:
                continue
            for j in data.get("jobs", []):
                content = html.unescape(j.get("content") or "")
                location = (j.get("location") or {}).get("name")
                departments = [
                    d["name"] for d in j.get("departments", []) if d.get("name")
                ]
                posted = j.get("first_published") or j.get("updated_at")
                yield RawJob(
                    source=self.name,
                    source_job_id=str(j["id"]),
                    title=j["title"],
                    company_name=company.name,
                    url=j.get("absolute_url"),
                    location=location,
                    work_mode=infer_work_mode(location),
                    description=strip_html(content),
                    description_html=content or None,
                    tags=departments,
                    posted_at=dateparser.parse(posted) if posted else None,
                )
