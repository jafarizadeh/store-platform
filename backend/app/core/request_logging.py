import logging
import time
import uuid

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("bynet.request")


class RequestLoggingMiddleware:
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

        request_id = uuid.uuid4().hex

        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id

        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")

        started_at = time.perf_counter()
        status_code = 500

        async def send_wrapper(
            message: Message,
        ) -> None:
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = message["status"]

                headers = MutableHeaders(
                    scope=message,
                )
                headers["X-Request-ID"] = request_id

            await send(message)

        try:
            await self.app(
                scope,
                receive,
                send_wrapper,
            )

        except Exception as exc:
            duration_ms = round(
                (time.perf_counter() - started_at) * 1000,
                2,
            )

            logger.error(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status_code": 500,
                    "duration_ms": duration_ms,
                    "exception_type": type(exc).__name__,
                },
            )

            raise

        duration_ms = round(
            (time.perf_counter() - started_at) * 1000,
            2,
        )

        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )
