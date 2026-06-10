from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://jobscrap:jobscrap@localhost:5433/jobscrap"
    redis_url: str = "redis://localhost:6380/0"

    scrape_interval_easy_hours: float = 4
    scrape_interval_hard_hours: float = 6

    enable_naukri: bool = False
    enable_wellfound: bool = False
    enable_linkedin: bool = False

    # Optional: enables LLM-assisted company discovery
    anthropic_api_key: str | None = None

    # Drives both what keyword sources search for and which scraped jobs are
    # kept — a job is stored only if its title/tags contain one of these.
    search_keywords: str = (
        "software engineer,software developer,developer,full stack,"
        "backend,frontend,front end,back end,devops,sde,data engineer"
    )
    search_location: str = "india"

    companies_file: Path = BACKEND_DIR / "companies.yaml"

    @property
    def keyword_list(self) -> list[str]:
        return [k.strip() for k in self.search_keywords.split(",") if k.strip()]


settings = Settings()
