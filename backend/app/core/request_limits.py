from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

MAX_REQUEST_BODY_BYTES = 1_048_576  # 1 MiB


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

        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")

        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError:
                response = JSONResponse(
                    status_code=400,
                    content={
                        "detail": "Invalid request",
                    },
                )
                await response(scope, receive, send)
                return

            if declared_size > MAX_REQUEST_BODY_BYTES:
                response = JSONResponse(
                    status_code=413,
                    content={
                        "detail": "Request too large",
                    },
                )
                await response(scope, receive, send)
                return

        received = 0

        async def limited_receive():
            nonlocal received

            message = await receive()

            if message["type"] == "http.request":
                received += len(message.get("body", b""))

                if received > MAX_REQUEST_BODY_BYTES:
                    return {
                        "type": "http.disconnect",
                    }

            return message

        await self.app(
            scope,
            limited_receive,
            send,
        )
