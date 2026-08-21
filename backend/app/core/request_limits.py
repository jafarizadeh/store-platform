from __future__ import annotations

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_REQUEST_BODY_BYTES = 1_048_576  # 1 MiB


class RequestTooLargeError(Exception):
    """Raised internally when a streamed request exceeds the body limit."""


class RequestSizeLimitMiddleware:
    def __init__(
        self,
        app: ASGIApp,
    ) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_lengths = [
            value
            for name, value in scope.get("headers", [])
            if name.lower() == b"content-length"
        ]

        if content_lengths:
            if len(set(content_lengths)) != 1:
                await self._send_invalid_request(
                    scope,
                    receive,
                    send,
                )
                return

            raw_content_length = content_lengths[0]

            try:
                decoded_content_length = raw_content_length.decode("ascii")
            except UnicodeDecodeError:
                await self._send_invalid_request(
                    scope,
                    receive,
                    send,
                )
                return

            if not decoded_content_length.isdigit():
                await self._send_invalid_request(
                    scope,
                    receive,
                    send,
                )
                return

            declared_size = int(decoded_content_length)

            if declared_size > MAX_REQUEST_BODY_BYTES:
                await self._send_request_too_large(
                    scope,
                    receive,
                    send,
                )
                return

        received_bytes = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received_bytes

            message = await receive()

            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))

                if received_bytes > MAX_REQUEST_BODY_BYTES:
                    raise RequestTooLargeError

            return message

        async def tracked_send(
            message: Message,
        ) -> None:
            nonlocal response_started

            if message["type"] == "http.response.start":
                response_started = True

            await send(message)

        try:
            await self.app(
                scope,
                limited_receive,
                tracked_send,
            )
        except RequestTooLargeError:
            if response_started:
                raise

            await self._send_request_too_large(
                scope,
                receive,
                send,
            )

    @staticmethod
    async def _send_invalid_request(
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        response = JSONResponse(
            status_code=400,
            content={
                "detail": "Invalid request",
            },
        )

        await response(
            scope,
            receive,
            send,
        )

    @staticmethod
    async def _send_request_too_large(
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        response = JSONResponse(
            status_code=413,
            content={
                "detail": "Request too large",
            },
        )

        await response(
            scope,
            receive,
            send,
        )
