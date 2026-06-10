from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.scrapers.base import BaseScraper, RawJob, strip_html

logger = logging.getLogger(__name__)

PAGES_PER_KEYWORD = 3
CHROME_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


class NaukriScraper(BaseScraper):
    """Loads Naukri search pages in headless Chrome and intercepts the
    jobapi/v3/search XHR. Direct HTTP calls get a recaptcha wall, and the
    bundled chromium headless-shell trips Akamai — a real Chrome channel
    (installed on the host) passes. Enable with ENABLE_NAUKRI=true.
    """

    name = "naukri"

    def fetch(self, db: Session) -> Iterator[RawJob]:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = None
            for channel in ("chrome", "msedge", None):
                try:
                    browser = p.chromium.launch(
                        channel=channel,
                        headless=True,
                        args=["--disable-blink-features=AutomationControlled"],
                    )
                    break
                except Exception:
                    continue
            if browser is None:
                raise RuntimeError("no chromium browser available for playwright")

            ctx = browser.new_context(
                user_agent=CHROME_UA,
                viewport={"width": 1440, "height": 900},
                locale="en-IN",
            )
            page = ctx.new_page()
            captured: list[dict] = []
            page.on(
                "response",
                lambda r: captured.append(r.json())
                if "jobapi/v3/search" in r.url and r.status == 200
                else None,
            )

            location = _slug(settings.search_location)
            for keyword in settings.keyword_list:
                for page_no in range(1, PAGES_PER_KEYWORD + 1):
                    url = f"https://www.naukri.com/{_slug(keyword)}-jobs-in-{location}"
                    if page_no > 1:
                        url += f"-{page_no}"
                    before = len(captured)
                    try:
                        page.goto(url, timeout=45000, wait_until="domcontentloaded")
                        page.wait_for_timeout(5000)
                    except Exception as exc:
                        logger.warning("naukri: page load failed %s: %r", url, exc)
                        continue
                    if len(captured) == before:
                        title = page.title()
                        if "access denied" in title.lower():
                            raise RuntimeError(
                                "naukri blocked the browser (Akamai 'Access Denied'); "
                                "run the worker where real Chrome is installed"
                            )
                        logger.warning("naukri: no jobapi response on %s", url)

            browser.close()

        seen: set[str] = set()
        for payload in captured:
            for j in payload.get("jobDetails", []):
                job_id = str(j.get("jobId") or "")
                if not job_id or job_id in seen:
                    continue
                seen.add(job_id)
                placeholders = {
                    ph.get("type"): ph.get("label")
                    for ph in j.get("placeholders", [])
                }
                jd_url = j.get("jdURL") or ""
                if jd_url and not jd_url.startswith("http"):
                    jd_url = f"https://www.naukri.com{jd_url}"
                desc_html = j.get("jobDescription")
                created = j.get("createdDate")
                tags = [
                    t.strip()
                    for t in (j.get("tagsAndSkills") or "").split(",")
                    if t.strip()
                ]
                location_label = placeholders.get("location")
                experience = placeholders.get("experience")
                if experience:
                    tags.append(experience)
                yield RawJob(
                    source=self.name,
                    source_job_id=job_id,
                    title=j.get("title") or "",
                    company_name=j.get("companyName") or "Unknown",
                    url=jd_url or None,
                    location=location_label,
                    work_mode=(
                        "remote"
                        if "remote" in (location_label or "").lower()
                        else "onsite"
                    ),
                    description=strip_html(desc_html),
                    description_html=desc_html,
                    tags=tags,
                    posted_at=(
                        datetime.fromtimestamp(created / 1000, tz=timezone.utc)
                        if isinstance(created, (int, float))
                        else None
                    ),
                )
