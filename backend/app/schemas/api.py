"""Request/response shapes for the HTTP API (separate from the stored guide content)."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.schemas.guide import Complexity, GuideContent, OAuthStatus


class ResultType(StrEnum):
    """generated_guides.result_type: one value per research outcome."""

    OAUTH_SUPPORTED = "oauth_supported"
    OAUTH_NOT_SUPPORTED = "oauth_not_supported"
    SUPPORT_NOT_FOUND = "support_not_found"
    INCONCLUSIVE = "inconclusive"

    @classmethod
    def from_oauth_status(cls, status: OAuthStatus) -> "ResultType":
        return {
            OAuthStatus.SUPPORTED: cls.OAUTH_SUPPORTED,
            OAuthStatus.NOT_SUPPORTED: cls.OAUTH_NOT_SUPPORTED,
            OAuthStatus.NOT_FOUND: cls.SUPPORT_NOT_FOUND,
            OAuthStatus.INCONCLUSIVE: cls.INCONCLUSIVE,
        }[status]


class ApplicationSummary(BaseModel):
    """One directory card (GET /api/applications)."""

    slug: str
    name: str
    category: str
    short_description: str
    complexity: Complexity


class ApplicationDetail(BaseModel):
    """A pre-built guide (GET /api/applications/{slug})."""

    slug: str
    name: str
    category: str
    short_description: str
    guide_content: GuideContent


class GeneratedGuideDetail(BaseModel):
    """An unlisted AI-generated guide (GET /api/guides/{public_id})."""

    public_id: str
    application_name: str
    result_type: ResultType
    created_at: datetime
    guide_content: GuideContent


class HealthResponse(BaseModel):
    status: str


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Every error the API returns has this shape: {"error": {"code": ..., "message": ...}}."""

    model_config = ConfigDict(json_schema_extra={"example": {"error": {"code": "not_found", "message": "Guide not found."}}})
    error: ErrorBody
