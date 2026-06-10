from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.config import settings
from app.scrapers.base import BaseScraper, RawJob
from app.scrapers.naukri import CHROME_UA

logger = logging.getLogger(__name__)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


class WellfoundScraper(BaseScraper):
    """Best-effort: loads wellfound.com role pages with headless Chrome and
    parses job listings out of the embedded __NEXT_DATA__ blob.

    Wellfound sits behind DataDome, which currently blocks datacenter IPs and
    most headless browsers. When the challenge page is served instead of
    content this raises, so the failure lands in scrape_runs and is visible
    in Settings. Enable with ENABLE_WELLFOUND=true.
    """

    name = "wellfound"

    def fetch(self, db: Session) -> Iterator[RawJob]:
        from playwright.sync_api import sync_playwright

        blobs: list[dict] = []
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
                user_agent=CHROME_UA, viewport={"width": 1440, "height": 900}
            )
            page = ctx.new_page()
            blocked = False
            for keyword in settings.keyword_list:
                url = f"https://wellfound.com/role/r/{_slug(keyword)}"
                try:
                    page.goto(url, timeout=45000, wait_until="domcontentloaded")
                    page.wait_for_timeout(5000)
                except Exception as exc:
                    logger.warning("wellfound: page load failed %s: %r", url, exc)
                    continue
                node = page.locator("#__NEXT_DATA__")
                if node.count() == 0:
                    blocked = True
                    logger.warning(
                        "wellfound: no __NEXT_DATA__ on %s (title=%r)",
                        url,
                        page.title(),
                    )
                    continue
                try:
                    blobs.append(json.loads(node.first.text_content() or "{}"))
                except json.JSONDecodeError:
                    logger.warning("wellfound: bad __NEXT_DATA__ JSON on %s", url)
            browser.close()

        if not blobs:
            if blocked:
                raise RuntimeError(
                    "wellfound served the DataDome challenge instead of content; "
                    "scraping currently needs a residential IP / real browser session"
                )
            raise RuntimeError("wellfound returned no parseable pages")

        seen: set[str] = set()
        for blob in blobs:
            yield from self._parse_blob(blob, seen)

    def _parse_blob(self, blob: dict, seen: set[str]) -> Iterator[RawJob]:
        # Apollo cache: JobListingSearchResult objects keyed by id, with
        # StartupResult companies referenced alongside.
        apollo = (
            blob.get("props", {}).get("pageProps", {}).get("apolloState", {}).get("data")
            or blob.get("props", {}).get("apolloState", {}).get("data")
            or {}
        )
        companies: dict[str, str] = {}
        for key, obj in apollo.items():
            if isinstance(obj, dict) and obj.get("__typename") == "StartupResult":
                companies[key] = obj.get("name") or "Unknown"
        for key, obj in apollo.items():
            if not isinstance(obj, dict):
                continue
            if obj.get("__typename") != "JobListingSearchResult":
                continue
            job_id = str(obj.get("id") or "")
            if not job_id or job_id in seen:
                continue
            seen.add(job_id)
            company_ref = (obj.get("startup") or {}).get("__ref", "")
            comp = obj.get("compensation") or ""
            slug = obj.get("slug") or job_id
            yield RawJob(
                source=self.name,
                source_job_id=job_id,
                title=obj.get("title") or "",
                company_name=companies.get(company_ref, "Unknown"),
                url=f"https://wellfound.com/jobs/{job_id}-{slug}",
                location=", ".join(obj.get("locationNames") or []) or None,
                work_mode="remote" if obj.get("remote") else "unknown",
                description=obj.get("description"),
                tags=[comp] if comp else [],
                posted_at=None,
            )
