"""A stand-in for the OpenAI client so research tests cost nothing.

It mimics only what our code uses: client.responses.stream(...) as a context
manager that yields events and offers get_final_response().
"""

import json
from types import SimpleNamespace as NS
from typing import Any


def search_call(query: str, urls: list[str]) -> NS:
    return NS(type="web_search_call", status="completed",
              action=NS(type="search", query=query, queries=None, sources=[NS(type="url", url=u) for u in urls]))


def open_page_call(url: str) -> NS:
    return NS(type="web_search_call", status="completed", action=NS(type="open_page", url=url))


def message(text: str) -> NS:
    return NS(type="message", content=[NS(type="output_text", text=text, annotations=[])])


def refusal_message() -> NS:
    return NS(type="message", content=[NS(type="refusal", refusal="I can't help with that.")])


class FakeStream:
    def __init__(self, events: list[NS], final: NS) -> None:
        self._events, self._final = events, final

    def __enter__(self) -> "FakeStream":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None

    def __iter__(self):
        yield from self._events

    def get_final_response(self) -> NS:
        return self._final


class FakeResponses:
    def __init__(self, stream: FakeStream | None = None, error: Exception | None = None) -> None:
        self._stream, self._error = stream, error
        self.calls: list[dict[str, Any]] = []

    def stream(self, **kwargs: Any) -> FakeStream:
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        assert self._stream is not None
        return self._stream


class FakeClient:
    def __init__(self, responses: FakeResponses) -> None:
        self.responses = responses


def successful_client(guide: dict[str, Any], consulted: list[str], opened: list[str] | None = None,
                      status: str = "completed", output_override: list[NS] | None = None,
                      incomplete_reason: str | None = None) -> FakeClient:
    """A client whose single call searches, optionally opens pages, then returns `guide` as JSON."""
    output = output_override if output_override is not None else [
        search_call("example oauth app setup", consulted),
        *[open_page_call(u) for u in (opened or [])],
        message(json.dumps(guide)),
    ]
    events = [
        NS(type="response.created"),
        NS(type="response.web_search_call.in_progress"),
        NS(type="response.web_search_call.searching"),
        NS(type="response.web_search_call.completed"),
        NS(type="response.output_text.delta", delta="{"),
        NS(type="response.output_text.delta", delta="..."),
        NS(type="response.completed"),
    ]
    final = NS(status=status, output=output, incomplete_details=NS(reason=incomplete_reason),
               usage=NS(input_tokens=1200, output_tokens=3400, output_tokens_details=NS(reasoning_tokens=900)))
    return FakeClient(FakeResponses(FakeStream(events, final)))
