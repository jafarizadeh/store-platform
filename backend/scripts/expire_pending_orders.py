from app.db.session import SessionLocal
from app.services.order_service import (
    expire_due_pending_orders,
)

BATCH_SIZE = 100


def main() -> None:
    total_expired = 0

    with SessionLocal() as db:
        while True:
            expired_count = expire_due_pending_orders(
                db,
                batch_size=BATCH_SIZE,
            )

            total_expired += expired_count

            if expired_count < BATCH_SIZE:
                break

    print(f"Expired pending orders: {total_expired}")


if __name__ == "__main__":
    main()
