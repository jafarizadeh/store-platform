from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from uuid import uuid4

from factories.catalog import create_product_offer
from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import Session

from app.core.auth_security import hash_password
from app.domain.payment import PaymentAttemptStatus
from app.models.order import Order, OrderEvent
from app.models.payment import Payment, PaymentAttempt
from app.models.product import Product
from app.models.product_offer import ProductOffer
from app.models.user import User
from app.payments.orchestrator import initiate_payment
from app.payments.provider import (
    PaymentInitiationRequest,
    PaymentInitiationResult,
)
from app.schemas.order import (
    OrderCreate,
    OrderItemCreate,
)
from app.services.order_service import (
    create_pending_order,
    expire_due_pending_orders,
)
from app.services.payment_service import prepare_payment

TEST_CREDENTIAL_HASH = hash_password("payment-expiry-race-test-credential")


class BlockingSuccessProvider:
    name = "fake-race"

    def __init__(
        self,
        *,
        started: Event,
        release: Event,
    ) -> None:
        self.started = started
        self.release = release
        self.request: PaymentInitiationRequest | None = None
        self.external_success = False

    def initiate_payment(
        self,
        request: PaymentInitiationRequest,
    ) -> PaymentInitiationResult:
        self.request = request
        self.started.set()

        if not self.release.wait(timeout=10):
            raise RuntimeError("Provider test release timed out.")

        self.external_success = True

        return PaymentInitiationResult(
            status=PaymentAttemptStatus.SUCCEEDED,
            provider_reference=(f"race-success-{request.attempt_id}"),
        )


def test_inflight_payment_blocks_reservation_expiry(
    test_engine: Engine,
) -> None:
    suffix = uuid4().hex

    user_id = None
    product_id = None
    offer_id = None
    order_id = None
    payment_id = None

    started = Event()
    release = Event()

    provider = BlockingSuccessProvider(
        started=started,
        release=release,
    )

    try:
        with Session(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        ) as setup_db:
            user = User(
                email=(f"payment-expiry-race-{suffix}@example.com"),
                password_hash=TEST_CREDENTIAL_HASH,
                is_active=True,
            )

            setup_db.add(user)
            setup_db.flush()

            product, offer = create_product_offer(
                setup_db,
                slug=(f"payment-expiry-race-{suffix}"),
                price_cents=3100,
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

            reservation_deadline = order.reservation_expires_at

        if user_id is None or order_id is None or payment_id is None:
            raise RuntimeError("Payment expiry race setup failed.")

        def payment_worker():
            with Session(
                bind=test_engine,
                autoflush=False,
                expire_on_commit=False,
            ) as worker_db:
                return initiate_payment(
                    worker_db,
                    payment_id=payment_id,
                    user_id=user_id,
                    provider=provider,
                    idempotency_key=(f"attempt-{uuid4().hex}"),
                )

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(payment_worker)

            if not started.wait(timeout=10):
                raise RuntimeError("Provider call did not start.")

            # Simulate reservation time passing while
            # the external provider call is still in flight.
            expiry_time = reservation_deadline + timedelta(seconds=1)

            with Session(
                bind=test_engine,
                autoflush=False,
                expire_on_commit=False,
            ) as expiry_db:
                expired_count = expire_due_pending_orders(
                    expiry_db,
                    current_time=expiry_time,
                )

            # Provider has now already accepted the
            # external payment and returns success.
            release.set()

            payment_outcome = None
            payment_error = None

            try:
                payment_outcome = future.result(timeout=15)
            except Exception as exc:
                payment_error = exc

        # Required invariant:
        #
        # An in-flight payment initiation must prevent
        # reservation expiry from releasing inventory.
        assert expired_count == 0

        assert payment_error is None
        assert payment_outcome is not None

        assert payment_outcome.status == PaymentAttemptStatus.SUCCEEDED

        assert provider.external_success

        with Session(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        ) as verify_db:
            order_status = verify_db.scalar(
                select(Order.status).where(Order.id == order_id)
            )

            payment_status = verify_db.scalar(
                select(Payment.status).where(Payment.id == payment_id)
            )

            stock_quantity = verify_db.scalar(
                select(ProductOffer.stock_quantity).where(ProductOffer.id == offer_id)
            )

            assert order_status == "paid"
            assert payment_status == "succeeded"
            assert stock_quantity == 0

    finally:
        release.set()

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


def test_expiry_wins_before_payment_and_provider_is_never_called(
    test_engine: Engine,
    monkeypatch,
) -> None:
    from datetime import UTC, datetime

    import pytest

    import app.services.order_service as order_service_module
    from app.domain.payment_errors import (
        PaymentOrderNotPayableError,
    )

    suffix = uuid4().hex

    user_id = None
    product_id = None
    offer_id = None
    order_id = None
    payment_id = None

    expiry_locked = Event()
    release_expiry = Event()

    class RecordingSuccessProvider:
        name = "fake-expiry-first"

        def __init__(self) -> None:
            self.calls: list[PaymentInitiationRequest] = []

        def initiate_payment(
            self,
            request: PaymentInitiationRequest,
        ) -> PaymentInitiationResult:
            self.calls.append(request)

            return PaymentInitiationResult(
                status=(PaymentAttemptStatus.SUCCEEDED),
                provider_reference=(f"should-not-run-{request.attempt_id}"),
            )

    provider = RecordingSuccessProvider()

    real_release_inventory = order_service_module.release_inventory

    def blocking_release_inventory(
        db: Session,
        quantities: dict[int, int],
    ) -> None:
        # expire_due_pending_orders has already
        # selected the Order FOR UPDATE before
        # reaching this function.
        expiry_locked.set()

        if not release_expiry.wait(timeout=10):
            raise RuntimeError("Expiry release barrier timed out.")

        real_release_inventory(
            db,
            quantities,
        )

    monkeypatch.setattr(
        order_service_module,
        "release_inventory",
        blocking_release_inventory,
    )

    try:
        with Session(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        ) as setup_db:
            user = User(
                email=(f"payment-expiry-first-{suffix}@example.com"),
                password_hash=TEST_CREDENTIAL_HASH,
                is_active=True,
            )

            setup_db.add(user)
            setup_db.flush()

            product, offer = create_product_offer(
                setup_db,
                slug=(f"payment-expiry-first-{suffix}"),
                price_cents=3300,
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
                idempotency_key=(f"order-{uuid4().hex}"),
            )

            payment = prepare_payment(
                setup_db,
                order_id=order.id,
                user_id=user.id,
            )

            current_time = datetime.now(UTC)

            order.reservation_expires_at = current_time - timedelta(seconds=1)

            setup_db.commit()

            user_id = user.id
            product_id = product.id
            offer_id = offer.id
            order_id = order.id
            payment_id = payment.id

        if user_id is None or order_id is None or payment_id is None:
            raise RuntimeError("Expiry-first race setup failed.")

        def expiry_worker() -> int:
            with Session(
                bind=test_engine,
                autoflush=False,
                expire_on_commit=False,
            ) as worker_db:
                return expire_due_pending_orders(
                    worker_db,
                    current_time=current_time,
                )

        def payment_worker():
            with Session(
                bind=test_engine,
                autoflush=False,
                expire_on_commit=False,
            ) as worker_db:
                return initiate_payment(
                    worker_db,
                    payment_id=payment_id,
                    user_id=user_id,
                    provider=provider,
                    idempotency_key=(f"attempt-{uuid4().hex}"),
                )

        with ThreadPoolExecutor(max_workers=2) as executor:
            expiry_future = executor.submit(expiry_worker)

            if not expiry_locked.wait(timeout=10):
                raise RuntimeError("Expiry did not acquire the Order lock.")

            # Payment now starts while expiry owns
            # the Order row lock. It must wait.
            payment_future = executor.submit(payment_worker)

            # Allow expiry to release inventory,
            # mark the Order expired, and commit.
            release_expiry.set()

            expired_count = expiry_future.result(timeout=15)

            assert expired_count == 1

            with pytest.raises(PaymentOrderNotPayableError):
                payment_future.result(timeout=15)

        # Crucial external-side invariant:
        # once expiry won the Order lock,
        # absolutely no provider call may occur.
        assert provider.calls == []

        with Session(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        ) as verify_db:
            order_status = verify_db.scalar(
                select(Order.status).where(Order.id == order_id)
            )

            stock_quantity = verify_db.scalar(
                select(ProductOffer.stock_quantity).where(ProductOffer.id == offer_id)
            )

            attempts = list(
                verify_db.scalars(
                    select(PaymentAttempt).where(
                        PaymentAttempt.payment_id == payment_id
                    )
                ).all()
            )

            assert order_status == "expired"
            assert stock_quantity == 1

            # prepare_payment_attempt validates the
            # locked Order before creating an attempt.
            assert attempts == []

    finally:
        release_expiry.set()

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
