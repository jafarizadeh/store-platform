from pydantic import BaseModel, ConfigDict


class ProductImageResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    image_path: str
    alt_text: str | None
    position: int
    is_primary: bool


class ProductOfferResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    sku: str
    name: str
    pricing_type: str
    fulfillment_type: str
    price_cents: int | None
    currency: str | None
    track_inventory: bool
    stock_quantity: int
    position: int


class ProductResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    slug: str
    name: str
    description: str | None
    product_type: str
    category: str
    difficulty_level: int | None
    images: list[ProductImageResponse]
    offers: list[ProductOfferResponse]
