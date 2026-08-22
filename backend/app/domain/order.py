from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OrderLineSnapshot:
    product_id: int
    product_name: str
    unit_price_cents: int
    quantity: int
