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
```

The api container runs migrations and seeds `companies.yaml` on start; the worker
scrapes every enabled source immediately, then on its schedule.

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
| Naukri | Headless Chrome + jobapi interception | off (`ENABLE_NAUKRI=true`) |
| Wellfound | Headless Chrome + __NEXT_DATA__ parse | off (`ENABLE_WELLFOUND=true`) |

Jobs unseen for 2 consecutive successful runs of their source are marked inactive.

### Naukri / Wellfound caveats

- **Naukri** trips Akamai with the bundled chromium headless-shell but works with a real
  Chrome install (the scraper tries the `chrome` channel first). Run the worker on the
  host for Naukri — inside Docker on Apple Silicon there is no Chrome build, so it will
  likely report "Access Denied". It searches `SEARCH_KEYWORDS` in `SEARCH_LOCATION`.
- **Wellfound** sits behind DataDome, which currently blocks headless browsers and
  datacenter IPs. The scraper is best-effort: when the challenge page is served the run
  is recorded as an error in Settings → Recent scrape runs and other sources are
  unaffected.
