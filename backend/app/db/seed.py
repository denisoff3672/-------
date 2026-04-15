from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import CarComfortClass, Tariff


def seed_default_tariffs(db: Session) -> None:
    defaults = [
        {
            "comfort_class": CarComfortClass.ECONOMY,
            "base_fare": 35,
            "price_per_km": 12,
            "price_per_minute": 1.5,
            "night_multiplier": 1.1,
        },
        {
            "comfort_class": CarComfortClass.STANDARD,
            "base_fare": 45,
            "price_per_km": 15,
            "price_per_minute": 2,
            "night_multiplier": 1.15,
        },
        {
            "comfort_class": CarComfortClass.BUSINESS,
            "base_fare": 70,
            "price_per_km": 22,
            "price_per_minute": 2.8,
            "night_multiplier": 1.2,
        },
    ]

    for item in defaults:
        existing = db.scalar(select(Tariff).where(Tariff.comfort_class == item["comfort_class"]))
        if not existing:
            db.add(Tariff(**item))

    db.commit()
