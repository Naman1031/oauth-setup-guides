"""HTTP API tests using FastAPI's TestClient (requests go straight to the app, no network)."""

import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.schemas.guide import GuideContent
from app.services.generated_guides import create_generated_guide

from .conftest import requires_db

ALL_SLUGS = ["discord", "github", "google-drive", "hubspot", "notion", "slack"]


def seed_file(slug: str) -> dict:
    return json.loads((get_settings().seed_data_dir / f"{slug}.json").read_text(encoding="utf-8"))


@requires_db
def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}  # nothing else is exposed


@requires_db
def test_list_applications(client: TestClient) -> None:
    response = client.get("/api/applications")
    assert response.status_code == 200
    body = response.json()
    assert [app["slug"] for app in body] == ALL_SLUGS  # sorted by name
    assert set(body[0]) == {"slug", "name", "category", "short_description", "complexity"}
    github = next(app for app in body if app["slug"] == "github")
    assert github["complexity"] == "easy"


@requires_db
@pytest.mark.parametrize("slug", ALL_SLUGS)
def test_read_each_application_guide(client: TestClient, slug: str) -> None:
    response = client.get(f"/api/applications/{slug}")
    assert response.status_code == 200
    body = response.json()
    expected = seed_file(slug)
    assert body["name"] == expected["name"]
    assert body["guide_content"] == expected["guide_content"]


@requires_db
def test_unknown_application_is_404_with_error_shape(client: TestClient) -> None:
    response = client.get("/api/applications/not-a-real-app")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "No guide exists for this application."}}


@requires_db
def test_generated_guide_roundtrip_and_noindex(client: TestClient, seeded_db: Session) -> None:
    guide = GuideContent.model_validate(seed_file("notion")["guide_content"])
    row = create_generated_guide(seeded_db, guide, submitted_website_url=None)

    response = client.get(f"/api/guides/{row.public_id}")
    assert response.status_code == 200
    assert response.headers["X-Robots-Tag"] == "noindex, nofollow"
    body = response.json()
    assert body["public_id"] == row.public_id
    assert body["result_type"] == "oauth_supported"
    assert "id" not in body  # the internal UUID is never exposed

    # Unlisted: a generated guide never shows up in the public directory.
    directory = client.get("/api/applications").json()
    assert len(directory) == 6


@requires_db
@pytest.mark.parametrize("public_id", ["unknown", "A" * 43])
def test_unknown_generated_guide_is_404(client: TestClient, public_id: str) -> None:
    response = client.get(f"/api/guides/{public_id}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert response.headers["X-Robots-Tag"] == "noindex, nofollow"  # error responses too


@requires_db
def test_unknown_route_uses_error_shape(client: TestClient) -> None:
    response = client.get("/api/nothing-here")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Not found."}}


@requires_db
def test_cors_allows_configured_origin_only(client: TestClient) -> None:
    preflight = {"Access-Control-Request-Method": "GET"}
    allowed = client.options("/api/applications", headers={"Origin": "http://localhost:5173", **preflight})
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    blocked = client.options("/api/applications", headers={"Origin": "https://evil.example", **preflight})
    assert "access-control-allow-origin" not in blocked.headers


@requires_db
def test_unexpected_errors_are_safe(seeded_db: Session) -> None:
    from app.db.session import get_db
    from app.main import app

    def broken_db():
        raise RuntimeError("secret connection string postgres://user:pw@host")

    app.dependency_overrides[get_db] = broken_db
    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            response = test_client.get("/api/applications")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 500
    assert response.json() == {"error": {"code": "internal_error", "message": "Something went wrong. Please try again later."}}
    assert "secret" not in response.text


def test_settings_reject_wildcard_cors(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(ValidationError):
        Settings()  # type: ignore[call-arg]


def test_settings_split_origins_and_normalize_db_url(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example, https://b.example/")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:5432/d")
    settings = Settings()  # type: ignore[call-arg]
    assert settings.cors_origins == ["https://a.example", "https://b.example"]
    assert settings.database_url.startswith("postgresql+psycopg://")


SECURITY_HEADER_VALUES = {
    "x-robots-tag": "noindex, nofollow",
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
}


def assert_security_headers(response) -> None:
    for name, value in SECURITY_HEADER_VALUES.items():
        assert response.headers.get(name) == value, (name, response.status_code)


@requires_db
def test_security_headers_on_success_404_and_preflight(client: TestClient) -> None:
    assert_security_headers(client.get("/api/applications"))
    assert_security_headers(client.get("/api/applications/nope"))
    assert_security_headers(client.get("/api/does-not-exist"))
    assert_security_headers(client.options("/api/applications", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"}))


@requires_db
def test_security_headers_on_unexpected_500(seeded_db: Session) -> None:
    from app.db.session import get_db
    from app.main import app

    def broken_db():
        raise RuntimeError("boom")

    app.dependency_overrides[get_db] = broken_db
    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            response = test_client.get("/api/applications")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 500
    assert_security_headers(response)


def test_production_requires_https_cors(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", "http://insecure.example")
    with pytest.raises(ValidationError, match="https"):
        Settings()  # type: ignore[call-arg]
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example")
    assert Settings().cors_origins == ["https://app.example"]  # type: ignore[call-arg]


def test_configuration_errors_never_print_secret_values(monkeypatch) -> None:
    from app.core.config import ConfigurationError, get_settings

    secret = "sk-THIS-MUST-NOT-APPEAR-1234567890"
    db_secret = "postgresql://user:VerySecretDbPassword@db.example:5432/x_test"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    monkeypatch.setenv("DATABASE_URL", db_secret)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", "http://insecure.example")
    get_settings.cache_clear()
    try:
        with pytest.raises(ConfigurationError) as excinfo:
            get_settings()
        text = str(excinfo.value) + repr(excinfo.value.__cause__) + repr(excinfo.value.__context__ if excinfo.value.__suppress_context__ is False else None)
        assert "CORS_ORIGINS must be https" in str(excinfo.value)
        assert secret not in text and "VerySecretDbPassword" not in text
    finally:
        get_settings.cache_clear()
