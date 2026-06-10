from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from time import mktime

import feedparser
from sqlalchemy.orm import Session

from app.scrapers.base import BaseScraper, RawJob, strip_html

FEEDS = [
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-front-end-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
]


class WeWorkRemotelyScraper(BaseScraper):
    name = "weworkremotely"

    def fetch(self, db: Session) -> Iterator[RawJob]:
        seen: set[str] = set()
        for feed_url in FEEDS:
            resp = self._request("GET", feed_url)
            if resp.status_code != 200:
                continue
            feed = feedparser.parse(resp.text)
            for entry in feed.entries:
                link = entry.get("link") or ""
                job_id = link.rstrip("/").rsplit("/", 1)[-1] or link
                if not job_id or job_id in seen:
                    continue
                seen.add(job_id)
                # Titles look like "Company: Role"
                title = entry.get("title") or ""
                company, _, role = title.partition(":")
                if not role:
                    role, company = title, "Unknown"
                desc_html = entry.get("description")
                published = entry.get("published_parsed")
                region = entry.get("region") or ""
                yield RawJob(
                    source=self.name,
                    source_job_id=job_id,
                    title=role.strip(),
                    company_name=company.strip() or "Unknown",
                    url=link,
                    location=region or "Remote",
                    work_mode="remote",
                    description=strip_html(desc_html),
                    description_html=desc_html,
                    tags=[t.term for t in entry.get("tags", []) if getattr(t, "term", None)],
                    posted_at=(
                        datetime.fromtimestamp(mktime(published), tz=timezone.utc)
                        if published
                        else None
                    ),
                )
