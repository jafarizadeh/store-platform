from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.orders import router as orders_router
from app.api.v1.payments import router as payments_router
from app.api.v1.products import router as products_router
from app.api.v1.webhooks import router as webhooks_router

router = APIRouter(
    prefix="/api/v1",
)

router.include_router(products_router)

router.include_router(orders_router)

router.include_router(payments_router)

router.include_router(webhooks_router)

router.include_router(auth_router)
