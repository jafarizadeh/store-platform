from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from factories.catalog import create_product_offer
from sqlalchemy import Engine, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth_security import hash_password
from app.domain.payment_errors import (
    PaymentAttemptAlreadyActiveError,
)
from app.models.order import Order, OrderEvent
from app.models.payment import Payment, PaymentAttempt
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
from app.services.payment_service import (
    prepare_payment,
    prepare_payment_attempt,
)

TEST_CREDENTIAL_HASH = hash_password("payment-concurrency-test-credential")


def test_payment_creation_and_attempt_are_safe_under_concurrency(
    test_engine: Engine,
) -> None:
    suffix = uuid4().hex

    user_id = None
    product_id = None
    offer_id = None
    order_id = None
    payment_id = None

    try:
        with Session(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        ) as setup_db:
            user = User(
                email=(f"payment-race-{suffix}@example.com"),
                password_hash=(TEST_CREDENTIAL_HASH),
                is_active=True,
            )

            setup_db.add(user)
            setup_db.flush()

            product, offer = create_product_offer(
                setup_db,
                slug=(f"payment-race-{suffix}"),
                price_cents=1900,
                stock_quantity=5,
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
                idempotency_key=(f"order-{uuid4().hex}"),
            )

            user_id = user.id
            product_id = product.id
            offer_id = offer.id
            order_id = order.id

        if user_id is None or order_id is None:
            raise RuntimeError("Payment concurrency setup failed.")

        payment_barrier = Barrier(2)

        def prepare_payment_worker() -> str:
            with Session(
                bind=test_engine,
                autoflush=False,
                expire_on_commit=False,
            ) as worker_db:
                payment_barrier.wait(timeout=10)

                payment = prepare_payment(
                    worker_db,
                    order_id=order_id,
                    user_id=user_id,
                )

                return str(payment.id)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(prepare_payment_worker) for _ in range(2)]

            payment_ids = [future.result(timeout=15) for future in futures]

        assert payment_ids[0] == payment_ids[1]

        with Session(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        ) as verify_db:
            stored_payment_ids = list(
                verify_db.scalars(
                    select(Payment.id).where(Payment.order_id == order_id)
                ).all()
            )

            assert len(stored_payment_ids) == 1

            payment_id = stored_payment_ids[0]

        attempt_key = f"attempt-{uuid4().hex}"

        attempt_barrier = Barrier(2)

        def prepare_attempt_worker() -> str:
            if payment_id is None:
                raise RuntimeError("Payment ID missing.")

            with Session(
                bind=test_engine,
                autoflush=False,
                expire_on_commit=False,
            ) as worker_db:
                attempt_barrier.wait(timeout=10)

                attempt = prepare_payment_attempt(
                    worker_db,
                    payment_id=payment_id,
                    user_id=user_id,
                    provider="paypal",
                    idempotency_key=(attempt_key),
                )

                return str(attempt.id)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(prepare_attempt_worker) for _ in range(2)]

            attempt_ids = [future.result(timeout=15) for future in futures]

        assert attempt_ids[0] == attempt_ids[1]

        with Session(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        ) as verify_db:
            payment_count = verify_db.scalar(
                select(func.count())
                .select_from(Payment)
                .where(Payment.order_id == order_id)
            )

            attempt_count = verify_db.scalar(
                select(func.count())
                .select_from(PaymentAttempt)
                .where(
                    PaymentAttempt.payment_id == payment_id,
                    PaymentAttempt.idempotency_key == attempt_key,
                )
            )

            assert payment_count == 1
            assert attempt_count == 1

    finally:
        if user_id is not None:
            with Session(
                bind=test_engine,
                autoflush=False,
            ) as cleanup_db:
                if payment_id is not None:
                    cleanup_db.execute(
                        delete(PaymentAttempt).where(
                            PaymentAttempt.payment_id == payment_id
                        )
                    )

                    cleanup_db.execute(delete(Payment).where(Payment.id == payment_id))

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


def test_different_attempt_keys_allow_only_one_unresolved_attempt(
    test_engine: Engine,
) -> None:
    suffix = uuid4().hex

    user_id = None
    product_id = None
    offer_id = None
    order_id = None
    payment_id = None

    try:
        with Session(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        ) as setup_db:
            user = User(
                email=(f"payment-active-race-{suffix}@example.com"),
                password_hash=TEST_CREDENTIAL_HASH,
                is_active=True,
            )

            setup_db.add(user)
            setup_db.flush()

            product, offer = create_product_offer(
                setup_db,
                slug=(f"payment-active-race-{suffix}"),
                price_cents=2100,
                stock_quantity=5,
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
                idempotency_key=(f"order-{uuid4().hex}"),
            )

            payment = prepare_payment(
                setup_db,
                order_id=order.id,
                user_id=user.id,
            )

            user_id = user.id
            product_id = product.id
            offer_id = offer.id
            order_id = order.id
            payment_id = payment.id

        if user_id is None or payment_id is None:
            raise RuntimeError("Active-attempt concurrency setup failed.")

        attempt_barrier = Barrier(2)

        keys = [
            f"attempt-a-{uuid4().hex}",
            f"attempt-b-{uuid4().hex}",
        ]

        def prepare_attempt_worker(
            key: str,
        ) -> tuple[str, str]:
            with Session(
                bind=test_engine,
                autoflush=False,
                expire_on_commit=False,
            ) as worker_db:
                attempt_barrier.wait(timeout=10)

                try:
                    attempt = prepare_payment_attempt(
                        worker_db,
                        payment_id=payment_id,
                        user_id=user_id,
                        provider="paypal",
                        idempotency_key=key,
                    )

                except PaymentAttemptAlreadyActiveError as exc:
                    return (
                        "blocked",
                        str(exc.attempt_id),
                    )

                return (
                    "created",
                    str(attempt.id),
                )

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(
                    prepare_attempt_worker,
                    key,
                )
                for key in keys
            ]

            results = [future.result(timeout=15) for future in futures]

        created = [value for status, value in results if status == "created"]

        blocked = [value for status, value in results if status == "blocked"]

        assert len(created) == 1
        assert len(blocked) == 1

        # The rejected worker must point to the
        # exact attempt created by the winner.
        assert blocked[0] == created[0]

        with Session(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        ) as verify_db:
            attempts = list(
                verify_db.scalars(
                    select(PaymentAttempt).where(
                        PaymentAttempt.payment_id == payment_id
                    )
                ).all()
            )

            unresolved_count = verify_db.scalar(
                select(func.count())
                .select_from(PaymentAttempt)
                .where(
                    PaymentAttempt.payment_id == payment_id,
                    PaymentAttempt.status.in_(
                        (
                            "created",
                            "pending",
                        )
                    ),
                )
            )

            assert len(attempts) == 1
            assert unresolved_count == 1

            assert str(attempts[0].id) == created[0]

            assert attempts[0].idempotency_key in keys

    finally:
        if user_id is not None:
            with Session(
                bind=test_engine,
                autoflush=False,
            ) as cleanup_db:
                if payment_id is not None:
                    cleanup_db.execute(
                        delete(PaymentAttempt).where(
                            PaymentAttempt.payment_id == payment_id
                        )
                    )

                    cleanup_db.execute(delete(Payment).where(Payment.id == payment_id))

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


def test_database_rejects_second_unresolved_attempt(
    test_engine: Engine,
) -> None:
    suffix = uuid4().hex

    user_id = None
    product_id = None
    offer_id = None
    order_id = None
    payment_id = None

    try:
        with Session(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        ) as setup_db:
            user = User(
                email=(f"payment-db-guard-{suffix}@example.com"),
                password_hash=TEST_CREDENTIAL_HASH,
                is_active=True,
            )

            setup_db.add(user)
            setup_db.flush()

            product, offer = create_product_offer(
                setup_db,
                slug=(f"payment-db-guard-{suffix}"),
                price_cents=2200,
                stock_quantity=5,
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
                idempotency_key=(f"order-{uuid4().hex}"),
            )

            payment = prepare_payment(
                setup_db,
                order_id=order.id,
                user_id=user.id,
            )

            user_id = user.id
            product_id = product.id
            offer_id = offer.id
            order_id = order.id
            payment_id = payment.id

        if payment_id is None:
            raise RuntimeError("Database guard setup failed.")

        # Deliberately bypass
        # prepare_payment_attempt().
        # This test proves the database itself
        # enforces the invariant.
        with Session(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        ) as direct_db:
            first = PaymentAttempt(
                payment_id=payment_id,
                idempotency_key=(f"direct-a-{uuid4().hex}"),
                provider="paypal",
                status="created",
            )

            direct_db.add(first)
            direct_db.commit()

            second = PaymentAttempt(
                payment_id=payment_id,
                idempotency_key=(f"direct-b-{uuid4().hex}"),
                provider="paypal",
                status="pending",
            )

            direct_db.add(second)

            with pytest.raises(IntegrityError) as error:
                direct_db.commit()

            constraint_name = getattr(
                getattr(
                    error.value.orig,
                    "diag",
                    None,
                ),
                "constraint_name",
                None,
            )

            assert constraint_name == ("uq_payment_attempts_one_unresolved_per_payment")

            direct_db.rollback()

        with Session(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        ) as verify_db:
            unresolved_count = verify_db.scalar(
                select(func.count())
                .select_from(PaymentAttempt)
                .where(
                    PaymentAttempt.payment_id == payment_id,
                    PaymentAttempt.status.in_(
                        (
                            "created",
                            "pending",
                        )
                    ),
                )
            )

            assert unresolved_count == 1

    finally:
        if user_id is not None:
            with Session(
                bind=test_engine,
                autoflush=False,
            ) as cleanup_db:
                if payment_id is not None:
                    cleanup_db.execute(
                        delete(PaymentAttempt).where(
                            PaymentAttempt.payment_id == payment_id
                        )
                    )

                    cleanup_db.execute(delete(Payment).where(Payment.id == payment_id))

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
