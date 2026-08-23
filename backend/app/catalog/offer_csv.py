from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

EXPECTED_FIELDS = [
    "product_slug",
    "product_name",
    "offer_name",
    "sku",
    "pricing_type",
    "fulfillment_type",
    "price_cents",
    "currency",
    "track_inventory",
    "stock_quantity",
    "position",
    "is_active",
]

VALID_PRICING_TYPES = {
    "fixed",
    "quote",
}

VALID_FULFILLMENT_TYPES = {
    "physical",
    "digital",
    "service",
}

SKU_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")

CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")


class OfferCsvError(ValueError):
    """Raised when catalog offer CSV data is invalid."""


@dataclass(
    frozen=True,
    slots=True,
)
class CatalogOfferRow:
    product_slug: str
    product_name: str
    offer_name: str
    sku: str
    pricing_type: str
    fulfillment_type: str
    price_cents: int | None
    currency: str | None
    track_inventory: bool
    stock_quantity: int
    position: int
    is_active: bool


def _fail(
    line: int,
    message: str,
) -> OfferCsvError:
    return OfferCsvError(f"CSV line {line}: {message}")


def _parse_bool(
    value: str,
    *,
    field: str,
    line: int,
) -> bool:
    normalized = value.strip().lower()

    if normalized == "true":
        return True

    if normalized == "false":
        return False

    raise _fail(
        line,
        f"{field} must be true or false",
    )


def _parse_nonnegative_int(
    value: str,
    *,
    field: str,
    line: int,
) -> int:
    raw = value.strip()

    if not raw:
        raise _fail(
            line,
            f"{field} is required",
        )

    try:
        parsed = int(raw)
    except ValueError as exc:
        raise _fail(
            line,
            f"{field} must be an integer",
        ) from exc

    if parsed < 0:
        raise _fail(
            line,
            f"{field} must be non-negative",
        )

    return parsed


def _load_catalog_names(
    catalog_path: Path,
) -> dict[str, str]:
    try:
        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise OfferCsvError(f"Cannot read catalog manifest: {exc}") from exc

    if not isinstance(raw, list):
        raise OfferCsvError("Catalog manifest must contain a JSON array")

    result: dict[str, str] = {}

    for entry in raw:
        if not isinstance(entry, dict):
            raise OfferCsvError("Catalog manifest contains an invalid entry")

        slug = entry.get("slug")
        name = entry.get("name")

        if (
            not isinstance(slug, str)
            or not slug
            or not isinstance(name, str)
            or not name
        ):
            raise OfferCsvError("Catalog product requires slug and name")

        if slug in result:
            raise OfferCsvError(f"Duplicate catalog slug: {slug}")

        result[slug] = name

    return result


def load_catalog_offers(
    csv_path: Path,
    catalog_path: Path,
) -> list[CatalogOfferRow]:
    catalog_names = _load_catalog_names(catalog_path)

    try:
        handle = csv_path.open(
            encoding="utf-8-sig",
            newline="",
        )
    except OSError as exc:
        raise OfferCsvError(f"Cannot open offer CSV: {exc}") from exc

    rows: list[CatalogOfferRow] = []
    seen_skus: set[str] = set()
    seen_positions: set[tuple[str, int]] = set()
    covered_products: set[str] = set()

    with handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames != EXPECTED_FIELDS:
            raise OfferCsvError(
                "CSV header does not match expected schema.\n"
                f"Expected: {EXPECTED_FIELDS}\n"
                f"Found:    {reader.fieldnames}"
            )

        for raw_row in reader:
            line = reader.line_num

            if not any((value or "").strip() for value in raw_row.values()):
                continue

            product_slug = raw_row["product_slug"].strip()

            product_name = raw_row["product_name"].strip()

            offer_name = raw_row["offer_name"].strip()

            sku = raw_row["sku"].strip()

            pricing_type = raw_row["pricing_type"].strip()

            fulfillment_type = raw_row["fulfillment_type"].strip()

            currency_raw = raw_row["currency"].strip()

            if product_slug not in catalog_names:
                raise _fail(
                    line,
                    f"unknown product_slug: {product_slug!r}",
                )

            expected_name = catalog_names[product_slug]

            if product_name != expected_name:
                raise _fail(
                    line,
                    "product_name does not match catalog manifest "
                    f"for {product_slug!r}",
                )

            if not offer_name:
                raise _fail(
                    line,
                    "offer_name is required",
                )

            if len(offer_name) > 160:
                raise _fail(
                    line,
                    "offer_name exceeds 160 characters",
                )

            if not SKU_PATTERN.fullmatch(sku):
                raise _fail(
                    line,
                    "sku must be 1-120 characters and contain "
                    "only letters, numbers, '.', '_' or '-'",
                )

            if sku in seen_skus:
                raise _fail(
                    line,
                    f"duplicate sku: {sku}",
                )

            seen_skus.add(sku)

            if pricing_type not in VALID_PRICING_TYPES:
                raise _fail(
                    line,
                    "pricing_type must be fixed or quote",
                )

            if fulfillment_type not in VALID_FULFILLMENT_TYPES:
                raise _fail(
                    line,
                    "fulfillment_type must be physical, digital or service",
                )

            price_raw = raw_row["price_cents"].strip()

            if pricing_type == "fixed":
                price_cents = _parse_nonnegative_int(
                    price_raw,
                    field="price_cents",
                    line=line,
                )

                if not CURRENCY_PATTERN.fullmatch(currency_raw):
                    raise _fail(
                        line,
                        "fixed offers require a 3-letter uppercase currency code",
                    )

                currency: str | None = currency_raw
            else:
                if price_raw:
                    raise _fail(
                        line,
                        "quote offers must not define price_cents",
                    )

                price_cents = None

                if currency_raw and not CURRENCY_PATTERN.fullmatch(currency_raw):
                    raise _fail(
                        line,
                        "currency must be blank or a 3-letter uppercase code",
                    )

                currency = currency_raw or None

            track_inventory = _parse_bool(
                raw_row["track_inventory"],
                field="track_inventory",
                line=line,
            )

            stock_quantity = _parse_nonnegative_int(
                raw_row["stock_quantity"],
                field="stock_quantity",
                line=line,
            )

            position = _parse_nonnegative_int(
                raw_row["position"],
                field="position",
                line=line,
            )

            position_key = (
                product_slug,
                position,
            )

            if position_key in seen_positions:
                raise _fail(
                    line,
                    f"duplicate offer position {position} for {product_slug}",
                )

            seen_positions.add(position_key)

            is_active = _parse_bool(
                raw_row["is_active"],
                field="is_active",
                line=line,
            )

            rows.append(
                CatalogOfferRow(
                    product_slug=product_slug,
                    product_name=product_name,
                    offer_name=offer_name,
                    sku=sku,
                    pricing_type=pricing_type,
                    fulfillment_type=fulfillment_type,
                    price_cents=price_cents,
                    currency=currency,
                    track_inventory=track_inventory,
                    stock_quantity=stock_quantity,
                    position=position,
                    is_active=is_active,
                )
            )

            covered_products.add(product_slug)

    missing_products = sorted(set(catalog_names) - covered_products)

    if missing_products:
        raise OfferCsvError(
            "Products without any offer row:\n  " + "\n  ".join(missing_products)
        )

    if not rows:
        raise OfferCsvError("Offer CSV contains no data rows")

    return rows
