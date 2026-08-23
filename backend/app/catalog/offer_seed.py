from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.catalog.offer_csv import CatalogOfferRow
from app.models.product import Product
from app.models.product_offer import ProductOffer

CATALOG_MANAGED_SKU_PREFIX = "BYN-"

DEMO_OFFER_SKUS = {
    "rpi5-standard",
    "cm5-standard",
    "pico-standard",
}


@dataclass(
    frozen=True,
    slots=True,
)
class OfferSeedResult:
    created: int
    updated: int
    deactivated: int


class OfferSeedError(RuntimeError):
    """Raised when validated offer data cannot be safely seeded."""


def _load_products(
    db: Session,
    *,
    slugs: set[str],
) -> dict[str, Product]:
    products = db.scalars(select(Product).where(Product.slug.in_(slugs))).all()

    by_slug = {product.slug: product for product in products}

    missing = sorted(slugs - set(by_slug))

    if missing:
        raise OfferSeedError(
            "Products are missing from the database:\n  " + "\n  ".join(missing)
        )

    return by_slug


def _apply_row(
    *,
    offer: ProductOffer,
    row: CatalogOfferRow,
) -> None:
    offer.name = row.offer_name
    offer.pricing_type = row.pricing_type
    offer.fulfillment_type = row.fulfillment_type
    offer.price_cents = row.price_cents
    offer.currency = row.currency
    offer.track_inventory = row.track_inventory
    offer.stock_quantity = row.stock_quantity
    offer.position = row.position
    offer.is_active = row.is_active


def _deactivate_stale_managed_offers(
    db: Session,
    *,
    catalog_product_ids: set[int],
    desired_skus: set[str],
) -> int:
    offers = db.scalars(
        select(ProductOffer).where(
            ProductOffer.product_id.in_(catalog_product_ids),
            ProductOffer.is_active.is_(True),
            or_(
                ProductOffer.sku.like(f"{CATALOG_MANAGED_SKU_PREFIX}%"),
                ProductOffer.sku.like("legacy-%"),
                ProductOffer.sku.in_(DEMO_OFFER_SKUS),
            ),
        )
    ).all()

    deactivated = 0

    for offer in offers:
        if offer.sku in desired_skus:
            continue

        offer.is_active = False
        deactivated += 1

    return deactivated


def sync_catalog_offers(
    db: Session,
    *,
    rows: list[CatalogOfferRow],
) -> OfferSeedResult:
    if not rows:
        raise OfferSeedError("Refusing to seed an empty offer list")

    slugs = {row.product_slug for row in rows}

    products = _load_products(
        db,
        slugs=slugs,
    )

    desired_skus = {row.sku for row in rows}

    existing_offers = db.scalars(
        select(ProductOffer).where(ProductOffer.sku.in_(desired_skus))
    ).all()

    offers_by_sku = {offer.sku: offer for offer in existing_offers}

    created = 0
    updated = 0

    for row in rows:
        product = products[row.product_slug]

        offer = offers_by_sku.get(row.sku)

        if offer is None:
            offer = ProductOffer(
                product_id=product.id,
                sku=row.sku,
                name=row.offer_name,
                pricing_type=row.pricing_type,
                fulfillment_type=row.fulfillment_type,
                price_cents=row.price_cents,
                currency=row.currency,
                track_inventory=row.track_inventory,
                stock_quantity=row.stock_quantity,
                is_active=row.is_active,
                position=row.position,
            )

            db.add(offer)

            offers_by_sku[row.sku] = offer

            created += 1
            continue

        if offer.product_id != product.id:
            raise OfferSeedError(
                f"SKU {row.sku!r} already belongs to a different product"
            )

        _apply_row(
            offer=offer,
            row=row,
        )

        updated += 1

    deactivated = _deactivate_stale_managed_offers(
        db,
        catalog_product_ids={product.id for product in products.values()},
        desired_skus=desired_skus,
    )

    db.flush()

    return OfferSeedResult(
        created=created,
        updated=updated,
        deactivated=deactivated,
    )
