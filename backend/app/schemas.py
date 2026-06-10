from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CompanyOut(ORMModel):
    id: int
    name: str
    website: str | None = None
    logo_url: str | None = None
    ats_type: str | None = None
    glassdoor_rating: float | None = None
    notes: str | None = None


class CompanyWithCounts(CompanyOut):
    open_jobs: int = 0
    applications: int = 0


class JobSourceOut(ORMModel):
    source: str
    url: str | None = None


class ApplicationOut(ORMModel):
    id: int
    job_id: int
    status: str
    applied_at: datetime | None = None
    resume_version: str | None = None
    cover_letter_used: bool = False
    notes: str | None = None
    next_followup_at: datetime | None = None
    status_history: list = []
    created_at: datetime
    updated_at: datetime


class JobListItem(ORMModel):
    id: int
    title: str
    company: CompanyOut
    location: str | None = None
    work_mode: str
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str | None = None
    tags: list[str] | None = None
    canonical_url: str | None = None
    posted_at: datetime | None = None
    scraped_at: datetime
    is_active: bool
    is_hidden: bool
    sources: list[JobSourceOut] = []
    application: ApplicationOut | None = None
    description_snippet: str | None = None


class JobDetail(JobListItem):
    description: str | None = None
    description_html: str | None = None


class JobListResponse(BaseModel):
    items: list[JobListItem]
    total: int
    page: int
    page_size: int


class ApplicationWithJob(ApplicationOut):
    job: JobListItem


class ApplicationCreate(BaseModel):
    job_id: int
    status: str = "saved"


class ApplicationUpdate(BaseModel):
    status: str | None = None
    applied_at: datetime | None = None
    resume_version: str | None = None
    cover_letter_used: bool | None = None
    notes: str | None = None
    next_followup_at: datetime | None = None


class StatsOverview(BaseModel):
    jobs_new_today: int
    jobs_active: int
    applications_total: int
    applied_this_week: int
    interviewing: int
    offers: int
    response_rate: float | None = None
    followups_due: int


class TimelinePoint(BaseModel):
    date: str
    applications: int
    jobs_scraped: int


class ScrapeRunOut(ORMModel):
    id: int
    source: str
    started_at: datetime
    finished_at: datetime | None = None
    jobs_found: int
    jobs_new: int
    jobs_updated: int
    jobs_skipped: int = 0
    status: str
    error: str | None = None


class SourceSettingOut(BaseModel):
    source: str
    enabled: bool
    available: bool
    last_run: ScrapeRunOut | None = None


class SourceSettingUpdate(BaseModel):
    enabled: bool
