"""Create the two MVP tables: applications and generated_guides.

Revision ID: 0001
Revises:
Create Date: 2026-11-04
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("short_description", sa.String(500), nullable=False),
        sa.Column("guide_content", postgresql.JSONB(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    # A unique index both speeds up lookups by slug and forbids duplicates.
    op.create_index("ix_applications_slug", "applications", ["slug"], unique=True)
    op.create_index("ix_applications_is_published", "applications", ["is_published"])

    op.create_table(
        "generated_guides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("public_id", sa.String(64), nullable=False),
        sa.Column("application_name", sa.String(200), nullable=False),
        sa.Column("submitted_website_url", sa.String(2048), nullable=True),
        sa.Column("result_type", sa.String(32), nullable=False),
        sa.Column("guide_content", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "result_type IN ('oauth_supported', 'oauth_not_supported', 'support_not_found', 'inconclusive')",
            name="ck_generated_guides_result_type",
        ),
    )
    op.create_index("ix_generated_guides_public_id", "generated_guides", ["public_id"], unique=True)

    # Supabase auto-exposes tables in the `public` schema through its REST
    # "Data API". Our frontend never uses it, so we turn on Row Level Security
    # with NO policies: the Data API's anon/authenticated roles can read and
    # write nothing. The backend connects as the table owner, which bypasses
    # RLS, so the app itself is unaffected. (Harmless on plain PostgreSQL.)
    op.execute("ALTER TABLE applications ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE generated_guides ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_generated_guides_public_id", table_name="generated_guides")
    op.drop_table("generated_guides")
    op.drop_index("ix_applications_is_published", table_name="applications")
    op.drop_index("ix_applications_slug", table_name="applications")
    op.drop_table("applications")
