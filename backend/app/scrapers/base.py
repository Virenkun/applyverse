from __future__ import annotations

import html
import logging
import random
import re
import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser

import httpx
from sqlalchemy.orm import Session
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Version/17.5 Safari/605.1.15 AppleWebKit/605.1.15 (KHTML, like Gecko)",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
]

# Minimum seconds between requests to the same domain
DOMAIN_THROTTLE_SECONDS = (2.0, 5.0)

_last_request_at: dict[str, float] = {}


@dataclass
class RawJob:
    source: str
    source_job_id: str
    title: str
    company_name: str
    url: str | None = None
    location: str | None = None
    work_mode: str = "unknown"
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str | None = None
    description: str | None = None
    description_html: str | None = None
    tags: list[str] = field(default_factory=list)
    posted_at: datetime | None = None


class _TagStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def strip_html(value: str | None) -> str | None:
    if not value:
        return value
    stripper = _TagStripper()
    stripper.feed(html.unescape(value))
    text = " ".join(stripper.parts)
    return re.sub(r"\s+", " ", text).strip()


def infer_work_mode(
    location: str | None,
    is_remote: bool | None = None,
    workplace_type: str | None = None,
) -> str:
    wt = (workplace_type or "").lower()
    loc = (location or "").lower()
    if is_remote or wt == "remote" or "remote" in loc:
        return "remote"
    if wt == "hybrid" or "hybrid" in loc:
        return "hybrid"
    if wt in ("onsite", "on-site") or location:
        return "onsite"
    return "unknown"


def _throttle(url: str, throttle_range: tuple[float, float]) -> None:
    domain = httpx.URL(url).host or ""
    elapsed = time.monotonic() - _last_request_at.get(domain, 0.0)
    wait = random.uniform(*throttle_range) - elapsed
    if wait > 0:
        time.sleep(wait)
    _last_request_at[domain] = time.monotonic()


class BaseScraper(ABC):
    """A scraper yields RawJobs for one source. HTTP helpers handle
    throttling, UA rotation and retry with exponential backoff."""

    name: str = "base"

    def __init__(self) -> None:
        self.client = httpx.Client(timeout=30, follow_redirects=True)
        self.throttle_range: tuple[float, float] = DOMAIN_THROTTLE_SECONDS

    @abstractmethod
    def fetch(self, db: Session) -> Iterator[RawJob]: ...

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
        reraise=True,
    )
    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        _throttle(url, self.throttle_range)
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        headers.update(kwargs.pop("headers", {}))
        resp = self.client.request(method, url, headers=headers, **kwargs)
        # 404 = board gone, not worth retrying; raise for retryable 5xx/429
        if resp.status_code in (429,) or resp.status_code >= 500:
            resp.raise_for_status()
        return resp

    def get_json(self, url: str, **kwargs):
        resp = self._request("GET", url, **kwargs)
        if resp.status_code != 200:
            logger.warning("%s: GET %s -> %s", self.name, url, resp.status_code)
            return None
        return resp.json()

    def post_json(self, url: str, **kwargs):
        resp = self._request("POST", url, **kwargs)
        if resp.status_code != 200:
            logger.warning("%s: POST %s -> %s", self.name, url, resp.status_code)
            return None
        return resp.json()

    def close(self) -> None:
        self.client.close()
