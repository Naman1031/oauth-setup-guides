"""Database operations for unlisted AI-generated guides.

`create_generated_guide` is used by the research workflow in Phase 3. It
only accepts an already-validated GuideContent, so an invalid or empty
result can't be stored by accident.
"""

import re
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import GeneratedGuide
from app.schemas.api import GeneratedGuideDetail, ResultType
from app.schemas.guide import GuideContent

# 32 random bytes → 43 URL-safe characters (256 bits of randomness).
# Guessing a valid one is practically impossible, unlike a sequential ID.
PUBLIC_ID_BYTES = 32
PUBLIC_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43}$")


def new_public_id() -> str:
    # `secrets` (not `random`) uses the operating system's cryptographic randomness.
    return secrets.token_urlsafe(PUBLIC_ID_BYTES)


def is_valid_public_id(value: str) -> bool:
    return bool(PUBLIC_ID_PATTERN.fullmatch(value))


def create_generated_guide(
    db: Session,
    guide: GuideContent,
    submitted_website_url: str | None,
) -> GeneratedGuide:
    row = GeneratedGuide(
        public_id=new_public_id(),
        application_name=guide.application_name,
        submitted_website_url=submitted_website_url,
        result_type=ResultType.from_oauth_status(guide.oauth_status).value,
        # mode="json" turns dates and enums into plain JSON values for JSONB.
        guide_content=guide.model_dump(mode="json"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)  # load database-generated values such as created_at
    return row


def get_generated_guide(db: Session, public_id: str) -> GeneratedGuideDetail | None:
    if not is_valid_public_id(public_id):
        return None  # don't even query the database for malformed IDs
    row = db.scalar(select(GeneratedGuide).where(GeneratedGuide.public_id == public_id))
    if row is None:
        return None
    return GeneratedGuideDetail(
        public_id=row.public_id,
        application_name=row.application_name,
        result_type=ResultType(row.result_type),
        created_at=row.created_at,
        guide_content=GuideContent.model_validate(row.guide_content),
    )
