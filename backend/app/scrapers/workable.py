from __future__ import annotations

from collections.abc import Iterator

from dateutil import parser as dateparser
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company
from app.scrapers.base import BaseScraper, RawJob, infer_work_mode, strip_html


class WorkableScraper(BaseScraper):
    name = "workable"

    def fetch(self, db: Session) -> Iterator[RawJob]:
        companies = db.scalars(
            select(Company).where(Company.ats_type == self.name)
        ).all()
        for company in companies:
            # v1 widget endpoint returns every job with description in one call
            data = self.get_json(
                f"https://apply.workable.com/api/v1/widget/accounts/{company.ats_board_id}",
                params={"details": "true"},
            )
            if not data:
                continue
            for j in data.get("jobs", []):
                location = ", ".join(
                    p for p in (j.get("city"), j.get("state"), j.get("country")) if p
                )
                desc_html = j.get("description")
                created = j.get("created_at")
                yield RawJob(
                    source=self.name,
                    source_job_id=str(j.get("shortcode") or j.get("code") or j["url"]),
                    title=j.get("title") or "",
                    company_name=company.name,
                    url=j.get("url") or j.get("application_url"),
                    location=location or None,
                    work_mode="remote"
                    if (j.get("telecommuting") or j.get("remote"))
                    else infer_work_mode(location),
                    description=strip_html(desc_html),
                    description_html=desc_html,
                    tags=[t for t in (j.get("department"),) if t],
                    posted_at=dateparser.parse(created) if created else None,
                )
