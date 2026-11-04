"""HTTP routes. Each one: read the request, call a service, return a Pydantic model.

No SQL here: queries live in app/services so they can be tested and reused.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.db.session import get_db
from app.schemas.api import ApplicationDetail, ApplicationSummary, ErrorResponse, GeneratedGuideDetail, HealthResponse
from app.services.applications import get_published_application, list_published_applications
from app.services.generated_guides import get_generated_guide

router = APIRouter(prefix="/api")

# `Depends(get_db)` asks FastAPI to call get_db() for each request and pass in
# the session; FastAPI also runs get_db's cleanup (closing it) afterwards.
DbSession = Annotated[Session, Depends(get_db)]
NOT_FOUND = {404: {"model": ErrorResponse}}


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    # Deliberately minimal: no versions, hostnames or database details.
    return HealthResponse(status="ok")


@router.get("/applications", response_model=list[ApplicationSummary])
def list_applications(db: DbSession) -> list[ApplicationSummary]:
    return list_published_applications(db)


@router.get("/applications/{slug}", response_model=ApplicationDetail, responses=NOT_FOUND)
def read_application(
    db: DbSession,
    slug: Annotated[str, Path(max_length=100)],
) -> ApplicationDetail:
    application = get_published_application(db, slug)
    if application is None:
        raise ApiError(404, "not_found", "No guide exists for this application.")
    return application


@router.get("/guides/{public_id}", response_model=GeneratedGuideDetail, responses=NOT_FOUND)
def read_generated_guide(
    db: DbSession,
    public_id: Annotated[str, Path(max_length=64)],
) -> GeneratedGuideDetail:
    # Unlisted, not private: anyone with the URL can read it. (The
    # X-Robots-Tag: noindex header is added to all API responses in main.py.)
    guide = get_generated_guide(db, public_id)
    if guide is None:
        raise ApiError(404, "not_found", "This guide does not exist.")
    return guide
