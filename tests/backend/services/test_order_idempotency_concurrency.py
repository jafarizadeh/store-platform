from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from factories.catalog import create_product_offer
from sqlalchemy import Engine, delete, func, select
from sqlalchemy.orm import Session

from app.core.auth_security import hash_password
from app.models.order import Order, OrderEvent
from app.models.product import Product
from app.models.product_offer import ProductOffer
from app.models.user import User
from app.schemas.order import (
    OrderCreate,
    OrderItemCreate,
)
from app.services.order_service import (
    create_pending_order,
)

TEST_CREDENTIAL_HASH = hash_password(
    "concurrency-" + "order-idempotency-test-credential"
)


def test_same_idempotency_key_is_safe_under_concurrency(
    test_engine: Engine,
) -> None:
    suffix = uuid4().hex

    user_id = None
    product_id = None
    offer_id = None

    idempotency_key = f"concurrent-{uuid4().hex}"

    try:
        with Session(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        ) as setup_db:
            user = User(
                email=(f"concurrent-order-{suffix}@example.com"),
                password_hash=(TEST_CREDENTIAL_HASH),
                is_active=True,
            )

            setup_db.add(user)
            setup_db.flush()

            product, offer = create_product_offer(
                setup_db,
                slug=(f"concurrent-idempotency-{suffix}"),
                price_cents=1200,
                stock_quantity=5,
            )

            setup_db.commit()

            user_id = user.id
            product_id = product.id
            offer_id = offer.id

        if user_id is None or offer_id is None:
            raise RuntimeError("Concurrency test setup failed.")

        start_barrier = Barrier(2)

        def create_from_worker() -> str:
            with Session(
                bind=test_engine,
                autoflush=False,
                expire_on_commit=False,
            ) as worker_db:
                start_barrier.wait(timeout=10)

                order = create_pending_order(
                    worker_db,
                    OrderCreate(
                        items=[
                            OrderItemCreate(
                                offer_id=(offer_id),
                                quantity=2,
                            )
                        ]
                    ),
                    user_id=user_id,
                    idempotency_key=(idempotency_key),
                )

                return str(order.id)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(create_from_worker) for _ in range(2)]

            order_ids = [future.result(timeout=15) for future in futures]

        assert order_ids[0] == order_ids[1]

        with Session(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        ) as verify_db:
            stock_quantity = verify_db.scalar(
                select(ProductOffer.stock_quantity).where(ProductOffer.id == offer_id)
            )

            matching_order_count = verify_db.scalar(
                select(func.count())
                .select_from(Order)
                .where(
                    Order.user_id == user_id,
                    Order.idempotency_key == idempotency_key,
                )
            )

            assert stock_quantity == 3
            assert matching_order_count == 1

    finally:
        if user_id is not None:
            with Session(
                bind=test_engine,
                autoflush=False,
            ) as cleanup_db:
                cleanup_db.execute(
                    delete(OrderEvent).where(
                        OrderEvent.order_id.in_(
                            select(Order.id).where(Order.user_id == user_id)
                        )
                    )
                )

                cleanup_db.execute(delete(Order).where(Order.user_id == user_id))

                if offer_id is not None:
                    cleanup_db.execute(
                        delete(ProductOffer).where(ProductOffer.id == offer_id)
                    )

                if product_id is not None:
                    cleanup_db.execute(delete(Product).where(Product.id == product_id))

                cleanup_db.execute(delete(User).where(User.id == user_id))

                cleanup_db.commit()
