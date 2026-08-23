from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.product_offer import ProductOffer


def create_product_offer(
    db: Session,
    *,
    slug: str,
    product_name: str | None = None,
    offer_name: str = "Standard",
    sku: str | None = None,
    product_type: str = "component",
    category: str = "Testing",
    difficulty_level: int | None = None,
    pricing_type: str = "fixed",
    fulfillment_type: str = "physical",
    price_cents: int | None = 1000,
    currency: str | None = "EUR",
    track_inventory: bool = True,
    stock_quantity: int = 10,
    product_active: bool = True,
    offer_active: bool = True,
) -> tuple[Product, ProductOffer]:
    product = Product(
        slug=slug,
        name=product_name or slug,
        description=None,
        product_type=product_type,
        category=category,
        difficulty_level=difficulty_level,
        image_path=None,
        is_active=product_active,
    )

    offer = ProductOffer(
        product=product,
        sku=sku or f"{slug}-standard",
        name=offer_name,
        pricing_type=pricing_type,
        fulfillment_type=fulfillment_type,
        price_cents=price_cents,
        currency=currency,
        track_inventory=track_inventory,
        stock_quantity=stock_quantity,
        is_active=offer_active,
        position=0,
    )

    db.add(product)
    db.flush()

    return product, offer
