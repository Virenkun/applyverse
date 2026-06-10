# JobScrap — Personal Job Scraper & Application Tracker

Scrapes jobs from ATS career pages (Greenhouse, Lever, Ashby, SmartRecruiters, Recruitee, Workable), RemoteOK, WeWorkRemotely, and optionally Naukri/Wellfound into Postgres, deduplicates them, and serves a dashboard with a searchable jobs feed and a Kanban application tracker.

## Stack

- **Backend**: FastAPI + SQLAlchemy 2 + Alembic + APScheduler worker (Python)
- **Frontend**: Next.js + Tailwind + shadcn/ui
- **DB**: PostgreSQL (full-text search), Redis (reserved for locks/cache)

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seed          # load companies.yaml
docker compose exec worker python -m app.worker --once   # first scrape
```

Dashboard: http://localhost:3000 · API docs: http://localhost:8000/docs

## Local development

```bash
# infra only
docker compose up -d db redis

# backend
cd backend
uv venv && uv pip install -e .
cp ../.env.example .env
alembic upgrade head
python -m app.seed
python -m app.worker --once              # scrape all enabled sources once
uvicorn app.main:app --reload            # API on :8000

# frontend
cd frontend
npm install
npm run dev                              # dashboard on :3000
```

## Adding companies

Edit `backend/companies.yaml` (or use the Settings page). Each entry:

```yaml
- name: Stripe
  ats: greenhouse        # greenhouse | lever | ashby | smartrecruiters | recruitee | workable
  board_id: stripe       # the company slug in that ATS's public API
```

Re-run `python -m app.seed` after manual edits.

## Sources

| Source | Method | Default |
|---|---|---|
| Greenhouse / Lever / Ashby / SmartRecruiters / Recruitee / Workable | Public JSON APIs | on |
| RemoteOK | Public JSON API | on |
| WeWorkRemotely | RSS | on |
| Naukri | Internal JSON API / Playwright | off (`ENABLE_NAUKRI=true`) |
| Wellfound | GraphQL / Playwright | off (`ENABLE_WELLFOUND=true`) |

Jobs unseen for 2 consecutive successful runs of their source are marked inactive.
