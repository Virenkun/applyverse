from __future__ import annotations

import logging
import random
import re
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company
from app.services.discover import _probe
from app.services.filtering import keyword_list

logger = logging.getLogger(__name__)

RESULTS_PER_QUERY = 20
QUERY_DELAY_SECONDS = (4.0, 7.0)

# Every ATS hosts postings on public, search-indexed pages — `site:` queries
# turn a keyword into company board slugs across the whole platform.
ATS_SITES: list[tuple[str, str, re.Pattern]] = [
    ("greenhouse", "boards.greenhouse.io", re.compile(r"boards\.greenhouse\.io/([A-Za-z0-9_-]+)")),
    ("greenhouse", "job-boards.greenhouse.io", re.compile(r"job-boards\.greenhouse\.io/([A-Za-z0-9_-]+)")),
    ("lever", "jobs.lever.co", re.compile(r"jobs\.lever\.co/([A-Za-z0-9_-]+)")),
    ("ashby", "jobs.ashbyhq.com", re.compile(r"jobs\.ashbyhq\.com/([A-Za-z0-9_.%-]+)")),
    ("workable", "apply.workable.com", re.compile(r"apply\.workable\.com/([A-Za-z0-9-]+)")),
    ("recruitee", "recruitee.com", re.compile(r"https?://([a-z0-9-]+)\.recruitee\.com")),
    ("smartrecruiters", "jobs.smartrecruiters.com", re.compile(r"jobs\.smartrecruiters\.com/([A-Za-z0-9]+)")),
]

SLUG_BLOCKLIST = {
    "jobs", "embed", "j", "api", "careers", "www", "boards", "share",
    "oauth", "login", "404", "privacy", "eu",
}


def _search(query: str, max_results: int) -> list[str]:
    from ddgs import DDGS

    try:
        results = DDGS().text(query, max_results=max_results)
    except Exception as exc:  # rate limits etc. — soft-fail the query
        logger.warning("web search failed for %r: %r", query, exc)
        return []
    return [r.get("href") or r.get("url") or "" for r in results or []]


def _provisional_name(slug: str) -> str:
    return re.sub(r"[-_.]+", " ", slug).strip().title() or slug


def extract_board(url: str) -> tuple[str, str] | None:
    """(ats, slug) from any ATS-hosted job/board URL, else None."""
    for ats, _site, slug_re in ATS_SITES:
        m = slug_re.search(url)
        if m and m.group(1).lower() not in SLUG_BLOCKLIST:
            return ats, m.group(1)
    return None


def register_board(
    db: Session,
    probe_client: httpx.Client,
    ats: str,
    slug: str,
    known: set[tuple[str, str]],
    known_names: set[str],
    name: str | None = None,
) -> bool:
    """Validate a board and save it as a company. Returns True when new."""
    if (ats, slug.lower()) in known:
        return False
    known.add((ats, slug.lower()))
    if not _probe(probe_client, ats, slug):
        return False
    company_name = name or _provisional_name(slug)
    if company_name.lower() in known_names:
        company = db.scalar(select(Company).where(Company.name.ilike(company_name)))
        if company is None or company.ats_type is not None:
            return False
        company.ats_type = ats
        company.ats_board_id = slug
        company.ats_probed_at = datetime.now(timezone.utc)
        db.commit()
        return True
    db.add(
        Company(
            name=company_name,
            ats_type=ats,
            ats_board_id=slug,
            ats_probed_at=datetime.now(timezone.utc),
        )
    )
    known_names.add(company_name.lower())
    db.commit()
    return True


def known_sets(db: Session) -> tuple[set[tuple[str, str]], set[str]]:
    known = {
        (c.ats_type, (c.ats_board_id or "").lower())
        for c in db.scalars(select(Company).where(Company.ats_type.is_not(None)))
    }
    known_names = {n.lower() for n in db.scalars(select(Company.name)).all()}
    return known, known_names


def discover_companies_via_search(
    db: Session, keywords: list[str] | None = None
) -> dict:
    """Search the public web for ATS job pages matching the role keywords and
    register every new company board found (after probe validation)."""
    kws = keywords if keywords is not None else keyword_list()
    if not kws:
        return {"queries": 0, "companies_new": 0}

    known, known_names = known_sets(db)

    queries = 0
    new_companies = 0
    with httpx.Client(timeout=15, follow_redirects=True) as probe_client:
        for keyword in kws:
            for ats, site, slug_re in ATS_SITES:
                queries += 1
                urls = _search(f'site:{site} "{keyword}"', RESULTS_PER_QUERY)
                time.sleep(random.uniform(*QUERY_DELAY_SECONDS))
                slugs: set[str] = set()
                for url in urls:
                    m = slug_re.search(url)
                    if not m:
                        continue
                    slug = m.group(1)
                    if slug.lower() in SLUG_BLOCKLIST:
                        continue
                    slugs.add(slug)
                for slug in slugs:
                    if register_board(
                        db, probe_client, ats, slug, known, known_names
                    ):
                        new_companies += 1
                        logger.info(
                            "web discovery: %s board %r (%s)", ats, slug, keyword
                        )

    stats = {"queries": queries, "companies_new": new_companies}
    logger.info("web discovery done: %s", stats)
    return stats
