"""Adds security headers to EVERY HTTP response, including errors and streams.

Written as a plain ASGI middleware (rather than @app.middleware("http")):
it only touches the response's start message, so it never buffers streamed
(SSE) bodies. The one response it can't reach is Starlette's built-in crash
handler, which sits outside all middleware; app/api/errors.py adds the same
headers there.
"""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

SECURITY_HEADERS: list[tuple[bytes, bytes]] = [
    # API JSON is data, not pages: never index it (also covers unlisted guides).
    (b"x-robots-tag", b"noindex, nofollow"),
    # Browsers must not guess a different content type (e.g. treat JSON as HTML).
    (b"x-content-type-options", b"nosniff"),
    # The API is never meant to be shown inside a frame.
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
]


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                existing = {name.lower() for name, _ in message.get("headers", [])}
                extra = [(name, value) for name, value in SECURITY_HEADERS if name not in existing]
                message["headers"] = list(message.get("headers", [])) + extra
            await send(message)

        await self.app(scope, receive, send_with_headers)
