"""Upsert companies from companies.yaml into the DB.

Usage: python -m app.seed
"""

import yaml
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models import Company


def seed_companies() -> tuple[int, int]:
    with open(settings.companies_file) as f:
        data = yaml.safe_load(f)

    created, updated = 0, 0
    with SessionLocal() as db:
        for entry in data.get("companies", []):
            company = db.scalar(select(Company).where(Company.name == entry["name"]))
            if company is None:
                company = Company(name=entry["name"])
                db.add(company)
                created += 1
            else:
                updated += 1
            company.ats_type = entry.get("ats")
            company.ats_board_id = str(entry.get("board_id")) if entry.get("board_id") else None
            company.website = entry.get("website") or company.website
        db.commit()
    return created, updated


if __name__ == "__main__":
    created, updated = seed_companies()
    print(f"companies seeded: {created} created, {updated} updated")
