"""Database queries for the public application directory."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Application
from app.schemas.api import ApplicationDetail, ApplicationSummary
from app.schemas.guide import GuideContent


def list_published_applications(db: Session) -> list[ApplicationSummary]:
    # select(...).where(...) builds a parameterized SQL query: values are sent
    # separately from the SQL text, so they can't be used for SQL injection.
    rows = db.scalars(
        select(Application).where(Application.is_published.is_(True)).order_by(Application.name)
    ).all()
    return [
        ApplicationSummary(
            slug=row.slug,
            name=row.name,
            category=row.category,
            short_description=row.short_description,
            complexity=row.guide_content["complexity"],
        )
        for row in rows
    ]


def get_published_application(db: Session, slug: str) -> ApplicationDetail | None:
    """Returns None for unknown OR unpublished slugs; the route turns that into a 404."""
    row = db.scalar(
        select(Application).where(Application.slug == slug, Application.is_published.is_(True))
    )
    if row is None:
        return None
    return ApplicationDetail(
        slug=row.slug,
        name=row.name,
        category=row.category,
        short_description=row.short_description,
        # Re-validate on the way out: the API never returns a guide that breaks the schema.
        guide_content=GuideContent.model_validate(row.guide_content),
    )
