from __future__ import annotations

from collections.abc import Iterator

from dateutil import parser as dateparser
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, JobSource
from app.scrapers.base import BaseScraper, RawJob, infer_work_mode, strip_html
from app.services.filtering import keyword_list

PAGE_SIZE = 100
MAX_POSTINGS_PER_COMPANY = 200
MAX_DETAIL_FETCHES_PER_COMPANY = 100


class SmartRecruitersScraper(BaseScraper):
    name = "smartrecruiters"

    def __init__(self) -> None:
        super().__init__()
        # Documented public API tolerates ~10 req/s; details need 1 call/job
        self.throttle_range = (0.3, 0.8)

    def _fetch_description(self, board_id: str, posting_id: str) -> tuple[str | None, str | None]:
        detail = self.get_json(
            f"https://api.smartrecruiters.com/v1/companies/{board_id}/postings/{posting_id}"
        )
        if not detail:
            return None, None
        sections = (detail.get("jobAd") or {}).get("sections") or {}
        parts_html = [
            s.get("text")
            for s in sections.values()
            if isinstance(s, dict) and s.get("text")
        ]
        html_desc = "\n".join(parts_html) or None
        return strip_html(html_desc), html_desc

    def fetch(self, db: Session) -> Iterator[RawJob]:
        companies = db.scalars(
            select(Company).where(Company.ats_type == self.name)
        ).all()
        kws = keyword_list()
        for company in companies:
            detail_budget = MAX_DETAIL_FETCHES_PER_COMPANY
            for offset in range(0, MAX_POSTINGS_PER_COMPANY, PAGE_SIZE):
                data = self.get_json(
                    f"https://api.smartrecruiters.com/v1/companies/{company.ats_board_id}/postings",
                    params={"limit": PAGE_SIZE, "offset": offset},
                )
                if not data or not data.get("content"):
                    break
                for j in data["content"]:
                    loc = j.get("location") or {}
                    location = loc.get("fullLocation") or ", ".join(
                        p for p in (loc.get("city"), loc.get("country")) if p
                    )
                    posting_id = str(j["id"])
                    title_lower = (j.get("name") or "").lower()
                    # Descriptions cost one request each — only fetch for
                    # unseen jobs that can pass the keyword filter anyway
                    relevant = not kws or any(kw in title_lower for kw in kws)
                    description = description_html = None
                    is_known = (
                        db.scalar(
                            select(JobSource.id).where(
                                JobSource.source == self.name,
                                JobSource.source_job_id == posting_id,
                            )
                        )
                        is not None
                    )
                    if not is_known and relevant and detail_budget > 0:
                        detail_budget -= 1
                        description, description_html = self._fetch_description(
                            company.ats_board_id, posting_id
                        )
                    released = j.get("releasedDate")
                    tags = [
                        lbl
                        for lbl in (
                            (j.get("function") or {}).get("label"),
                            (j.get("experienceLevel") or {}).get("label"),
                            (j.get("typeOfEmployment") or {}).get("label"),
                        )
                        if lbl
                    ]
                    work_mode = "remote" if loc.get("remote") else (
                        "hybrid" if loc.get("hybrid") else infer_work_mode(location)
                    )
                    yield RawJob(
                        source=self.name,
                        source_job_id=posting_id,
                        title=j.get("name") or "",
                        company_name=company.name,
                        url=f"https://jobs.smartrecruiters.com/{company.ats_board_id}/{posting_id}",
                        location=location or None,
                        work_mode=work_mode,
                        description=description,
                        description_html=description_html,
                        tags=tags,
                        posted_at=dateparser.parse(released) if released else None,
                    )
                if offset + PAGE_SIZE >= int(data.get("totalFound", 0)):
                    break
