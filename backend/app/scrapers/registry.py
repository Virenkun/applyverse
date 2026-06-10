from __future__ import annotations

from app.config import settings
from app.scrapers.ashby import AshbyScraper
from app.scrapers.base import BaseScraper
from app.scrapers.greenhouse import GreenhouseScraper
from app.scrapers.lever import LeverScraper
from app.scrapers.recruitee import RecruiteeScraper
from app.scrapers.remoteok import RemoteOKScraper
from app.scrapers.smartrecruiters import SmartRecruitersScraper
from app.scrapers.weworkremotely import WeWorkRemotelyScraper
from app.scrapers.workable import WorkableScraper

SCRAPERS: dict[str, type[BaseScraper]] = {
    "greenhouse": GreenhouseScraper,
    "lever": LeverScraper,
    "ashby": AshbyScraper,
    "smartrecruiters": SmartRecruitersScraper,
    "recruitee": RecruiteeScraper,
    "workable": WorkableScraper,
    "remoteok": RemoteOKScraper,
    "weworkremotely": WeWorkRemotelyScraper,
}

# Filled in lazily — playwright import is heavy and these stay off by default
EASY_SOURCES = list(SCRAPERS)
HARD_SOURCES: list[str] = []


def register_hard_sources() -> None:
    from app.scrapers.naukri import NaukriScraper
    from app.scrapers.wellfound import WellfoundScraper

    SCRAPERS["naukri"] = NaukriScraper
    SCRAPERS["wellfound"] = WellfoundScraper
    HARD_SOURCES[:] = ["naukri", "wellfound"]


def enabled_sources() -> list[str]:
    sources = list(EASY_SOURCES)
    if settings.enable_naukri or settings.enable_wellfound:
        register_hard_sources()
        if settings.enable_naukri:
            sources.append("naukri")
        if settings.enable_wellfound:
            sources.append("wellfound")
    return sources


def build_scraper(name: str) -> BaseScraper:
    if name in ("naukri", "wellfound") and name not in SCRAPERS:
        register_hard_sources()
    return SCRAPERS[name]()
