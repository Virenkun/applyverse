from __future__ import annotations

from collections.abc import Iterator

from dateutil import parser as dateparser
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company
from app.scrapers.base import BaseScraper, RawJob, infer_work_mode, strip_html


class RecruiteeScraper(BaseScraper):
    name = "recruitee"

    def fetch(self, db: Session) -> Iterator[RawJob]:
        companies = db.scalars(
            select(Company).where(Company.ats_type == self.name)
        ).all()
        for company in companies:
            data = self.get_json(
                f"https://{company.ats_board_id}.recruitee.com/api/offers/"
            )
            if not data:
                continue
            for j in data.get("offers", []):
                location = j.get("location") or ", ".join(
                    p for p in (j.get("city"), j.get("country")) if p
                )
                desc_html = "\n".join(
                    p for p in (j.get("description"), j.get("requirements")) if p
                )
                created = j.get("created_at")
                tags = [t for t in (j.get("department"),) if t] + list(
                    j.get("tags") or []
                )
                yield RawJob(
                    source=self.name,
                    source_job_id=str(j["id"]),
                    title=j.get("title") or "",
                    company_name=company.name,
                    url=j.get("careers_url"),
                    location=location or None,
                    work_mode="remote" if j.get("remote") else infer_work_mode(location),
                    description=strip_html(desc_html),
                    description_html=desc_html or None,
                    tags=tags,
                    posted_at=dateparser.parse(created) if created else None,
                )
