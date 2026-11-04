"""The `generated_guides` table: completed AI research results, reachable only by unlisted URL."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

class GeneratedGuide(Base):
    __tablename__ = "generated_guides"
    __table_args__ = (
        # The database itself rejects any other value, even if Python code has a bug.
        CheckConstraint(
            "result_type IN ('oauth_supported', 'oauth_not_supported', 'support_not_found', 'inconclusive')",
            name="ck_generated_guides_result_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Random, unguessable ID used in the share URL. The UUID `id` is never exposed.
    public_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    application_name: Mapped[str] = mapped_column(String(200), nullable=False)
    submitted_website_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    result_type: Mapped[str] = mapped_column(String(32), nullable=False)
    guide_content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
