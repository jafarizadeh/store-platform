from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OrderLineSnapshot:
    offer_id: int
    product_name: str
    offer_name: str
    sku: str
    fulfillment_type: str
    unit_price_cents: int
    quantity: int
