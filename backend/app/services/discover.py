from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Company

logger = logging.getLogger(__name__)

COMPANIES_PER_RUN = 25
REPROBE_AFTER = timedelta(days=7)
PROBE_DELAY_SECONDS = 0.5

# Suffixes that rarely appear in ATS board slugs
NAME_NOISE = re.compile(
    r"\b(inc|llc|ltd|limited|pvt|private|corp|corporation|technologies|"
    r"technology|labs|software|solutions|group|co)\b",
    re.IGNORECASE,
)


def _slug_candidates(name: str) -> list[str]:
    cleaned = NAME_NOISE.sub(" ", name)
    base = re.sub(r"[^a-z0-9 ]+", "", cleaned.lower()).strip()
    if not base:
        return []
    joined = base.replace(" ", "")
    hyphenated = re.sub(r"\s+", "-", base)
    out = [joined]
    if hyphenated != joined:
        out.append(hyphenated)
    return out


def _probe(client: httpx.Client, ats: str, slug: str) -> bool:
    """True when `slug` is a live board on `ats`."""
    try:
        if ats == "greenhouse":
            r = client.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
            return r.status_code == 200 and "jobs" in r.json()
        if ats == "lever":
            r = client.get(f"https://api.lever.co/v0/postings/{slug}?mode=json&limit=1")
            return r.status_code == 200 and isinstance(r.json(), list)
        if ats == "ashby":
            r = client.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
            return r.status_code == 200 and "jobs" in r.json()
        if ats == "smartrecruiters":
            # Returns 200 with an empty list for ANY slug — only a non-zero
            # totalFound proves the company exists
            r = client.get(
                f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=1"
            )
            return r.status_code == 200 and r.json().get("totalFound", 0) > 0
        if ats == "recruitee":
            r = client.get(f"https://{slug}.recruitee.com/api/offers/")
            return r.status_code == 200 and "offers" in r.json()
        if ats == "workable":
            r = client.get(
                f"https://apply.workable.com/api/v1/widget/accounts/{slug}"
            )
            return r.status_code == 200 and "jobs" in r.json()
    except (httpx.HTTPError, ValueError):
        return False
    return False


ATS_ORDER = ["greenhouse", "lever", "ashby", "smartrecruiters", "recruitee", "workable"]


def discover_ats_boards(db: Session, limit: int = COMPANIES_PER_RUN) -> dict:
    """Probe companies discovered by keyword sources for a public ATS board.

    Companies arrive from RemoteOK/WWR/Naukri with no ats_type; when a probe
    hits, the company joins the regular ATS polling on the next run.
    """
    cutoff = datetime.now(timezone.utc) - REPROBE_AFTER
    candidates = db.scalars(
        select(Company)
        .where(
            Company.ats_type.is_(None),
            or_(Company.ats_probed_at.is_(None), Company.ats_probed_at < cutoff),
        )
        .order_by(Company.ats_probed_at.asc().nulls_first(), Company.id)
        .limit(limit)
    ).all()

    found = 0
    with httpx.Client(timeout=15, follow_redirects=True) as client:
        for company in candidates:
            company.ats_probed_at = datetime.now(timezone.utc)
            for slug in _slug_candidates(company.name):
                hit = None
                for ats in ATS_ORDER:
                    if _probe(client, ats, slug):
                        hit = ats
                        break
                    time.sleep(PROBE_DELAY_SECONDS)
                if hit:
                    company.ats_type = hit
                    company.ats_board_id = slug
                    found += 1
                    logger.info(
                        "discovered %s board %r for company %r",
                        hit,
                        slug,
                        company.name,
                    )
                    break
            db.commit()

    stats = {"probed": len(candidates), "boards_found": found}
    logger.info("ats discovery done: %s", stats)
    return stats
