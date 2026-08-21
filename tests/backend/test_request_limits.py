import asyncio
import json

from starlette.responses import PlainTextResponse
from starlette.types import Message, Receive, Scope, Send

from app.core.request_limits import (
    MAX_REQUEST_BODY_BYTES,
    RequestSizeLimitMiddleware,
)


async def _run_request(
    headers: list[tuple[bytes, bytes]],
    request_messages: list[Message],
) -> tuple[int, bytes, bool]:
    app_called = False
    sent_messages: list[Message] = []
    pending_messages = list(request_messages)

    async def receive() -> Message:
        if pending_messages:
            return pending_messages.pop(0)

        return {
            "type": "http.disconnect",
        }

    async def send(message: Message) -> None:
        sent_messages.append(message)

    async def app(
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        nonlocal app_called
        app_called = True

        while True:
            message = await receive()

            if message["type"] != "http.request":
                return

            if not message.get("more_body", False):
                break

        response = PlainTextResponse("ok")
        await response(scope, receive, send)

    scope: Scope = {
        "type": "http",
        "asgi": {
            "version": "3.0",
        },
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "state": {},
    }

    middleware = RequestSizeLimitMiddleware(app)

    await middleware(
        scope,
        receive,
        send,
    )

    status_code = next(
        message["status"]
        for message in sent_messages
        if message["type"] == "http.response.start"
    )

    body = b"".join(
        message.get("body", b"")
        for message in sent_messages
        if message["type"] == "http.response.body"
    )

    return status_code, body, app_called


def test_declared_oversized_request_is_rejected_before_app() -> None:
    status_code, body, app_called = asyncio.run(
        _run_request(
            [
                (
                    b"content-length",
                    str(MAX_REQUEST_BODY_BYTES + 1).encode(),
                ),
            ],
            [],
        )
    )

    assert status_code == 413
    assert json.loads(body) == {
        "detail": "Request too large",
    }
    assert app_called is False


def test_streamed_oversized_request_returns_413() -> None:
    status_code, body, app_called = asyncio.run(
        _run_request(
            [],
            [
                {
                    "type": "http.request",
                    "body": b"a" * MAX_REQUEST_BODY_BYTES,
                    "more_body": True,
                },
                {
                    "type": "http.request",
                    "body": b"b",
                    "more_body": False,
                },
            ],
        )
    )

    assert status_code == 413
    assert json.loads(body) == {
        "detail": "Request too large",
    }
    assert app_called is True


def test_streamed_request_at_exact_limit_is_allowed() -> None:
    status_code, body, app_called = asyncio.run(
        _run_request(
            [],
            [
                {
                    "type": "http.request",
                    "body": b"a" * MAX_REQUEST_BODY_BYTES,
                    "more_body": False,
                },
            ],
        )
    )

    assert status_code == 200
    assert body == b"ok"
    assert app_called is True


def test_invalid_content_length_returns_400() -> None:
    status_code, body, app_called = asyncio.run(
        _run_request(
            [
                (
                    b"content-length",
                    b"not-a-number",
                ),
            ],
            [],
        )
    )

    assert status_code == 400
    assert json.loads(body) == {
        "detail": "Invalid request",
    }
    assert app_called is False


def test_conflicting_content_lengths_return_400() -> None:
    status_code, body, app_called = asyncio.run(
        _run_request(
            [
                (b"content-length", b"10"),
                (b"content-length", b"20"),
            ],
            [],
        )
    )

    assert status_code == 400
    assert json.loads(body) == {
        "detail": "Invalid request",
    }
    assert app_called is False
