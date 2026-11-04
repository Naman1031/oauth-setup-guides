"""Database tests: migrations, constraints, seeding and guide storage."""

import json

import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Application, GeneratedGuide
from app.schemas.guide import GuideContent
from app.services.applications import get_published_application, list_published_applications
from app.services.generated_guides import create_generated_guide, get_generated_guide, is_valid_public_id
from app.services.seeding import SeedError, load_seed_records, seed_applications

from .conftest import requires_db

pytestmark = requires_db


def github_guide() -> GuideContent:
    path = get_settings().seed_data_dir / "github.json"
    return GuideContent.model_validate(json.loads(path.read_text(encoding="utf-8"))["guide_content"])


def test_migration_creates_tables_and_indexes(db: Session) -> None:
    inspector = inspect(db.connection())
    assert {"applications", "generated_guides"} <= set(inspector.get_table_names())
    app_indexes = {ix["name"]: ix for ix in inspector.get_indexes("applications")}
    assert app_indexes["ix_applications_slug"]["unique"]
    assert "ix_applications_is_published" in app_indexes
    guide_indexes = {ix["name"]: ix for ix in inspector.get_indexes("generated_guides")}
    assert guide_indexes["ix_generated_guides_public_id"]["unique"]


def test_row_level_security_is_enabled(db: Session) -> None:
    # Blocks Supabase's auto-generated Data API from reading our tables.
    rows = db.execute(
        text("SELECT relname, relrowsecurity FROM pg_class WHERE relname IN ('applications', 'generated_guides')")
    ).all()
    assert dict(rows) == {"applications": True, "generated_guides": True}


def test_seeding_inserts_six_then_updates_idempotently(db: Session) -> None:
    records = load_seed_records(get_settings().seed_data_dir)
    first = seed_applications(db, records)
    second = seed_applications(db, records)
    assert len(first.inserted) == 6 and first.updated == []
    assert second.inserted == [] and len(second.updated) == 6
    assert db.scalar(select(func.count()).select_from(Application)) == 6


def test_seeded_content_is_stored_unchanged(seeded_db: Session) -> None:
    stored = seeded_db.scalar(select(Application.guide_content).where(Application.slug == "github"))
    path = get_settings().seed_data_dir / "github.json"
    assert stored == json.loads(path.read_text(encoding="utf-8"))["guide_content"]


def test_invalid_seed_file_writes_nothing(db: Session, tmp_path) -> None:
    good = (get_settings().seed_data_dir / "github.json").read_text(encoding="utf-8")
    (tmp_path / "github.json").write_text(good, encoding="utf-8")
    (tmp_path / "broken.json").write_text('{"slug": "broken"}', encoding="utf-8")
    with pytest.raises(SeedError):
        load_seed_records(tmp_path)
    assert db.scalar(select(func.count()).select_from(Application)) == 0


def test_seed_filename_must_match_slug(tmp_path) -> None:
    good = (get_settings().seed_data_dir / "github.json").read_text(encoding="utf-8")
    (tmp_path / "wrong-name.json").write_text(good, encoding="utf-8")
    with pytest.raises(SeedError, match="filename must match slug"):
        load_seed_records(tmp_path)


def test_slug_must_be_unique(seeded_db: Session) -> None:
    duplicate = Application(slug="github", name="Dup", category="x", short_description="x", guide_content={})
    seeded_db.add(duplicate)
    with pytest.raises(IntegrityError):
        seeded_db.flush()


def test_result_type_check_constraint(db: Session) -> None:
    db.add(GeneratedGuide(public_id="x" * 43, application_name="X", result_type="made_up", guide_content={}))
    with pytest.raises(IntegrityError, match="ck_generated_guides_result_type"):
        db.flush()


def test_timestamps_are_set_by_the_database(seeded_db: Session) -> None:
    row = seeded_db.scalar(select(Application).where(Application.slug == "slack"))
    assert row.created_at is not None and row.created_at.tzinfo is not None


def test_unpublished_application_is_hidden(seeded_db: Session) -> None:
    seeded_db.execute(text("UPDATE applications SET is_published = false WHERE slug = 'notion'"))
    assert "notion" not in {app.slug for app in list_published_applications(seeded_db)}
    assert get_published_application(seeded_db, "notion") is None


def test_create_and_read_generated_guide(db: Session) -> None:
    row = create_generated_guide(db, github_guide(), submitted_website_url="https://github.com")
    assert is_valid_public_id(row.public_id)
    assert row.result_type == "oauth_supported"

    detail = get_generated_guide(db, row.public_id)
    assert detail is not None
    assert detail.guide_content == github_guide()
    assert detail.application_name == "GitHub"


def test_public_ids_are_random_and_unique(db: Session) -> None:
    ids = {create_generated_guide(db, github_guide(), None).public_id for _ in range(5)}
    assert len(ids) == 5


@pytest.mark.parametrize("bad_id", ["", "short", "x" * 44, "../../etc/passwd" + "a" * 27, "a" * 42 + "!"])
def test_malformed_public_id_returns_none(db: Session, bad_id: str) -> None:
    assert get_generated_guide(db, bad_id) is None
