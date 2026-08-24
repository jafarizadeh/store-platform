from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

from factories.catalog import create_product_offer
from sqlalchemy import Engine, delete, func, select
from sqlalchemy.orm import Session

from app.core.auth_security import hash_password
from app.domain.order_errors import (
    InsufficientStockError,
)
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

TEST_CREDENTIAL_HASH = hash_password("inventory-concurrency-test-credential")


def test_two_users_cannot_oversell_last_item(
    test_engine: Engine,
) -> None:
    suffix = uuid4().hex

    user_ids: list[UUID] = []
    product_id = None
    offer_id = None

    try:
        with Session(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        ) as setup_db:
            first_user = User(
                email=(f"inventory-race-first-{suffix}@example.com"),
                password_hash=(TEST_CREDENTIAL_HASH),
                is_active=True,
            )

            second_user = User(
                email=(f"inventory-race-second-{suffix}@example.com"),
                password_hash=(TEST_CREDENTIAL_HASH),
                is_active=True,
            )

            setup_db.add_all(
                [
                    first_user,
                    second_user,
                ]
            )
            setup_db.flush()

            product, offer = create_product_offer(
                setup_db,
                slug=(f"inventory-race-{suffix}"),
                price_cents=1200,
                stock_quantity=1,
            )

            setup_db.commit()

            user_ids = [
                first_user.id,
                second_user.id,
            ]
            product_id = product.id
            offer_id = offer.id

        if len(user_ids) != 2 or offer_id is None:
            raise RuntimeError("Concurrency test setup failed.")

        start_barrier = Barrier(2)

        def create_from_worker(
            user_id: UUID,
        ) -> tuple[str, str | int]:
            with Session(
                bind=test_engine,
                autoflush=False,
                expire_on_commit=False,
            ) as worker_db:
                start_barrier.wait(timeout=10)

                try:
                    order = create_pending_order(
                        worker_db,
                        OrderCreate(
                            items=[
                                OrderItemCreate(
                                    offer_id=(offer_id),
                                    quantity=1,
                                )
                            ]
                        ),
                        user_id=user_id,
                        idempotency_key=(f"inventory-race-{uuid4().hex}"),
                    )
                except InsufficientStockError as exc:
                    return (
                        "insufficient",
                        exc.available_quantity,
                    )

                return (
                    "created",
                    str(order.id),
                )

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(
                    create_from_worker,
                    user_id,
                )
                for user_id in user_ids
            ]

            results = [future.result(timeout=15) for future in futures]

        statuses = sorted(result[0] for result in results)

        assert statuses == [
            "created",
            "insufficient",
        ]

        insufficient_results = [
            result for result in results if result[0] == "insufficient"
        ]

        assert insufficient_results == [
            (
                "insufficient",
                0,
            )
        ]

        with Session(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        ) as verify_db:
            stock_quantity = verify_db.scalar(
                select(ProductOffer.stock_quantity).where(ProductOffer.id == offer_id)
            )

            order_count = verify_db.scalar(
                select(func.count())
                .select_from(Order)
                .where(Order.user_id.in_(user_ids))
            )

            event_count = verify_db.scalar(
                select(func.count())
                .select_from(OrderEvent)
                .join(
                    Order,
                    Order.id == OrderEvent.order_id,
                )
                .where(Order.user_id.in_(user_ids))
            )

            assert stock_quantity == 0
            assert order_count == 1

            # The one successful order gets
            # order_created + inventory_reserved.
            assert event_count == 2

    finally:
        if user_ids:
            with Session(
                bind=test_engine,
                autoflush=False,
            ) as cleanup_db:
                order_ids = select(Order.id).where(Order.user_id.in_(user_ids))

                cleanup_db.execute(
                    delete(OrderEvent).where(OrderEvent.order_id.in_(order_ids))
                )

                cleanup_db.execute(delete(Order).where(Order.user_id.in_(user_ids)))

                if offer_id is not None:
                    cleanup_db.execute(
                        delete(ProductOffer).where(ProductOffer.id == offer_id)
                    )

                if product_id is not None:
                    cleanup_db.execute(delete(Product).where(Product.id == product_id))

                cleanup_db.execute(delete(User).where(User.id.in_(user_ids)))

                cleanup_db.commit()
