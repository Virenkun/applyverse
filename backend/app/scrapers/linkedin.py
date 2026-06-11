from __future__ import annotations

import html as html_lib
import logging
import re
from collections.abc import Iterator

from dateutil import parser as dateparser
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Job, JobSource
from app.scrapers.base import BaseScraper, RawJob, infer_work_mode, strip_html

logger = logging.getLogger(__name__)

PAGES_PER_KEYWORD = 2  # 25 results per page
# Descriptions cost one request each — cap per run to keep volume (and ban
# risk) bounded; only unseen, keyword-matching jobs spend the budget
DETAIL_BUDGET = 60
GUEST_SEARCH = (
    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
)
GUEST_DETAIL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

DESC_RE = re.compile(
    r'show-more-less-html__markup[^>]*>(?P<html>.*?)</div>', re.DOTALL
)
CRITERIA_RE = re.compile(
    r'description__job-criteria-subheader">\s*(?P<key>.*?)\s*</h3>.*?'
    r'description__job-criteria-text[^>]*>\s*(?P<val>.*?)\s*</span>',
    re.DOTALL,
)

CARD_RE = re.compile(
    r'base-card__full-link[^"]*"\s+href="(?P<url>[^"]+)".*?'
    r'base-search-card__title[^"]*">\s*(?:<span[^>]*>\s*)?(?P<title>.*?)\s*(?:</span>\s*)?</h3>.*?'
    r'(?:hidden-nested-link[^"]*"[^>]*>\s*(?P<company>.*?)\s*</a>.*?)?'
    r'job-search-card__location[^"]*">\s*(?P<location>.*?)\s*</span>'
    r'(?:.*?datetime="(?P<date>[\d-]+)")?',
    re.DOTALL,
)
JOB_ID_RE = re.compile(r"-(\d{6,})\??")


class LinkedInScraper(BaseScraper):
    """LinkedIn guest job search — no login, parses the public HTML cards the
    jobs page loads for anonymous visitors.

    WARNING: scraping LinkedIn violates their ToS; they aggressively
    rate-limit (HTTP 429/999) and may block your IP. Low volume + throttle
    keeps it survivable but this stays best-effort and off by default.
    Enable with ENABLE_LINKEDIN=true. The card list carries no description, so
    up to DETAIL_BUDGET unseen, keyword-matching jobs get one extra guest
    request each to pull the full job description.
    """

    name = "linkedin"

    def _fetch_detail(self, job_id: str) -> tuple[str | None, str | None, list[str]]:
        resp = self._request(
            "GET",
            GUEST_DETAIL.format(job_id=job_id),
            headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        if resp.status_code != 200:
            return None, None, []
        m = DESC_RE.search(resp.text)
        desc_html = m.group("html").strip() if m else None
        tags = [
            html_lib.unescape(c.group("val")).strip()
            for c in CRITERIA_RE.finditer(resp.text)
            if c.group("key").strip() in ("Seniority level", "Job function")
        ]
        return strip_html(desc_html), desc_html, tags

    def fetch(self, db: Session) -> Iterator[RawJob]:
        seen: set[str] = set()
        blocked = 0
        kws = settings.keyword_list
        detail_budget = DETAIL_BUDGET
        for keyword in settings.keyword_list:
            for page in range(PAGES_PER_KEYWORD):
                resp = self._request(
                    "GET",
                    GUEST_SEARCH,
                    params={
                        "keywords": keyword,
                        "location": settings.search_location,
                        "start": page * 25,
                    },
                    headers={"Accept-Language": "en-US,en;q=0.9"},
                )
                if resp.status_code in (429, 999):
                    blocked += 1
                    logger.warning(
                        "linkedin: rate limited (%s) on %r page %s",
                        resp.status_code,
                        keyword,
                        page,
                    )
                    break
                if resp.status_code != 200 or not resp.text.strip():
                    break
                for m in CARD_RE.finditer(resp.text):
                    url = html_lib.unescape(m.group("url")).split("?")[0]
                    id_match = JOB_ID_RE.search(url + "?")
                    job_id = id_match.group(1) if id_match else url
                    if job_id in seen:
                        continue
                    seen.add(job_id)
                    company = html_lib.unescape(m.group("company") or "").strip()
                    location = html_lib.unescape(m.group("location")).strip() or None
                    date = m.group("date")
                    title = html_lib.unescape(m.group("title")).strip()

                    description = description_html = None
                    tags: list[str] = []
                    relevant = not kws or any(kw in title.lower() for kw in kws)
                    if relevant and detail_budget > 0:
                        # Spend the budget on jobs with no stored description:
                        # unseen ones, plus older rows scraped before detail
                        # fetching existed (backfill).
                        existing = db.scalar(
                            select(Job.description)
                            .join(JobSource, JobSource.job_id == Job.id)
                            .where(
                                JobSource.source == self.name,
                                JobSource.source_job_id == job_id,
                            )
                        )
                        needs_detail = existing is None
                        if needs_detail:
                            detail_budget -= 1
                            try:
                                description, description_html, tags = (
                                    self._fetch_detail(job_id)
                                )
                            except Exception as exc:  # one bad detail must not abort
                                logger.warning(
                                    "linkedin: detail fetch failed for %s: %r",
                                    job_id,
                                    exc,
                                )

                    yield RawJob(
                        source=self.name,
                        source_job_id=job_id,
                        title=title,
                        company_name=company or "Unknown",
                        url=url,
                        location=location,
                        work_mode=infer_work_mode(f"{title} {location or ''}"),
                        description=description,
                        description_html=description_html,
                        tags=tags,
                        posted_at=dateparser.parse(date) if date else None,
                    )
        if blocked and not seen:
            raise RuntimeError(
                "linkedin rate-limited every request (HTTP 429/999); "
                "try again later or from a different network"
            )
