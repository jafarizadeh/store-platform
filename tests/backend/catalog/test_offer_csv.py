import csv
import json
from pathlib import Path

import pytest

from app.catalog.offer_csv import (
    EXPECTED_FIELDS,
    OfferCsvError,
    load_catalog_offers,
)


def _write_catalog(
    path: Path,
) -> None:
    path.write_text(
        json.dumps(
            [
                {
                    "slug": "product-a",
                    "name": "Product A",
                },
                {
                    "slug": "product-b",
                    "name": "Product B",
                },
            ]
        ),
        encoding="utf-8",
    )


def _base_rows():
    return [
        {
            "product_slug": "product-a",
            "product_name": "Product A",
            "offer_name": "Standard",
            "sku": "TEST-A",
            "pricing_type": "fixed",
            "fulfillment_type": "physical",
            "price_cents": "1000",
            "currency": "EUR",
            "track_inventory": "true",
            "stock_quantity": "5",
            "position": "0",
            "is_active": "true",
        },
        {
            "product_slug": "product-b",
            "product_name": "Product B",
            "offer_name": "Standard",
            "sku": "TEST-B",
            "pricing_type": "fixed",
            "fulfillment_type": "physical",
            "price_cents": "2000",
            "currency": "EUR",
            "track_inventory": "true",
            "stock_quantity": "3",
            "position": "0",
            "is_active": "true",
        },
    ]


def _write_csv(
    path: Path,
    rows,
) -> None:
    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=EXPECTED_FIELDS,
        )
        writer.writeheader()
        writer.writerows(rows)


def test_valid_offer_csv(
    tmp_path: Path,
) -> None:
    catalog = tmp_path / "catalog.json"
    offers = tmp_path / "offers.csv"

    _write_catalog(catalog)
    _write_csv(
        offers,
        _base_rows(),
    )

    rows = load_catalog_offers(
        offers,
        catalog,
    )

    assert len(rows) == 2
    assert rows[0].price_cents == 1000
    assert rows[0].is_active


def test_duplicate_sku_is_rejected(
    tmp_path: Path,
) -> None:
    catalog = tmp_path / "catalog.json"
    offers = tmp_path / "offers.csv"

    rows = _base_rows()
    rows[1]["sku"] = "TEST-A"

    _write_catalog(catalog)
    _write_csv(offers, rows)

    with pytest.raises(
        OfferCsvError,
        match="duplicate sku",
    ):
        load_catalog_offers(
            offers,
            catalog,
        )


def test_duplicate_product_position_is_rejected(
    tmp_path: Path,
) -> None:
    catalog = tmp_path / "catalog.json"
    offers = tmp_path / "offers.csv"

    rows = _base_rows()

    duplicate = dict(rows[0])
    duplicate["sku"] = "TEST-A-SECOND"

    rows.insert(
        1,
        duplicate,
    )

    _write_catalog(catalog)
    _write_csv(offers, rows)

    with pytest.raises(
        OfferCsvError,
        match="duplicate offer position",
    ):
        load_catalog_offers(
            offers,
            catalog,
        )


def test_quote_offer_cannot_have_price(
    tmp_path: Path,
) -> None:
    catalog = tmp_path / "catalog.json"
    offers = tmp_path / "offers.csv"

    rows = _base_rows()

    rows[0]["pricing_type"] = "quote"

    _write_catalog(catalog)
    _write_csv(offers, rows)

    with pytest.raises(
        OfferCsvError,
        match=("quote offers must not define price_cents"),
    ):
        load_catalog_offers(
            offers,
            catalog,
        )


def test_missing_product_offer_is_rejected(
    tmp_path: Path,
) -> None:
    catalog = tmp_path / "catalog.json"
    offers = tmp_path / "offers.csv"

    rows = _base_rows()[:1]

    _write_catalog(catalog)
    _write_csv(offers, rows)

    with pytest.raises(
        OfferCsvError,
        match=("Products without any offer row"),
    ):
        load_catalog_offers(
            offers,
            catalog,
        )
