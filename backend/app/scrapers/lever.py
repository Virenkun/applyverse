from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company
from app.scrapers.base import BaseScraper, RawJob, infer_work_mode


class LeverScraper(BaseScraper):
    name = "lever"

    def fetch(self, db: Session) -> Iterator[RawJob]:
        companies = db.scalars(
            select(Company).where(Company.ats_type == self.name)
        ).all()
        for company in companies:
            data = self.get_json(
                f"https://api.lever.co/v0/postings/{company.ats_board_id}",
                params={"mode": "json"},
            )
            if not data:
                continue
            for j in data:
                categories = j.get("categories") or {}
                location = categories.get("location")
                salary = j.get("salaryRange") or {}
                tags = [
                    t
                    for t in (categories.get("team"), categories.get("commitment"))
                    if t
                ]
                created_ms = j.get("createdAt")
                yield RawJob(
                    source=self.name,
                    source_job_id=str(j["id"]),
                    title=j.get("text") or "",
                    company_name=company.name,
                    url=j.get("hostedUrl"),
                    location=location,
                    work_mode=infer_work_mode(
                        location, workplace_type=j.get("workplaceType")
                    ),
                    salary_min=salary.get("min"),
                    salary_max=salary.get("max"),
                    currency=salary.get("currency"),
                    description=j.get("descriptionPlain"),
                    description_html=j.get("description"),
                    tags=tags,
                    posted_at=(
                        datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc)
                        if created_ms
                        else None
                    ),
                )
