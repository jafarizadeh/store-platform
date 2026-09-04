from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import Engine, delete
from sqlalchemy.orm import Session

from app.models.order_number_sequence import (
    OrderDailySequence,
)
from app.repositories.order_repository import (
    next_order_number,
)


def test_order_numbers_are_unique_under_concurrency(
    test_engine: Engine,
) -> None:
    worker_count = 8
    start_barrier = Barrier(worker_count)

    def allocate_from_worker() -> str:
        with Session(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        ) as db:
            start_barrier.wait(timeout=10)

            order_number = next_order_number(db)

            db.commit()

            return order_number

    try:
        with ThreadPoolExecutor(
            max_workers=worker_count,
        ) as executor:
            futures = [
                executor.submit(allocate_from_worker) for _ in range(worker_count)
            ]

            order_numbers = [future.result(timeout=15) for future in futures]

        assert len(order_numbers) == worker_count
        assert len(set(order_numbers)) == worker_count

        prefixes = {order_number.rsplit("-", 1)[0] for order_number in order_numbers}

        assert len(prefixes) == 1

        counters = sorted(
            int(order_number.rsplit("-", 1)[1]) for order_number in order_numbers
        )

        assert counters == list(
            range(
                counters[0],
                counters[0] + worker_count,
            )
        )

        for order_number in order_numbers:
            assert order_number.startswith("BN-")
            assert len(order_number) == 14

    finally:
        with Session(
            bind=test_engine,
            autoflush=False,
        ) as cleanup_db:
            cleanup_db.execute(delete(OrderDailySequence))
            cleanup_db.commit()


def test_order_number_rollback_does_not_consume_counter(
    test_engine: Engine,
) -> None:
    try:
        with Session(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        ) as db:
            first = next_order_number(db)

            db.rollback()

        with Session(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        ) as db:
            second = next_order_number(db)

            db.commit()

        assert first == second
        assert first.endswith("-0001")

    finally:
        with Session(
            bind=test_engine,
            autoflush=False,
        ) as cleanup_db:
            cleanup_db.execute(delete(OrderDailySequence))
            cleanup_db.commit()
