import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import applications, companies, jobs, scrape, settings, stats

app = FastAPI(title="Applyverse API")

# Comma-separated origins, or "*" for any. Behind the nginx reverse proxy the
# browser talks to /api on the same origin, so CORS is moot there; this only
# matters when the API is hit cross-origin (e.g. local dev on :3000).
_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _origins.strip() == "*" else
    [o.strip() for o in _origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/api")
app.include_router(applications.router, prefix="/api")
app.include_router(companies.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(scrape.router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
