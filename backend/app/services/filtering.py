from __future__ import annotations

from app.config import settings
from app.scrapers.base import RawJob


def keyword_list() -> list[str]:
    return [k.lower() for k in settings.keyword_list]


def matches_keywords(raw: RawJob, keywords: list[str] | None = None) -> bool:
    """True when the job looks like one of the configured roles.

    Matches keyword phrases against title and tags (not description — every
    JD mentions \"software\" somewhere). Empty keyword list keeps everything.
    """
    kws = keyword_list() if keywords is None else keywords
    if not kws:
        return True
    haystack = raw.title.lower()
    for tag in raw.tags or []:
        haystack += " | " + tag.lower()
    return any(kw in haystack for kw in kws)
