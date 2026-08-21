from fastapi import FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.router import router as api_v1_router
from app.core.config import settings
from app.core.errors import unhandled_exception_handler
from app.core.logging import configure_logging
from app.core.request_limits import RequestSizeLimitMiddleware
from app.core.request_logging import RequestLoggingMiddleware
from app.core.security import SecurityHeadersMiddleware
from app.db.session import engine

development = settings.app_env == "development"

configure_logging()

app = FastAPI(
    title=settings.app_name,
    debug=False,
    docs_url="/docs" if development else None,
    redoc_url=None,
    openapi_url="/openapi.json" if development else None,
)

app.add_exception_handler(Exception, unhandled_exception_handler)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)

app.include_router(api_v1_router)


@app.get(
    "/health/live",
    include_in_schema=False,
)
def liveness():
    return {
        "status": "ok",
    }


@app.get(
    "/health/ready",
    include_in_schema=False,
)
def readiness():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

            products_table = connection.execute(
                text(
                    """
                    SELECT to_regclass('public.products')
                    """
                )
            ).scalar_one()

            orders_table = connection.execute(
                text(
                    """
                    SELECT to_regclass('public.orders')
                    """
                )
            ).scalar_one()

            order_items_table = connection.execute(
                text(
                    """
                    SELECT to_regclass('public.order_items')
                    """
                )
            ).scalar_one()

            if not all(
                [
                    products_table,
                    orders_table,
                    order_items_table,
                ]
            ):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Service unavailable",
                )

        return {
            "status": "ready",
        }

    except HTTPException:
        raise

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unavailable",
        ) from None
