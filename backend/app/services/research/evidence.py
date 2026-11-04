"""Check the model's claims against what the API reports actually happened.

The model WRITES the guide, but the Responses API separately REPORTS the
web-search actions it performed (searches, pages opened, find-in-page) and
the URLs it consulted. We trust the report over the prose:

- a source survives only if its URL was actually consulted;
- claims that lose all their sources drop from "verified" to "unknown";
- "pages inspected" keeps only pages the agent really opened;
- "safe actions attempted" is generated from the real action log;
- dates, domains and the tested status are set by us, not the model.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.schemas.guide import EvidenceLabel, GuideContent, PortalExplorationStatus

MAX_LISTED_ACTIONS = 20


# ---------- What actually happened ----------


@dataclass
class ResearchTrace:
    """Facts extracted from the API's output items (not from the model's text)."""

    search_queries: list[str] = field(default_factory=list)
    opened_pages: list[str] = field(default_factory=list)
    find_in_page: list[tuple[str, str | None]] = field(default_factory=list)
    consulted_urls: set[str] = field(default_factory=set)  # normalized
    web_search_calls: int = 0


def _get(obj: Any, name: str) -> Any:
    """Read a field from an SDK object or a plain dict (tests use dicts)."""
    return obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)


def normalize_url(url: str) -> str:
    """Compare URLs loosely: lowercase scheme/host, drop fragment, trailing slash and utm_* tracking."""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return url
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith("utm_")])
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, query, ""))


def extract_trace(response_output: list[Any]) -> ResearchTrace:
    trace = ResearchTrace()
    for item in response_output or []:
        item_type = _get(item, "type")
        if item_type == "web_search_call":
            trace.web_search_calls += 1
            action = _get(item, "action")
            action_type = _get(action, "type") if action is not None else None
            if action_type == "search":
                queries = _get(action, "queries") or []
                query = _get(action, "query")
                trace.search_queries.extend(q for q in [*queries, query] if q)
                for source in _get(action, "sources") or []:
                    if _get(source, "url"):
                        trace.consulted_urls.add(normalize_url(_get(source, "url")))
            elif action_type == "open_page" and _get(action, "url"):
                trace.opened_pages.append(_get(action, "url"))
                trace.consulted_urls.add(normalize_url(_get(action, "url")))
            elif action_type == "find_in_page":
                url = _get(action, "url")
                trace.find_in_page.append((_get(action, "pattern") or "", url))
                if url:
                    trace.consulted_urls.add(normalize_url(url))
        elif item_type == "message":
            # Inline url_citation annotations also point at consulted pages.
            for part in _get(item, "content") or []:
                for annotation in _get(part, "annotations") or []:
                    if _get(annotation, "type") == "url_citation" and _get(annotation, "url"):
                        trace.consulted_urls.add(normalize_url(_get(annotation, "url")))
    # Keep order but drop duplicates (the model may repeat a search or reopen a page).
    trace.search_queries = list(dict.fromkeys(trace.search_queries))
    trace.opened_pages = list(dict.fromkeys(trace.opened_pages))
    trace.find_in_page = list(dict.fromkeys(trace.find_in_page))
    return trace


# ---------- Reconciliation ----------


def presanitize(raw: dict[str, Any]) -> dict[str, Any]:
    """Before the first validation: force values only one answer is honest for.

    The agent never tests anything, so a "test-based" claim or a "tested"
    status from the model is wrong by definition; correct it rather than
    rejecting an otherwise useful result.
    """
    for note in raw.get("evidence_notes") or []:
        if isinstance(note, dict) and note.get("verification_basis") == "test":
            note["verification_basis"] = "documentation"
    if isinstance(raw.get("tested_status"), dict):
        raw["tested_status"]["status"] = "not_tested"
    return raw


@dataclass
class ReconcileReport:
    """What we changed, for logging and tests."""

    dropped_sources: list[str] = field(default_factory=list)
    downgraded_claims: int = 0
    portal_downgraded: bool = False


def _remove_ids(node: Any, removed: set[str], report: ReconcileReport) -> None:
    """Walk the guide dict: strip removed source ids; a 'verified' item left with no sources becomes 'unknown'."""
    if isinstance(node, dict):
        for key in ("source_ids", "review_source_ids"):
            if key in node:
                node[key] = [sid for sid in node[key] if sid not in removed]
        if node.get("evidence_label") == EvidenceLabel.VERIFIED.value and "source_ids" in node and not node["source_ids"]:
            node["evidence_label"] = EvidenceLabel.UNKNOWN.value
            if "verification_basis" in node:
                node["verification_basis"] = None
            report.downgraded_claims += 1
        for value in node.values():
            _remove_ids(value, removed, report)
    elif isinstance(node, list):
        for item in node:
            _remove_ids(item, removed, report)


def _actions_log(trace: ResearchTrace) -> list[str]:
    actions = [f"Web search: “{q}”" for q in trace.search_queries]
    actions += [f"Opened public page: {url}" for url in trace.opened_pages]
    actions += [f"Searched within {url or 'a page'} for “{pattern}”" for pattern, url in trace.find_in_page]
    if len(actions) > MAX_LISTED_ACTIONS:
        hidden = len(actions) - (MAX_LISTED_ACTIONS - 1)
        actions = actions[: MAX_LISTED_ACTIONS - 1] + [f"…and {hidden} more actions"]
    return actions or ["No web actions were recorded."]


def reconcile(guide: GuideContent, trace: ResearchTrace, application_name: str, today: date) -> tuple[GuideContent, ReconcileReport]:
    """Return a corrected copy of the guide (re-validated) and a report of the changes."""
    report = ReconcileReport()
    data = guide.model_dump(mode="json")

    # 1. Sources must have been consulted. Domain and date come from us.
    kept, removed = [], set()
    for source in data["sources"]:
        if normalize_url(source["url"]) in trace.consulted_urls:
            source["domain"] = (urlsplit(source["url"]).hostname or source["domain"]).lower()
            source["accessed_at"] = today.isoformat()
            kept.append(source)
        else:
            removed.add(source["id"])
            report.dropped_sources.append(source["url"])
    data["sources"] = kept
    _remove_ids(data, removed, report)

    # 2. Nothing was tested by the agent; "test-based" evidence is impossible.
    data["tested_status"] = {
        "status": "not_tested",
        "notes": "Generated by the research agent from public web sources. No setup step was performed or tested.",
    }

    # 3. Portal exploration: only pages that were really opened count.
    portal = data["portal_exploration"]
    opened = {normalize_url(url) for url in trace.opened_pages} | {normalize_url(url) for _, url in trace.find_in_page if url}
    portal["pages_inspected"] = [page for page in portal["pages_inspected"] if normalize_url(page["url"]) in opened]
    portal["safe_actions_attempted"] = _actions_log(trace)
    if not portal["pages_inspected"] and portal["status"] != PortalExplorationStatus.NOT_ATTEMPTED.value:
        portal["status"] = PortalExplorationStatus.NOT_ATTEMPTED.value
        portal["observations"] = [
            "The research agent did not open a setup portal page directly; findings come from search results and documentation.",
            *portal["observations"],
        ][:20]
        report.portal_downgraded = True

    # 4. Fields we own.
    data["application_name"] = application_name
    data["last_researched_at"] = today.isoformat()
    data["schema_version"] = 1

    # Re-run every schema rule (cross-references, labels, lengths) on the result.
    return GuideContent.model_validate(data), report


def check_useful(guide: GuideContent) -> str | None:
    """Reasons a validated guide is still not worth saving (spec: no empty/invalid results)."""
    if not guide.sources:
        return "no source could be confirmed from the web search results"
    if guide.oauth_status == "supported" and not guide.setup_steps:
        return "status is 'supported' but there are no setup steps"
    return None
