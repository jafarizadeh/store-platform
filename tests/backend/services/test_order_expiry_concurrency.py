from concurrent.futures import (
    ThreadPoolExecutor,
)
from datetime import (
    UTC,
    datetime,
    timedelta,
)
from threading import Barrier
from uuid import uuid4

from factories.catalog import (
    create_product_offer,
)
from sqlalchemy import (
    Engine,
    delete,
    select,
)
from sqlalchemy.orm import Session

from app.core.auth_security import (
    hash_password,
)
from app.models.order import (
    Order,
    OrderEvent,
)
from app.models.product import Product
from app.models.product_offer import (
    ProductOffer,
)
from app.models.user import User
from app.schemas.order import (
    OrderCreate,
    OrderItemCreate,
)
from app.services.order_service import (
    create_pending_order,
    expire_due_pending_orders,
)

TEST_CREDENTIAL_HASH = hash_password("expiry-concurrency-test-credential")


def test_concurrent_expiry_workers_release_inventory_once(
    test_engine: Engine,
) -> None:
    suffix = uuid4().hex

    user_id = None
    product_id = None
    offer_id = None
    order_id = None

    try:
        current_time = datetime.now(UTC)

        with Session(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        ) as setup_db:
            user = User(
                email=(f"expiry-race-{suffix}@example.com"),
                password_hash=(TEST_CREDENTIAL_HASH),
                is_active=True,
            )

            setup_db.add(user)
            setup_db.flush()

            product, offer = create_product_offer(
                setup_db,
                slug=(f"expiry-race-{suffix}"),
                price_cents=1200,
                stock_quantity=1,
            )

            setup_db.commit()

            order = create_pending_order(
                setup_db,
                OrderCreate(
                    items=[
                        OrderItemCreate(
                            offer_id=offer.id,
                            quantity=1,
                        )
                    ]
                ),
                user_id=user.id,
                idempotency_key=(f"expiry-race-{uuid4().hex}"),
            )

            order.reservation_expires_at = current_time - timedelta(seconds=1)

            setup_db.commit()

            user_id = user.id
            product_id = product.id
            offer_id = offer.id
            order_id = order.id

        if user_id is None or offer_id is None or order_id is None:
            raise RuntimeError("Concurrency setup failed.")

        barrier = Barrier(2)

        def expire_from_worker() -> int:
            with Session(
                bind=test_engine,
                autoflush=False,
                expire_on_commit=False,
            ) as worker_db:
                barrier.wait(timeout=10)

                return expire_due_pending_orders(
                    worker_db,
                    current_time=current_time,
                    batch_size=10,
                )

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(expire_from_worker) for _ in range(2)]

            results = sorted(future.result(timeout=15) for future in futures)

        assert results == [0, 1]

        with Session(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        ) as verify_db:
            stock_quantity = verify_db.scalar(
                select(ProductOffer.stock_quantity).where(ProductOffer.id == offer_id)
            )

            status = verify_db.scalar(select(Order.status).where(Order.id == order_id))

            event_types = list(
                verify_db.scalars(
                    select(OrderEvent.event_type)
                    .where(OrderEvent.order_id == order_id)
                    .order_by(OrderEvent.id)
                ).all()
            )

            assert stock_quantity == 1
            assert status == "expired"

            assert event_types == [
                "order_created",
                "inventory_reserved",
                "order_status_changed",
                "inventory_released",
            ]

    finally:
        if user_id is not None:
            with Session(
                bind=test_engine,
                autoflush=False,
            ) as cleanup_db:
                if order_id is not None:
                    cleanup_db.execute(
                        delete(OrderEvent).where(OrderEvent.order_id == order_id)
                    )

                    cleanup_db.execute(delete(Order).where(Order.id == order_id))

                if offer_id is not None:
                    cleanup_db.execute(
                        delete(ProductOffer).where(ProductOffer.id == offer_id)
                    )

                if product_id is not None:
                    cleanup_db.execute(delete(Product).where(Product.id == product_id))

                cleanup_db.execute(delete(User).where(User.id == user_id))

                cleanup_db.commit()
