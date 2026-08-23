from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.product_offer import ProductOffer

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent

CATALOG_PATH = BACKEND_ROOT / "data/catalog-v1.json"
PUBLIC_ROOT = REPO_ROOT / "frontend/public"
PRODUCT_ASSET_ROOT = (PUBLIC_ROOT / "assets/products").resolve()

EXPECTED_PRODUCTS = 26
EXPECTED_IMAGES = 102

VALID_PRODUCT_TYPES = {
    "component",
    "kit",
    "project",
    "solution",
    "service",
}

# These belong to the old development/demo seed and must never
# appear as real commercial offers.
DEMO_OFFER_SKUS = {
    "rpi5-standard",
    "cm5-standard",
    "pico-standard",
}


def _require_string(
    entry: dict[str, Any],
    key: str,
) -> str:
    value = entry.get(key)

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key!r} must be a non-empty string")

    return value.strip()


def _validate_image_path(
    image_path: str,
) -> Path:
    if not image_path.startswith("/assets/products/"):
        raise ValueError(f"Invalid product image path: {image_path}")

    public_file = (PUBLIC_ROOT / image_path.lstrip("/")).resolve()

    if not public_file.is_relative_to(PRODUCT_ASSET_ROOT):
        raise ValueError(f"Image path escapes product asset root: {image_path}")

    if not public_file.is_file() or public_file.suffix.lower() != ".webp":
        raise ValueError(f"Product image does not exist: {public_file}")

    return public_file


def load_catalog() -> list[dict[str, Any]]:
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    if not isinstance(raw, list):
        raise ValueError("Catalog root must be a JSON array")

    if len(raw) != EXPECTED_PRODUCTS:
        raise ValueError(f"Expected {EXPECTED_PRODUCTS} products, found {len(raw)}")

    seen_slugs: set[str] = set()
    total_images = 0

    for entry in raw:
        if not isinstance(entry, dict):
            raise ValueError("Every catalog entry must be an object")

        slug = _require_string(
            entry,
            "slug",
        )
        _require_string(
            entry,
            "name",
        )
        category = _require_string(
            entry,
            "category",
        )
        product_type = _require_string(
            entry,
            "product_type",
        )

        if slug in seen_slugs:
            raise ValueError(f"Duplicate product slug: {slug}")

        seen_slugs.add(slug)

        if product_type not in VALID_PRODUCT_TYPES:
            raise ValueError(f"Invalid product_type for {slug}: {product_type}")

        if len(category) > 80:
            raise ValueError(f"Category too long for {slug}")

        difficulty = entry.get("difficulty_level")

        if difficulty is not None and (
            not isinstance(difficulty, int) or not 1 <= difficulty <= 10
        ):
            raise ValueError(f"Invalid difficulty_level for {slug}")

        offers = entry.get("offers")

        if offers != []:
            raise ValueError(
                f"{slug}: offers must remain empty until "
                "real SKU/price/stock data is supplied"
            )

        images = entry.get("images")

        if not isinstance(images, list) or not images:
            raise ValueError(f"{slug}: at least one image is required")

        positions: set[int] = set()
        paths: set[str] = set()
        primary_count = 0

        for image in images:
            if not isinstance(image, dict):
                raise ValueError(f"{slug}: invalid image entry")

            image_path = _require_string(
                image,
                "image_path",
            )

            position = image.get("position")

            is_primary = image.get("is_primary")

            alt_text = image.get("alt_text")

            if not isinstance(position, int) or position < 0:
                raise ValueError(f"{slug}: invalid image position")

            if position in positions:
                raise ValueError(f"{slug}: duplicate image position {position}")

            positions.add(position)

            if image_path in paths:
                raise ValueError(f"{slug}: duplicate image path {image_path}")

            paths.add(image_path)

            if not isinstance(
                is_primary,
                bool,
            ):
                raise ValueError(f"{slug}: is_primary must be boolean")

            if is_primary:
                primary_count += 1

            if alt_text is not None and (
                not isinstance(
                    alt_text,
                    str,
                )
                or len(alt_text) > 255
            ):
                raise ValueError(f"{slug}: invalid alt_text")

            _validate_image_path(image_path)

        expected_positions = set(range(len(images)))

        if positions != expected_positions:
            raise ValueError(
                f"{slug}: image positions must be contiguous starting at zero"
            )

        if primary_count != 1:
            raise ValueError(f"{slug}: exactly one primary image is required")

        total_images += len(images)

    if total_images != EXPECTED_IMAGES:
        raise ValueError(f"Expected {EXPECTED_IMAGES} images, found {total_images}")

    return raw


def _sync_product_images(
    db: Session,
    *,
    product: Product,
    images: list[dict[str, Any]],
) -> int:
    db.execute(delete(ProductImage).where(ProductImage.product_id == product.id))

    db.flush()

    for image in images:
        db.add(
            ProductImage(
                product_id=product.id,
                image_path=image["image_path"],
                alt_text=image.get("alt_text"),
                position=image["position"],
                is_primary=image["is_primary"],
            )
        )

    return len(images)


def _upsert_product(
    db: Session,
    *,
    entry: dict[str, Any],
) -> tuple[Product, bool]:
    slug = entry["slug"]

    product = db.scalar(select(Product).where(Product.slug == slug))

    created = product is None

    primary_image = next(image for image in entry["images"] if image["is_primary"])

    values = {
        "name": entry["name"],
        "description": (entry.get("description") or None),
        "product_type": entry["product_type"],
        "category": entry["category"],
        "difficulty_level": entry.get("difficulty_level"),
        # Legacy compatibility column. Public API now
        # uses product_images instead.
        "image_path": primary_image["image_path"],
        "is_active": bool(
            entry.get(
                "is_active",
                True,
            )
        ),
    }

    if product is None:
        product = Product(
            slug=slug,
            **values,
        )

        db.add(product)
        db.flush()
    else:
        for key, value in values.items():
            setattr(
                product,
                key,
                value,
            )

        db.flush()

    return product, created


def _deactivate_products_outside_catalog(
    db: Session,
    *,
    catalog_slugs: set[str],
) -> list[str]:
    products = db.scalars(
        select(Product).where(
            Product.is_active.is_(True),
            ~Product.slug.in_(catalog_slugs),
        )
    ).all()

    deactivated: list[str] = []

    for product in products:
        product.is_active = False
        deactivated.append(product.slug)

    return sorted(deactivated)


def _deactivate_demo_offers(
    db: Session,
) -> list[str]:
    offers = db.scalars(
        select(ProductOffer).where(ProductOffer.is_active.is_(True))
    ).all()

    offers = [
        offer
        for offer in offers
        if (offer.sku in DEMO_OFFER_SKUS or offer.sku.startswith("legacy-"))
    ]

    deactivated: list[str] = []

    for offer in offers:
        offer.is_active = False
        deactivated.append(offer.sku)

    return sorted(deactivated)


def seed_catalog(
    catalog: list[dict[str, Any]],
) -> None:
    created_products = 0
    updated_products = 0
    image_count = 0

    catalog_slugs = {entry["slug"] for entry in catalog}

    with SessionLocal() as db:
        for entry in catalog:
            product, created = _upsert_product(
                db,
                entry=entry,
            )

            if created:
                created_products += 1
            else:
                updated_products += 1

            image_count += _sync_product_images(
                db,
                product=product,
                images=entry["images"],
            )

        deactivated_products = _deactivate_products_outside_catalog(
            db,
            catalog_slugs=catalog_slugs,
        )

        deactivated_demo_offers = _deactivate_demo_offers(db)

        db.commit()

    print()
    print("Catalog seed completed")
    print(f"Created products:      {created_products}")
    print(f"Updated products:      {updated_products}")
    print(f"Synced images:         {image_count}")
    print(f"Deactivated products: {len(deactivated_products)}")
    print(f"Deactivated demo offers: {len(deactivated_demo_offers)}")

    if deactivated_products:
        print()
        print("Products deactivated because they are outside catalog:")

        for slug in deactivated_products:
            print(f"  - {slug}")

    if deactivated_demo_offers:
        print()
        print("Legacy demo offers deactivated:")

        for sku in deactivated_demo_offers:
            print(f"  - {sku}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Validate or seed the ByNET product catalog.")
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help=(
            "Validate the catalog manifest "
            "and asset files without changing "
            "the database."
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    catalog = load_catalog()

    print(f"Catalog validated: {len(catalog)} products")

    print(f"Images validated: {sum(len(item['images']) for item in catalog)}")

    if args.validate_only:
        print("Database unchanged: validate-only mode")
        return

    seed_catalog(catalog)


if __name__ == "__main__":
    main()
