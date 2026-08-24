from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from factories.catalog import create_product_offer
from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import Session

from app.core.auth_security import hash_password
from app.domain.order_event import OrderEventType
from app.domain.payment import PaymentAttemptStatus
from app.domain.payment_errors import (
    PaymentProviderResultConflictError,
)
from app.models.order import Order, OrderEvent
from app.models.payment import Payment, PaymentAttempt
from app.models.product import Product
from app.models.product_offer import ProductOffer
from app.models.user import User
from app.payments.orchestrator import refresh_payment_status
from app.payments.provider import (
    PaymentStatusRequest,
    PaymentStatusResult,
)
from app.schemas.order import (
    OrderCreate,
    OrderItemCreate,
)
from app.services.order_service import create_pending_order
from app.services.payment_service import (
    prepare_payment,
    prepare_payment_attempt,
)

TEST_CREDENTIAL_HASH = hash_password("payment-status-concurrency-test-credential")

PROVIDER_REFERENCE = "status-concurrency-reference"


def _setup_pending_attempt(
    test_engine: Engine,
) -> tuple:
    suffix = uuid4().hex

    with Session(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    ) as db:
        user = User(
            email=(f"payment-status-race-{suffix}@example.com"),
            password_hash=TEST_CREDENTIAL_HASH,
            is_active=True,
        )

        db.add(user)
        db.flush()

        product, offer = create_product_offer(
            db,
            slug=(f"payment-status-race-{suffix}"),
            price_cents=2600,
            stock_quantity=5,
        )

        db.commit()

        order = create_pending_order(
            db,
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
            db,
            order_id=order.id,
            user_id=user.id,
        )

        attempt = prepare_payment_attempt(
            db,
            payment_id=payment.id,
            user_id=user.id,
            provider="fake",
            idempotency_key=(f"attempt-{uuid4().hex}"),
        )

        attempt.status = PaymentAttemptStatus.PENDING.value
        attempt.provider_reference = PROVIDER_REFERENCE

        db.commit()

        return (
            user.id,
            product.id,
            offer.id,
            order.id,
            payment.id,
            attempt.id,
        )


def _cleanup(
    test_engine: Engine,
    *,
    user_id,
    product_id,
    offer_id,
    order_id,
    payment_id,
) -> None:
    with Session(
        bind=test_engine,
        autoflush=False,
    ) as db:
        db.execute(
            delete(PaymentAttempt).where(PaymentAttempt.payment_id == payment_id)
        )

        db.execute(delete(Payment).where(Payment.id == payment_id))

        db.execute(delete(OrderEvent).where(OrderEvent.order_id == order_id))

        db.execute(delete(Order).where(Order.id == order_id))

        db.execute(delete(ProductOffer).where(ProductOffer.id == offer_id))

        db.execute(delete(Product).where(Product.id == product_id))

        db.execute(delete(User).where(User.id == user_id))

        db.commit()


class BarrierStatusProvider:
    name = "fake"

    def __init__(
        self,
        *,
        db: Session,
        barrier: Barrier,
        result: PaymentStatusResult,
    ) -> None:
        self.db = db
        self.barrier = barrier
        self.result = result

    def get_payment_status(
        self,
        request: PaymentStatusRequest,
    ) -> PaymentStatusResult:
        # Both workers must reach provider I/O
        # with no database transaction active.
        assert not self.db.in_transaction()

        self.barrier.wait(timeout=10)

        return self.result


def test_concurrent_exact_terminal_replay_is_idempotent(
    test_engine: Engine,
) -> None:
    (
        user_id,
        product_id,
        offer_id,
        order_id,
        payment_id,
        attempt_id,
    ) = _setup_pending_attempt(test_engine)

    barrier = Barrier(2)

    result = PaymentStatusResult(
        status=PaymentAttemptStatus.SUCCEEDED,
        provider_reference=PROVIDER_REFERENCE,
    )

    try:

        def worker():
            with Session(
                bind=test_engine,
                autoflush=False,
                expire_on_commit=False,
            ) as worker_db:
                provider = BarrierStatusProvider(
                    db=worker_db,
                    barrier=barrier,
                    result=result,
                )

                return refresh_payment_status(
                    worker_db,
                    attempt_id=attempt_id,
                    provider=provider,
                )

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(worker) for _ in range(2)]

            outcomes = [future.result(timeout=15) for future in futures]

        assert all(
            outcome.status == PaymentAttemptStatus.SUCCEEDED for outcome in outcomes
        )

        with Session(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        ) as verify_db:
            order = verify_db.get(
                Order,
                order_id,
            )

            payment = verify_db.get(
                Payment,
                payment_id,
            )

            attempt = verify_db.get(
                PaymentAttempt,
                attempt_id,
            )

            events = list(
                verify_db.scalars(
                    select(OrderEvent)
                    .where(OrderEvent.order_id == order_id)
                    .order_by(OrderEvent.id)
                ).all()
            )

            paid_events = [
                event
                for event in events
                if (
                    event.event_type == OrderEventType.ORDER_STATUS_CHANGED
                    and event.event_data
                    and event.event_data.get("to_status") == "paid"
                )
            ]

            stock_quantity = verify_db.scalar(
                select(ProductOffer.stock_quantity).where(ProductOffer.id == offer_id)
            )

            assert order is not None
            assert payment is not None
            assert attempt is not None

            assert order.status == "paid"
            assert payment.status == "succeeded"
            assert attempt.status == "succeeded"

            # Concurrent exact replay must never
            # produce a duplicate paid event.
            assert len(paid_events) == 1

            # Checkout reserved exactly one unit.
            assert stock_quantity == 4

    finally:
        _cleanup(
            test_engine,
            user_id=user_id,
            product_id=product_id,
            offer_id=offer_id,
            order_id=order_id,
            payment_id=payment_id,
        )


def test_concurrent_conflicting_terminal_results_first_commit_wins(
    test_engine: Engine,
) -> None:
    (
        user_id,
        product_id,
        offer_id,
        order_id,
        payment_id,
        attempt_id,
    ) = _setup_pending_attempt(test_engine)

    barrier = Barrier(2)

    success_result = PaymentStatusResult(
        status=PaymentAttemptStatus.SUCCEEDED,
        provider_reference=PROVIDER_REFERENCE,
    )

    failed_result = PaymentStatusResult(
        status=PaymentAttemptStatus.FAILED,
        provider_reference=PROVIDER_REFERENCE,
        failure_code="provider_declined",
    )

    try:

        def worker(
            result: PaymentStatusResult,
        ) -> tuple[str, PaymentAttemptStatus]:
            with Session(
                bind=test_engine,
                autoflush=False,
                expire_on_commit=False,
            ) as worker_db:
                provider = BarrierStatusProvider(
                    db=worker_db,
                    barrier=barrier,
                    result=result,
                )

                try:
                    outcome = refresh_payment_status(
                        worker_db,
                        attempt_id=attempt_id,
                        provider=provider,
                    )

                except PaymentProviderResultConflictError:
                    return (
                        "conflict",
                        result.status,
                    )

                return (
                    "committed",
                    outcome.status,
                )

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(
                    worker,
                    success_result,
                ),
                executor.submit(
                    worker,
                    failed_result,
                ),
            ]

            results = [future.result(timeout=15) for future in futures]

        committed = [status for outcome, status in results if outcome == "committed"]

        conflicts = [status for outcome, status in results if outcome == "conflict"]

        assert len(committed) == 1
        assert len(conflicts) == 1

        winner = committed[0]

        with Session(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        ) as verify_db:
            order = verify_db.get(
                Order,
                order_id,
            )

            payment = verify_db.get(
                Payment,
                payment_id,
            )

            attempt = verify_db.get(
                PaymentAttempt,
                attempt_id,
            )

            events = list(
                verify_db.scalars(
                    select(OrderEvent)
                    .where(OrderEvent.order_id == order_id)
                    .order_by(OrderEvent.id)
                ).all()
            )

            paid_events = [
                event
                for event in events
                if (
                    event.event_type == OrderEventType.ORDER_STATUS_CHANGED
                    and event.event_data
                    and event.event_data.get("to_status") == "paid"
                )
            ]

            stock_quantity = verify_db.scalar(
                select(ProductOffer.stock_quantity).where(ProductOffer.id == offer_id)
            )

            assert order is not None
            assert payment is not None
            assert attempt is not None

            assert attempt.status == winner.value

            if winner == PaymentAttemptStatus.SUCCEEDED:
                assert order.status == "paid"
                assert payment.status == "succeeded"
                assert len(paid_events) == 1

            else:
                assert winner == PaymentAttemptStatus.FAILED
                assert order.status == "pending"
                assert payment.status == "pending"
                assert len(paid_events) == 0
                assert attempt.failure_code == "provider_declined"

            # Neither reconciliation path may
            # alter inventory directly.
            assert stock_quantity == 4

    finally:
        _cleanup(
            test_engine,
            user_id=user_id,
            product_id=product_id,
            offer_id=offer_id,
            order_id=order_id,
            payment_id=payment_id,
        )
