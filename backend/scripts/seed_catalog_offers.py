from __future__ import annotations

import argparse
from pathlib import Path

from app.catalog.offer_csv import (
    OfferCsvError,
    load_catalog_offers,
)
from app.catalog.offer_seed import (
    OfferSeedError,
    sync_catalog_offers,
)
from app.db.session import SessionLocal

BACKEND_ROOT = Path(__file__).resolve().parents[1]

CSV_PATH = BACKEND_ROOT / "data/catalog-offers.csv"

CATALOG_PATH = BACKEND_ROOT / "data/catalog-v1.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Validate and transactionally seed catalog offers.")
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help=("Validate files without changing the database."),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        rows = load_catalog_offers(
            CSV_PATH,
            CATALOG_PATH,
        )
    except OfferCsvError as exc:
        raise SystemExit(f"Catalog offer validation FAILED:\n{exc}") from exc

    print("Catalog offer validation: OK")
    print(f"Offer rows: {len(rows)}")

    if args.validate_only:
        print("Database unchanged: validate-only mode")
        return

    try:
        with SessionLocal() as db:
            result = sync_catalog_offers(
                db,
                rows=rows,
            )

            db.commit()
    except OfferSeedError as exc:
        raise SystemExit(f"Catalog offer seed FAILED:\n{exc}") from exc

    print()
    print("Catalog offer seed completed")
    print(f"Created:     {result.created}")
    print(f"Updated:     {result.updated}")
    print(f"Deactivated: {result.deactivated}")


if __name__ == "__main__":
    main()
