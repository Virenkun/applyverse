from __future__ import annotations

import html as html_lib
import logging
import re
from collections.abc import Iterator

from dateutil import parser as dateparser
from sqlalchemy.orm import Session

from app.config import settings
from app.scrapers.base import BaseScraper, RawJob, infer_work_mode

logger = logging.getLogger(__name__)

PAGES_PER_KEYWORD = 2  # 25 results per page
GUEST_SEARCH = (
    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
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
    Enable with ENABLE_LINKEDIN=true. No description is fetched — the card
    list has none and per-job fetches would multiply the request volume.
    """

    name = "linkedin"

    def fetch(self, db: Session) -> Iterator[RawJob]:
        seen: set[str] = set()
        blocked = 0
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
                    yield RawJob(
                        source=self.name,
                        source_job_id=job_id,
                        title=title,
                        company_name=company or "Unknown",
                        url=url,
                        location=location,
                        work_mode=infer_work_mode(f"{title} {location or ''}"),
                        posted_at=dateparser.parse(date) if date else None,
                    )
        if blocked and not seen:
            raise RuntimeError(
                "linkedin rate-limited every request (HTTP 429/999); "
                "try again later or from a different network"
            )
