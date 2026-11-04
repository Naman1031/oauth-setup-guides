"""The research workflow: ONE sequential Python generator, no agent framework.

It yields (event_name, payload) pairs that the route sends to the browser
as Server-Sent Events. Every "progress" event is emitted at the moment the
corresponding backend work actually starts or finishes; there are no timers.

Stages:
  1. validating_input         – our Pydantic/URL safety checks
  2. searching_documentation  – starts when the OpenAI call is sent; completes
                                when the model begins writing the guide
  3. analysing_requirements   – the model writing the structured guide, until
                                the response completes
  4. validating_guide         – JSON → schema → evidence reconciliation → usefulness
  5. saving_result            – insert into generated_guides (only if all passed)
"""

import logging
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.schemas.api import ResultType
from app.schemas.guide import GuideContent
from app.schemas.research import ERROR_MESSAGES, RETRYABLE, STAGE_LABELS, ErrorCode, ResearchRequest, Stage
from app.services.generated_guides import create_generated_guide
from app.services.research.evidence import check_useful, presanitize, reconcile
from app.services.research.openai_runner import ResearchCallResult, ResearchError, ResponsesClient, StreamSignal, run_research_call

logger = logging.getLogger(__name__)

Event = tuple[str, dict[str, Any]]


def progress(stage: Stage, state: str) -> Event:
    return "progress", {"stage": stage.value, "label": STAGE_LABELS[stage], "state": state}


def error_event(code: ErrorCode) -> Event:
    return "error", {"code": code.value, "message": ERROR_MESSAGES[code], "retryable": code in RETRYABLE}


def run_research(
    raw_input: dict[str, Any],
    settings: Settings,
    client_factory: Callable[[Settings], ResponsesClient],
    session_factory: Callable[[], Session],
) -> Iterator[Event]:
    """Yield progress events, then exactly one `complete` or `error` event."""
    stage = Stage.VALIDATING_INPUT
    try:
        # ---- 1. Validate input ----
        yield progress(stage, "started")
        try:
            request = ResearchRequest.model_validate(raw_input)
        except ValidationError:
            yield error_event(ErrorCode.INVALID_INPUT)
            return
        client = client_factory(settings)  # raises NOT_CONFIGURED if no key/model
        yield progress(stage, "completed")

        # ---- 2 + 3. One streamed OpenAI call ----
        stage = Stage.SEARCHING_DOCUMENTATION
        yield progress(stage, "started")
        today = datetime.now(UTC).date()
        searches_completed = 0
        result: ResearchCallResult | None = None
        for item in run_research_call(client, settings, request.application_name, request.website_url, today):
            if isinstance(item, ResearchCallResult):
                result = item
            elif item.kind == "search_completed":
                searches_completed += 1
                # A concise, factual finding: how many searches have finished.
                yield "activity", {"web_searches_completed": searches_completed}
            elif item.kind == "writing_started" and stage == Stage.SEARCHING_DOCUMENTATION:
                yield progress(stage, "completed")
                stage = Stage.ANALYSING_REQUIREMENTS
                yield progress(stage, "started")
        if result is None:  # defensive: the runner always yields a result or raises
            raise ResearchError(ErrorCode.INTERNAL_ERROR, "no result from research call")
        if stage == Stage.SEARCHING_DOCUMENTATION:  # model never streamed text deltas
            yield progress(stage, "completed")
            stage = Stage.ANALYSING_REQUIREMENTS
            yield progress(stage, "started")
        yield progress(stage, "completed")

        # ---- 4. Validate the guide and its evidence ----
        stage = Stage.VALIDATING_GUIDE
        yield progress(stage, "started")
        try:
            guide = GuideContent.model_validate(presanitize(result.raw_guide))
            guide, report = reconcile(guide, result.trace, request.application_name, today)
        except ValidationError as error:
            # Field paths only; never log the model's full text.
            fields = sorted({".".join(str(p) for p in e["loc"]) for e in error.errors()})[:10]
            raise ResearchError(ErrorCode.INVALID_RESULT, f"schema validation failed at {fields}") from error
        problem = check_useful(guide)
        if problem:
            raise ResearchError(ErrorCode.INVALID_RESULT, problem)
        logger.info(
            "research reconciled: sources_kept=%d dropped=%d downgraded_claims=%d portal_downgraded=%s",
            len(guide.sources), len(report.dropped_sources), report.downgraded_claims, report.portal_downgraded,
        )
        yield progress(stage, "completed")

        # ---- 5. Save (only reached when everything above passed) ----
        stage = Stage.SAVING_RESULT
        yield progress(stage, "started")
        try:
            with session_factory() as db:
                row = create_generated_guide(db, guide, request.website_url)
        except Exception as error:
            raise ResearchError(ErrorCode.SAVE_FAILED, f"{type(error).__name__}") from error
        yield progress(stage, "completed")

        yield "complete", {
            "public_id": row.public_id,
            "guide_path": f"/guides/{row.public_id}",
            "result_type": ResultType(row.result_type).value,
            "application_name": row.application_name,
        }
    except ResearchError as error:
        logger.warning("research failed at %s: %s (%s)", stage.value, error.code.value, error.detail)
        yield error_event(error.code)
    except Exception:
        logger.exception("unexpected research failure at %s", stage.value)
        yield error_event(ErrorCode.INTERNAL_ERROR)
