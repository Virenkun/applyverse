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

## How jobs flow in

1. **Keyword filter** — `SEARCH_KEYWORDS` in `.env` decides what gets stored. Every
   scraped job from every source is kept only if its title or tags contain one of the
   keywords; the rest are counted as "off-keyword" in Settings → Recent scrape runs.
   After changing keywords, clean older noise with
   `python -m app.prune --execute` (jobs you saved/applied to are never deleted).
2. **Web-search discovery** — ATS job pages are public and search-indexed, so the
   daily discovery job runs `site:boards.greenhouse.io "<keyword>"` style queries
   (DuckDuckGo, no API key) for every keyword × ATS platform, extracts the company
   slugs from result URLs, validates each against the ATS API, and registers the
   board. This is how keywords reach across *all* of Greenhouse/Lever/Ashby/etc.
   despite those APIs being per-company.
3. **LLM discovery (optional)** — set `ANTHROPIC_API_KEY` and the discovery job also
   asks Claude (with web search) for companies currently hiring your keywords,
   registering any ATS boards it returns. Uses Haiku — costs pennies per day.
4. **Scraper-sourced discovery** — companies surfaced by keyword sources (LinkedIn,
   Naukri, RemoteOK, WeWorkRemotely) are probed for ATS boards too.
   Run everything manually with `python -m app.worker --discover`.
5. **Seed companies** — `companies.yaml` is just a starter/extras list for boards you
   care about explicitly; the pipeline no longer depends on it.

## Adding companies manually

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
| LinkedIn | Guest search endpoint (no login) | off (`ENABLE_LINKEDIN=true`) |

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
- **LinkedIn** uses the guest search endpoint (anonymous, no credentials). Scraping
  LinkedIn violates their ToS and they rate-limit hard (HTTP 429/999) — volume is kept
  low (2 pages per keyword), descriptions are not fetched, and a fully blocked run is
  recorded as an error without affecting other sources. Your IP can still get
  temporarily blocked; disable if that becomes a problem.
