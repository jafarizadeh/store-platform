from pydantic import BaseModel, ConfigDict


class ProductResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    slug: str
    name: str
    description: str | None
    category: str
    image_path: str | None
    price_cents: int
    currency: str
    stock_quantity: int
