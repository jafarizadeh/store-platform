from __future__ import annotations

from factories.catalog import create_product_offer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog.offer_csv import CatalogOfferRow
from app.catalog.offer_seed import (
    OfferSeedError,
    sync_catalog_offers,
)
from app.models.product import Product
from app.models.product_offer import ProductOffer


def _row(
    *,
    product_slug: str,
    sku: str,
    offer_name: str = "Standard",
    price_cents: int = 1990,
    stock_quantity: int = 5,
    position: int = 0,
    is_active: bool = True,
) -> CatalogOfferRow:
    return CatalogOfferRow(
        product_slug=product_slug,
        product_name=product_slug,
        offer_name=offer_name,
        sku=sku,
        pricing_type="fixed",
        fulfillment_type="physical",
        price_cents=price_cents,
        currency="EUR",
        track_inventory=True,
        stock_quantity=stock_quantity,
        position=position,
        is_active=is_active,
    )


def _create_product(
    db: Session,
    *,
    slug: str,
) -> Product:
    product = Product(
        slug=slug,
        name=slug,
        description=None,
        product_type="component",
        category="Testing",
        difficulty_level=None,
        image_path=None,
        is_active=True,
    )

    db.add(product)
    db.flush()

    return product


def test_sync_catalog_offers_creates_offer(
    db_session: Session,
) -> None:
    product = _create_product(
        db_session,
        slug="seed-create-product",
    )

    result = sync_catalog_offers(
        db_session,
        rows=[
            _row(
                product_slug=product.slug,
                sku="BYN-SEED-CREATE",
                price_cents=2490,
                stock_quantity=7,
            )
        ],
    )

    offer = db_session.scalar(
        select(ProductOffer).where(ProductOffer.sku == "BYN-SEED-CREATE")
    )

    assert offer is not None
    assert offer.product_id == product.id
    assert offer.price_cents == 2490
    assert offer.stock_quantity == 7
    assert offer.is_active is True

    assert result.created == 1
    assert result.updated == 0
    assert result.deactivated == 0


def test_sync_catalog_offers_is_idempotent(
    db_session: Session,
) -> None:
    product = _create_product(
        db_session,
        slug="seed-idempotent-product",
    )

    rows = [
        _row(
            product_slug=product.slug,
            sku="BYN-SEED-IDEMPOTENT",
            price_cents=3490,
            stock_quantity=4,
        )
    ]

    first = sync_catalog_offers(
        db_session,
        rows=rows,
    )

    db_session.flush()

    second = sync_catalog_offers(
        db_session,
        rows=rows,
    )

    offers = db_session.scalars(
        select(ProductOffer).where(ProductOffer.sku == "BYN-SEED-IDEMPOTENT")
    ).all()

    assert len(offers) == 1
    assert first.created == 1
    assert first.updated == 0
    assert second.created == 0
    assert second.updated == 1


def test_sync_catalog_offers_updates_existing_offer(
    db_session: Session,
) -> None:
    product, existing = create_product_offer(
        db_session,
        slug="seed-update-product",
        sku="BYN-SEED-UPDATE",
        offer_name="Old",
        price_cents=1000,
        stock_quantity=2,
    )

    result = sync_catalog_offers(
        db_session,
        rows=[
            _row(
                product_slug=product.slug,
                sku=existing.sku,
                offer_name="Updated",
                price_cents=4590,
                stock_quantity=11,
            )
        ],
    )

    db_session.refresh(existing)

    assert existing.name == "Updated"
    assert existing.price_cents == 4590
    assert existing.stock_quantity == 11
    assert existing.is_active is True

    assert result.created == 0
    assert result.updated == 1
    assert result.deactivated == 0


def test_sync_catalog_offers_deactivates_stale_managed_offer(
    db_session: Session,
) -> None:
    product, stale_offer = create_product_offer(
        db_session,
        slug="seed-stale-product",
        sku="BYN-OLD-OFFER",
        offer_active=True,
    )

    result = sync_catalog_offers(
        db_session,
        rows=[
            _row(
                product_slug=product.slug,
                sku="BYN-NEW-OFFER",
            )
        ],
    )

    db_session.refresh(stale_offer)

    new_offer = db_session.scalar(
        select(ProductOffer).where(ProductOffer.sku == "BYN-NEW-OFFER")
    )

    assert stale_offer.is_active is False
    assert new_offer is not None
    assert new_offer.is_active is True

    assert result.created == 1
    assert result.updated == 0
    assert result.deactivated == 1


def test_sync_catalog_offers_preserves_unmanaged_offer(
    db_session: Session,
) -> None:
    product, unmanaged = create_product_offer(
        db_session,
        slug="seed-unmanaged-product",
        sku="SUPPLIER-KEEP-ME",
        offer_active=True,
    )

    result = sync_catalog_offers(
        db_session,
        rows=[
            _row(
                product_slug=product.slug,
                sku="BYN-MANAGED-OFFER",
            )
        ],
    )

    db_session.refresh(unmanaged)

    assert unmanaged.is_active is True
    assert result.created == 1
    assert result.deactivated == 0


def test_sync_catalog_offers_rejects_sku_owned_by_other_product(
    db_session: Session,
) -> None:
    owner, existing = create_product_offer(
        db_session,
        slug="seed-sku-owner",
        sku="BYN-SKU-CONFLICT",
    )

    target = _create_product(
        db_session,
        slug="seed-sku-target",
    )

    assert existing.product_id == owner.id
    assert target.id != owner.id

    try:
        sync_catalog_offers(
            db_session,
            rows=[
                _row(
                    product_slug=target.slug,
                    sku="BYN-SKU-CONFLICT",
                )
            ],
        )
    except OfferSeedError as exc:
        assert "different product" in str(exc)
    else:
        raise AssertionError("Expected OfferSeedError")


def test_sync_catalog_offers_rejects_empty_input(
    db_session: Session,
) -> None:
    try:
        sync_catalog_offers(
            db_session,
            rows=[],
        )
    except OfferSeedError as exc:
        assert "empty offer list" in str(exc)
    else:
        raise AssertionError("Expected OfferSeedError")
