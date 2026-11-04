"""Load the researched guides from seed_data/guides/*.json into `applications`.

Repeatable ("idempotent"): running it twice gives the same result. New
slugs are inserted, existing slugs are updated in place. Adding a new
application to the directory = adding one JSON file and re-running this.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Application
from app.schemas.guide import GuideContent


class SeedRecord(BaseModel):
    """One seed file: the relational columns plus the guide content."""

    model_config = ConfigDict(extra="forbid")
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,99}$")
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    short_description: str = Field(min_length=1, max_length=500)
    guide_content: GuideContent


class SeedError(Exception):
    """A seed file is unreadable or invalid. Nothing is written when this is raised."""


@dataclass
class SeedResult:
    inserted: list[str]
    updated: list[str]


def load_seed_records(seed_dir: Path) -> list[SeedRecord]:
    files = sorted(seed_dir.glob("*.json"))
    if not files:
        raise SeedError(f"no seed files found in {seed_dir}")

    records: list[SeedRecord] = []
    for path in files:
        try:
            record = SeedRecord.model_validate(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, ValidationError) as error:
            raise SeedError(f"{path.name}: {error}") from error
        if path.stem != record.slug:
            raise SeedError(f"{path.name}: filename must match slug {record.slug!r}")
        records.append(record)
    return records


def seed_applications(db: Session, records: list[SeedRecord]) -> SeedResult:
    """Validate everything first, then write all rows in one transaction."""
    result = SeedResult(inserted=[], updated=[])
    for record in records:
        values = {
            "name": record.name,
            "category": record.category,
            "short_description": record.short_description,
            "guide_content": record.guide_content.model_dump(mode="json"),
            "is_published": True,
        }
        existing = db.scalar(select(Application).where(Application.slug == record.slug))
        if existing is None:
            db.add(Application(slug=record.slug, **values))
            result.inserted.append(record.slug)
        else:
            for column, value in values.items():
                setattr(existing, column, value)
            result.updated.append(record.slug)
    # One commit: either every file is applied or (on error) none is.
    db.commit()
    return result
