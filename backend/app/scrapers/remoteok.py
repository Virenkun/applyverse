from __future__ import annotations

from collections.abc import Iterator

from dateutil import parser as dateparser
from sqlalchemy.orm import Session

from app.scrapers.base import BaseScraper, RawJob, strip_html


class RemoteOKScraper(BaseScraper):
    name = "remoteok"

    def fetch(self, db: Session) -> Iterator[RawJob]:
        data = self.get_json("https://remoteok.com/api")
        if not data:
            return
        for j in data:
            # First element is a legal notice, not a job
            if not isinstance(j, dict) or not j.get("id") or not j.get("position"):
                continue
            date = j.get("date")
            desc_html = j.get("description")
            yield RawJob(
                source=self.name,
                source_job_id=str(j["id"]),
                title=j["position"],
                company_name=j.get("company") or "Unknown",
                url=j.get("url"),
                location=j.get("location") or "Remote",
                work_mode="remote",
                salary_min=j.get("salary_min") or None,
                salary_max=j.get("salary_max") or None,
                currency="USD" if j.get("salary_min") else None,
                description=strip_html(desc_html),
                description_html=desc_html,
                tags=list(j.get("tags") or []),
                posted_at=dateparser.parse(date) if date else None,
            )
