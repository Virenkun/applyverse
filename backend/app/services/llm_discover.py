from __future__ import annotations

import json
import logging
import re

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.services.web_discover import extract_board, known_sets, register_board

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"

PROMPT = """Find companies that are currently hiring for these roles: {keywords}.
Location focus: {location} (remote-friendly companies anywhere also count).

Use web search to find CURRENT openings. Strongly prefer job postings hosted on
these ATS platforms: boards.greenhouse.io, job-boards.greenhouse.io,
jobs.lever.co, jobs.ashbyhq.com, apply.workable.com, *.recruitee.com,
jobs.smartrecruiters.com.

Respond with ONLY a JSON array, no prose, of up to 25 entries:
[{{"name": "Company Name", "job_url": "https://boards.greenhouse.io/..."}}]
Each job_url must be a real URL you found, hosted on one of those platforms."""


def discover_companies_via_llm(db: Session) -> dict:
    """Ask Claude (with web search) for companies hiring the configured roles,
    then register any ATS boards found in the returned URLs."""
    if not settings.anthropic_api_key:
        return {"skipped": "no ANTHROPIC_API_KEY"}

    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 8}],
        messages=[
            {
                "role": "user",
                "content": PROMPT.format(
                    keywords=", ".join(settings.keyword_list),
                    location=settings.search_location,
                ),
            }
        ],
    )

    text = "".join(
        block.text for block in response.content if block.type == "text"
    )
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        logger.warning("llm discovery: no JSON array in response: %.200s", text)
        return {"companies_new": 0, "parse_error": True}
    try:
        entries = json.loads(match.group(0))
    except json.JSONDecodeError:
        logger.warning("llm discovery: bad JSON: %.200s", match.group(0))
        return {"companies_new": 0, "parse_error": True}

    known, known_names = known_sets(db)
    new_companies = 0
    with httpx.Client(timeout=15, follow_redirects=True) as probe_client:
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            board = extract_board(str(entry.get("job_url") or ""))
            if board is None:
                continue
            ats, slug = board
            if register_board(
                db, probe_client, ats, slug, known, known_names,
                name=(entry.get("name") or "").strip() or None,
            ):
                new_companies += 1
                logger.info("llm discovery: %s board %r (%s)", ats, slug, entry.get("name"))

    stats = {"companies_new": new_companies, "suggestions": len(entries)}
    logger.info("llm discovery done: %s", stats)
    return stats
