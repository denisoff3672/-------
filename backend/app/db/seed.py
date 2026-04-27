from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.entities import Car, CarComfortClass, Client, Driver, Tariff, User, UserRole


PREDEFINED_USERS = [
    {
        "username": "denis.drobot888@gmail.com",
        "password": "Qwerty13",
        "first_name": "Denis",
        "last_name": "Drobot",
        "phone": "+380500000000",
        "role": UserRole.ADMIN,
    },
    {
        "username": "driver@taxi.local",
        "password": "driver123",
        "first_name": "Demo",
        "last_name": "Driver",
        "phone": "+380500000002",
        "role": UserRole.DRIVER,
        "license_number": "DRV-DEFAULT-001",
    },
    {
        "username": "client@taxi.local",
        "password": "client123",
        "first_name": "Demo",
        "last_name": "Client",
        "phone": "+380500000001",
        "role": UserRole.CLIENT,
    },
]


def _fleet_definitions() -> list[dict]:
    fleet: list[dict] = []

    economy_models = [("Dacia", "Logan"), ("Dacia", "Sandero")]
    comfort_models = [("Volkswagen", "Passat B7"), ("Volkswagen", "Passat NMS"), ("Renault", "Laguna")]
    business_models = [("BMW", "7 Series"), ("Mercedes", "S Class")]

    for index in range(10):
        make, model = economy_models[index % len(economy_models)]
        fleet.append(
            {
                "plate_number": f"AE10{index:02d}EK",
                "make": make,
                "model": model,
                "production_year": 2013 + (index % 5),
                "engine": "1.2 бензин" if index % 2 == 0 else "1.5 дизель",
                "transmission": "manual" if index % 2 == 0 else "automatic",
                "color": "White",
                "comfort_class": CarComfortClass.ECONOMY,
                "technical_status": "good",
            }
        )

    for index in range(10):
        make, model = comfort_models[index % len(comfort_models)]
        fleet.append(
            {
                "plate_number": f"BC20{index:02d}CM",
                "make": make,
                "model": model,
                "production_year": 2014 + (index % 6),
                "engine": "2.0 дизель" if index % 2 == 0 else "1.8 бензин",
                "transmission": "automatic",
                "color": "Black",
                "comfort_class": CarComfortClass.COMFORT,
                "technical_status": "good",
            }
        )

    for index in range(10):
        make, model = business_models[index % len(business_models)]
        fleet.append(
            {
                "plate_number": f"KA30{index:02d}BS",
                "make": make,
                "model": model,
                "production_year": 2017 + (index % 7),
                "engine": "3.0 бензин" if index % 2 == 0 else "3.0 дизель",
                "transmission": "automatic",
                "color": "Graphite",
                "comfort_class": CarComfortClass.BUSINESS,
                "technical_status": "good",
            }
        )

    return fleet


def _ensure_unique_license_number(db: Session, base_license: str) -> str:
    candidate = base_license
    suffix = 1

    while db.scalar(select(Driver).where(Driver.license_number == candidate)):
        candidate = f"{base_license}-{suffix:03d}"
        suffix += 1

    return candidate


def seed_default_tariffs(db: Session) -> None:
    defaults = [
        {
            "comfort_class": CarComfortClass.ECONOMY,
            "base_fare": 0,
            "price_per_km": 25,
            "price_per_minute": 1.5,
            "night_multiplier": 1.0,
        },
        {
            "comfort_class": CarComfortClass.STANDARD,
            "base_fare": 0,
            "price_per_km": 35,
            "price_per_minute": 2,
            "night_multiplier": 1.0,
        },
        {
            "comfort_class": CarComfortClass.COMFORT,
            "base_fare": 0,
            "price_per_km": 35,
            "price_per_minute": 2.2,
            "night_multiplier": 1.0,
        },
        {
            "comfort_class": CarComfortClass.BUSINESS,
            "base_fare": 0,
            "price_per_km": 50,
            "price_per_minute": 2.8,
            "night_multiplier": 1.0,
        },
    ]

    for item in defaults:
        existing = db.scalar(select(Tariff).where(Tariff.comfort_class == item["comfort_class"]))
        if not existing:
            db.add(Tariff(**item))

    db.commit()


def seed_predefined_users(db: Session) -> None:
    for payload in PREDEFINED_USERS:
        existing_user = db.scalar(select(User).where(User.username == payload["username"]))
        user = existing_user

        if not user:
            user = User(
                username=payload["username"],
                hashed_password=hash_password(payload["password"]),
                first_name=payload["first_name"],
                last_name=payload["last_name"],
                phone=payload["phone"],
                role=payload["role"],
            )
            db.add(user)
            db.flush()

        if payload["role"] == UserRole.CLIENT:
            existing_client_profile = db.scalar(select(Client).where(Client.user_id == user.id))
            if not existing_client_profile:
                db.add(Client(user_id=user.id, phone=payload["phone"], balance=0))

        if payload["role"] == UserRole.DRIVER:
            existing_driver_profile = db.scalar(select(Driver).where(Driver.user_id == user.id))
            if not existing_driver_profile:
                license_number = f"DRV-{user.id:06d}"
                existing_license = db.scalar(select(Driver).where(Driver.license_number == license_number))
                if existing_license:
                    license_number = _ensure_unique_license_number(db, license_number)
                db.add(Driver(user_id=user.id, license_number=license_number))

    db.commit()


def seed_fleet_cars(db: Session) -> None:
    for car_payload in _fleet_definitions():
        existing_car = db.scalar(select(Car).where(Car.plate_number == car_payload["plate_number"]))
        if not existing_car:
            db.add(Car(**car_payload))

    db.commit()
