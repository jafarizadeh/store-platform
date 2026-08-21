from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.product import Product

PRODUCTS = [
    {
        "slug": "raspberry-pi-5",
        "name": "Raspberry Pi 5",
        "description": "Powerful Raspberry Pi board for modern projects.",
        "category": "Boards",
        "image_path": "/assets/products/raspberry-pi/rpi01.png",
        "price_cents": 7900,
        "currency": "EUR",
        "stock_quantity": 10,
    },
    {
        "slug": "compute-module-5",
        "name": "Compute Module 5",
        "description": "Compact computing platform for embedded applications.",
        "category": "Modules",
        "image_path": "/assets/products/raspberry-pi/rpi02.png",
        "price_cents": 5900,
        "currency": "EUR",
        "stock_quantity": 10,
    },
    {
        "slug": "raspberry-pi-pico",
        "name": "Raspberry Pi Pico",
        "description": "Small and affordable board for electronics experiments.",
        "category": "Microcontrollers",
        "image_path": "/assets/products/raspberry-pi/rpi03.png",
        "price_cents": 900,
        "currency": "EUR",
        "stock_quantity": 20,
    },
]


def main() -> None:
    with SessionLocal() as db:
        for data in PRODUCTS:
            product = db.scalar(select(Product).where(Product.slug == data["slug"]))

            if product is None:
                product = Product(**data)
                db.add(product)
            else:
                for key, value in data.items():
                    setattr(product, key, value)

        db.commit()


if __name__ == "__main__":
    main()
