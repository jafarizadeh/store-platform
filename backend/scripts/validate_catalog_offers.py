from pathlib import Path

from app.catalog.offer_csv import (
    OfferCsvError,
    load_catalog_offers,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]

CSV_PATH = BACKEND_ROOT / "data/catalog-offers.csv"

CATALOG_PATH = BACKEND_ROOT / "data/catalog-v1.json"


def main() -> None:
    try:
        rows = load_catalog_offers(
            CSV_PATH,
            CATALOG_PATH,
        )
    except OfferCsvError as exc:
        raise SystemExit(f"Catalog offer validation FAILED:\n{exc}") from exc

    products = {row.product_slug for row in rows}

    skus = {row.sku for row in rows}

    active = sum(row.is_active for row in rows)

    print("Catalog offer validation: OK")
    print(f"Products covered: {len(products)}")
    print(f"Offer rows:       {len(rows)}")
    print(f"Unique SKUs:      {len(skus)}")
    print(f"Active offers:    {active}")
    print("Database unchanged.")


if __name__ == "__main__":
    main()
