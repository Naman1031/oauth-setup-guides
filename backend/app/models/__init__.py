"""Importing this package registers every model on Base.metadata (Alembic relies on that)."""

from app.models.application import Application
from app.models.generated_guide import GeneratedGuide

__all__ = ["Application", "GeneratedGuide"]
