"""End-to-end acceptance checks against a RUNNING deployment (local or live).

Costs nothing: it never starts a real research run. (Invalid research
inputs are rejected before any OpenAI call, so those checks are free too.)

Usage (from backend/):
  python -m scripts.e2e_check --api http://localhost:8000 --frontend-origin http://localhost:5173
  python -m scripts.e2e_check --api https://<api>.onrender.com --frontend https://<app>.vercel.app \
      --guide-id <public_id> --production

Exit code 0 = all checks passed.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

EXPECTED_APPS = {"GitHub", "Slack", "Google Drive", "Notion", "HubSpot", "Discord"}
GUIDE_FIELDS = {
    "application_name", "oauth_status", "summary", "complexity", "complexity_rationale", "prerequisites",
    "setup_steps", "permissions_scopes", "credentials_configuration", "time_approval", "agent_human_tasks",
    "portal_exploration", "composio_managed_oauth", "common_issues", "sources", "evidence_notes",
    "tested_status", "last_researched_at", "checklist_items",
}
SECURITY_HEADERS = {"x-robots-tag": "noindex", "x-content-type-options": "nosniff"}

results: list[tuple[bool, str]] = []


def check(ok: bool, label: str) -> None:
    results.append((ok, label))
    print(f"{'PASS' if ok else 'FAIL'}  {label}")


def request(method: str, url: str, body: dict | None = None, headers: dict | None = None, timeout: int = 90):
    """Return (status, headers-dict-lowercased, text). Never raises for HTTP errors."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"User-Agent": "e2e-check", **(headers or {})})
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as err:
        return err.code, {k.lower(): v for k, v in err.headers.items()}, err.read().decode("utf-8", "replace")


def api_checks(api: str, frontend_origin: str | None, guide_id: str | None, production: bool) -> None:
    status, headers, text = request("GET", f"{api}/api/health")
    check(status == 200 and json.loads(text) == {"status": "ok"}, "health returns only {'status': 'ok'}")
    check(all(v in headers.get(k, "") for k, v in SECURITY_HEADERS.items()), "API sends noindex + nosniff headers")

    status, _, text = request("GET", f"{api}/api/applications")
    apps = json.loads(text) if status == 200 else []
    check({a["name"] for a in apps} == EXPECTED_APPS, f"directory lists exactly the six apps ({len(apps)} found)")
    for name in sorted(EXPECTED_APPS):
        check(sum(name.lower() in a["name"].lower() for a in apps) == 1, f"search term '{name}' matches exactly one card")

    for app in apps:
        status, _, text = request("GET", f"{api}/api/applications/{app['slug']}")
        guide = json.loads(text).get("guide_content", {}) if status == 200 else {}
        ok = (
            status == 200
            and GUIDE_FIELDS <= set(guide)
            and len(guide["sources"]) > 0
            and guide["tested_status"]["status"] in ("tested", "not_tested")
            and guide["composio_managed_oauth"]["availability"]
            and any("evidence_label" in step for step in guide["setup_steps"])
        )
        check(bool(ok), f"{app['slug']}: same schema, sources, evidence labels, tested status, Composio section")

    status, _, text = request("GET", f"{api}/api/applications/not-a-real-app")
    check(status == 404 and json.loads(text)["error"]["code"] == "not_found", "unknown slug → 404 with error shape")
    status, headers, _ = request("GET", f"{api}/api/guides/{'A' * 43}")
    check(status == 404 and "noindex" in headers.get("x-robots-tag", ""), "unknown guide id → 404 (noindex)")

    for bad in ["javascript:alert(1)", "ftp://example.com", "http://localhost:8000", "http://10.0.0.1",
                "http://169.254.169.254/latest", "https://user:pw@example.com", "not a url"]:
        status, _, text = request("POST", f"{api}/api/research/stream", {"application_name": "X", "website_url": bad})
        check(status == 422, f"research rejects unsafe URL {bad!r} (422, no OpenAI call)")

    if frontend_origin:
        status, headers, _ = request("OPTIONS", f"{api}/api/research/stream", headers={
            "Origin": frontend_origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})
        check(headers.get("access-control-allow-origin") == frontend_origin, f"CORS allows {frontend_origin}")
    status, headers, _ = request("GET", f"{api}/api/applications", headers={"Origin": "https://evil.example"})
    check("access-control-allow-origin" not in headers, "CORS does not allow an arbitrary origin")

    if production:
        status, _, _ = request("GET", f"{api}/docs")
        check(status == 404, "interactive /docs disabled in production")

    if guide_id:
        status, headers, text = request("GET", f"{api}/api/guides/{guide_id}")
        check(status == 200 and "noindex" in headers.get("x-robots-tag", ""), "generated guide opens by its unlisted id (noindex)")
        name = json.loads(text)["application_name"] if status == 200 else None
        check(name not in {a["name"] for a in apps}, "generated guide does not appear in the directory")


def frontend_checks(frontend: str, guide_id: str | None) -> None:
    status, headers, text = request("GET", f"{frontend}/")
    check(status == 200 and '<div id="root">' in text, "frontend home page served")
    check("content-security-policy" in headers, "frontend sends a Content-Security-Policy")
    status, _, text = request("GET", f"{frontend}/apps/github")
    check(status == 200 and '<div id="root">' in text, "deep link /apps/github served (SPA rewrite)")
    path = f"/guides/{guide_id or 'A' * 43}"
    status, headers, _ = request("GET", f"{frontend}{path}")
    check(status == 200 and "noindex" in headers.get("x-robots-tag", ""), f"{path.split('/')[1]} page sends X-Robots-Tag: noindex")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api", required=True, help="API base URL, e.g. http://localhost:8000")
    parser.add_argument("--frontend", help="frontend URL (deployed); enables header/rewrite checks")
    parser.add_argument("--frontend-origin", help="origin that CORS must allow (defaults to --frontend)")
    parser.add_argument("--guide-id", help="public_id of an existing generated guide")
    parser.add_argument("--production", action="store_true", help="also check production-only settings")
    args = parser.parse_args()

    api = args.api.rstrip("/")
    frontend = args.frontend.rstrip("/") if args.frontend else None
    api_checks(api, args.frontend_origin or frontend, args.guide_id, args.production)
    if frontend:
        frontend_checks(frontend, args.guide_id)

    failed = [label for ok, label in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
