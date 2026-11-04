"""POST /api/research/stream over HTTP (fake OpenAI client) and the rate limiter."""

import copy
import json
from contextlib import nullcontext

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.research import get_client_factory, get_rate_limiter, get_research_session_factory
from app.core.config import get_settings
from app.services.research.rate_limit import ResearchRateLimiter

from .conftest import requires_db
from .fake_openai import successful_client


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def guide() -> dict:
    path = get_settings().seed_data_dir / "slack.json"
    return copy.deepcopy(json.loads(path.read_text(encoding="utf-8"))["guide_content"])


def install_fakes(client: TestClient, db: Session, limiter: ResearchRateLimiter) -> None:
    g = guide()
    fake = successful_client(g, consulted=[s["url"] for s in g["sources"]])
    app = client.app
    app.dependency_overrides[get_client_factory] = lambda: (lambda _settings: fake)
    app.dependency_overrides[get_research_session_factory] = lambda: (lambda: nullcontext(db))
    app.dependency_overrides[get_rate_limiter] = lambda: limiter


@requires_db
def test_stream_returns_sse_events_and_guide_is_readable(client: TestClient, seeded_db: Session) -> None:
    limiter = ResearchRateLimiter(per_ip_per_hour=5, per_day=10, max_concurrent=1)
    install_fakes(client, seeded_db, limiter)

    response = client.post("/api/research/stream", json={"application_name": "Example App"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(response.text)
    assert events[0] == ("progress", {"stage": "validating_input", "label": "Validating the application input", "state": "started"})
    name, payload = events[-1]
    assert name == "complete"

    # The saved guide opens by its unlisted URL and stays out of the directory.
    guide_response = client.get(f"/api/guides/{payload['public_id']}")
    assert guide_response.status_code == 200
    assert guide_response.json()["guide_content"]["application_name"] == "Example App"
    assert len(client.get("/api/applications").json()) == 6

    assert limiter._running == 0  # slot released after the stream ended


@requires_db
def test_rate_limit_returns_429_with_retry_after(client: TestClient, seeded_db: Session) -> None:
    limiter = ResearchRateLimiter(per_ip_per_hour=1, per_day=10, max_concurrent=1)
    install_fakes(client, seeded_db, limiter)
    assert client.post("/api/research/stream", json={"application_name": "A"}).status_code == 200
    second = client.post("/api/research/stream", json={"application_name": "B"})
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "rate_limited"
    assert int(second.headers["Retry-After"]) > 0


@requires_db
def test_oversized_body_rejected(client: TestClient, seeded_db: Session) -> None:
    install_fakes(client, seeded_db, ResearchRateLimiter(5, 10, 1))
    response = client.post("/api/research/stream", content=json.dumps({"application_name": "x" * 5000}),
                           headers={"Content-Type": "application/json"})
    assert response.status_code == 413


@requires_db
def test_invalid_input_is_reported_in_stream(client: TestClient, seeded_db: Session) -> None:
    install_fakes(client, seeded_db, ResearchRateLimiter(5, 10, 1))
    events = parse_sse(client.post("/api/research/stream", json={"application_name": "X", "website_url": "http://localhost"}).text)
    assert events[-1][0] == "error" and events[-1][1]["code"] == "invalid_input"


@requires_db
def test_cors_preflight_allows_post_from_frontend(client: TestClient) -> None:
    response = client.options("/api/research/stream", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


# ---- Rate limiter unit tests (no database) ----


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_limiter_per_ip_window_slides() -> None:
    clock = FakeClock()
    limiter = ResearchRateLimiter(per_ip_per_hour=2, per_day=100, max_concurrent=5, clock=clock)
    assert limiter.try_acquire("1.1.1.1").allowed and limiter.try_acquire("1.1.1.1").allowed
    assert limiter.try_acquire("1.1.1.1").reason == "ip_hourly"
    assert limiter.try_acquire("2.2.2.2").allowed  # other IPs unaffected
    clock.now += 3601
    assert limiter.try_acquire("1.1.1.1").allowed


def test_limiter_daily_and_concurrency() -> None:
    limiter = ResearchRateLimiter(per_ip_per_hour=100, per_day=2, max_concurrent=1, clock=FakeClock())
    assert limiter.try_acquire("a").allowed
    assert limiter.try_acquire("b").reason == "busy"
    limiter.release()
    assert limiter.try_acquire("b").allowed
    limiter.release()
    assert limiter.try_acquire("c").reason == "daily"
