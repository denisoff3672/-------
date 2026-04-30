from __future__ import annotations

import argparse
import csv
import json
import random
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.db.seed import PREDEFINED_USERS, _fleet_definitions, seed_default_tariffs
from app.db.seed_from_sources import CAR_MAKES_MODELS, NAMES, ORDER_REVIEW_COMMENTS, SURNAMES
from app.models.entities import (
    AuthToken,
    Car,
    CarComfortClass,
    Client,
    Driver,
    DriverApplication,
    DriverApplicationStatus,
    DriverClassApplication,
    DriverClassApplicationStatus,
    DriverStatus,
    Order,
    OrderStatus,
    Review,
    Tariff,
    TokenType,
    User,
    UserRole,
)
from app.services.pricing import haversine_km

DEFAULT_SEED_RECORDS = 1000
DEFAULT_RANDOM_SEED = 42
DEFAULT_BULK_SEED_PATH = Path(__file__).with_name("seed_bulk_data.json")
DEFAULT_ADMIN_EMAIL = "admin@taxi.local"
DEFAULT_ADMIN_PASSWORD = "admin123"

ADDRESS_POOL = [
    "вул. Шевченка, 1",
    "просп. Чорновола, 45",
    "вул. Стрийська, 111",
    "вул. Городоцька, 25",
    "вул. Франка, 12",
    "вул. Личаківська, 80",
    "вул. Наукова, 7",
    "вул. Кульпарківська, 95",
]

UKRAINE_BOUNDS = {
    "min_lat": 44.0,
    "max_lat": 52.5,
    "min_lng": 22.0,
    "max_lng": 41.5,
}
LVIV_BOUNDS = {
    "min_lat": 49.77,
    "max_lat": 49.9,
    "min_lng": 23.9,
    "max_lng": 24.1,
}

TARIFF_PRESETS = {
    CarComfortClass.ECONOMY: (0, 25, 1.5, 1.0),
    CarComfortClass.STANDARD: (0, 35, 2.0, 1.0),
    CarComfortClass.COMFORT: (0, 35, 2.2, 1.0),
    CarComfortClass.BUSINESS: (0, 50, 2.8, 1.0),
}


@dataclass(slots=True)
class SeedMeta:
    generated_at: str
    records_per_table: int
    random_seed: int
    admin_email: str


@dataclass(slots=True)
class SeedSummary:
    users: int = 0
    clients: int = 0
    drivers: int = 0
    cars: int = 0
    driver_applications: int = 0
    driver_class_applications: int = 0
    orders: int = 0
    reviews: int = 0
    auth_tokens: int = 0
    tariffs: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "users": self.users,
            "clients": self.clients,
            "drivers": self.drivers,
            "cars": self.cars,
            "driver_applications": self.driver_applications,
            "driver_class_applications": self.driver_class_applications,
            "orders": self.orders,
            "reviews": self.reviews,
            "auth_tokens": self.auth_tokens,
            "tariffs": self.tariffs,
        }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _unique_phone(prefix: str, index: int) -> str:
    return f"+380{prefix}{1000000 + index:07d}"


def _build_plate(index: int) -> str:
    return f"SE{index:04d}ED"


def _random_car_class(rng: random.Random) -> CarComfortClass:
    return rng.choices(
        [CarComfortClass.ECONOMY, CarComfortClass.STANDARD, CarComfortClass.COMFORT, CarComfortClass.BUSINESS],
        weights=[0.4, 0.3, 0.2, 0.1],
        k=1,
    )[0]


def _random_name(rng: random.Random) -> tuple[str, str]:
    return rng.choice(NAMES), rng.choice(SURNAMES)


def _clean_address_cell(value: str | None) -> str | None:
    if not value:
        return None
    candidate = str(value).strip().lstrip("\ufeff")
    candidate = re.sub(r"^\d+[\.)]\s*", "", candidate)
    candidate = re.sub(r"\s+", " ", candidate).strip(" ;.")
    if "," not in candidate:
        return None
    return candidate


def load_addresses_from_csv(path: Path | None) -> list[str]:
    if not path or not path.exists():
        return ADDRESS_POOL.copy()

    text = ""
    for encoding in ("utf-8-sig", "utf-8", "cp1251", "windows-1251", "latin-1"):
        try:
            text = path.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    if not text:
        return ADDRESS_POOL.copy()

    addresses: list[str] = []
    seen: set[str] = set()
    reader = csv.DictReader(text.splitlines())
    if reader.fieldnames:
        normalized_map = {str(name).strip().lower(): name for name in reader.fieldnames if name}
        pickup_key = normalized_map.get("pickup_address")
        dropoff_key = normalized_map.get("dropoff_address")
        if pickup_key or dropoff_key:
            for row in reader:
                for key in (pickup_key, dropoff_key):
                    if not key:
                        continue
                    cleaned = _clean_address_cell(row.get(key))
                    if cleaned and cleaned not in seen:
                        seen.add(cleaned)
                        addresses.append(cleaned)

    if not addresses:
        for line in text.splitlines():
            parts = [part.strip() for part in line.split(";")]
            for part in parts:
                cleaned = _clean_address_cell(part)
                if cleaned and cleaned not in seen:
                    seen.add(cleaned)
                    addresses.append(cleaned)

    return addresses if addresses else ADDRESS_POOL.copy()


def _random_ua_latlng(rng: random.Random) -> tuple[float, float]:
    return (
        round(rng.uniform(UKRAINE_BOUNDS["min_lat"], UKRAINE_BOUNDS["max_lat"]), 6),
        round(rng.uniform(UKRAINE_BOUNDS["min_lng"], UKRAINE_BOUNDS["max_lng"]), 6),
    )


def _random_lviv_latlng(rng: random.Random) -> tuple[float, float]:
    return (
        round(rng.uniform(LVIV_BOUNDS["min_lat"], LVIV_BOUNDS["max_lat"]), 6),
        round(rng.uniform(LVIV_BOUNDS["min_lng"], LVIV_BOUNDS["max_lng"]), 6),
    )


def _distinct_addresses(addresses: list[str], index: int) -> tuple[str, str]:
    if not addresses:
        return "вул. Городоцька, 25", "вул. Кульпарківська, 95"
    if len(addresses) == 1:
        return addresses[0], f"{addresses[0]} (інша точка)"
    pickup = addresses[index % len(addresses)]
    dropoff = addresses[(index + 1) % len(addresses)]
    if pickup == dropoff:
        dropoff = addresses[(index + 2) % len(addresses)]
    if pickup == dropoff:
        dropoff = f"{dropoff} (інша точка)"
    return pickup, dropoff


def _estimate_cost(distance_km: float, minutes: int, comfort_class: CarComfortClass) -> float:
    base, per_km, per_min, _ = TARIFF_PRESETS[comfort_class]
    return round(base + distance_km * per_km + minutes * per_min, 2)


def generate_seed_payload(records_per_table: int = DEFAULT_SEED_RECORDS, random_seed: int = DEFAULT_RANDOM_SEED) -> dict[str, Any]:
    records_per_table = max(1, int(records_per_table))
    rng = random.Random(random_seed)

    meta = SeedMeta(
        generated_at=_utc_now().isoformat(),
        records_per_table=records_per_table,
        random_seed=random_seed,
        admin_email=DEFAULT_ADMIN_EMAIL,
    )

    users: list[dict[str, Any]] = []
    clients: list[dict[str, Any]] = []
    drivers: list[dict[str, Any]] = []
    cars: list[dict[str, Any]] = []
    driver_applications: list[dict[str, Any]] = []
    driver_class_applications: list[dict[str, Any]] = []
    orders: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    auth_tokens: list[dict[str, Any]] = []

    users.append(
        {
            "key": "user_admin_0001",
            "username": DEFAULT_ADMIN_EMAIL,
            "hashed_password": hash_password(DEFAULT_ADMIN_PASSWORD),
            "first_name": "Admin",
            "last_name": "Taxi",
            "phone": "+380500000001",
            "role": UserRole.ADMIN.value,
            "is_blocked": False,
        }
    )

    client_user_keys: list[str] = []
    driver_user_keys: list[str] = []

    for idx in range(records_per_table):
        first_name, last_name = _random_name(rng)
        key = f"user_client_{idx + 1:04d}"
        client_user_keys.append(key)
        users.append(
            {
                "key": key,
                "username": f"client{idx + 1:04d}@seed.local",
                "hashed_password": hash_password("seed12345"),
                "first_name": first_name,
                "last_name": last_name,
                "phone": _unique_phone("67", idx),
                "role": UserRole.CLIENT.value,
                "is_blocked": False,
            }
        )

    for idx in range(records_per_table):
        first_name, last_name = _random_name(rng)
        key = f"user_driver_{idx + 1:04d}"
        driver_user_keys.append(key)
        users.append(
            {
                "key": key,
                "username": f"driver{idx + 1:04d}@seed.local",
                "hashed_password": hash_password("seed12345"),
                "first_name": first_name,
                "last_name": last_name,
                "phone": _unique_phone("50", idx),
                "role": UserRole.DRIVER.value,
                "is_blocked": False,
            }
        )

    for idx, user_key in enumerate(client_user_keys):
        clients.append(
            {
                "user_key": user_key,
                "phone": _unique_phone("67", idx),
                "balance": round(rng.uniform(0, 2500), 2),
            }
        )

    for idx in range(records_per_table):
        car_class = _random_car_class(rng)
        make, model = rng.choice(CAR_MAKES_MODELS[car_class])
        cars.append(
            {
                "key": f"car_{idx + 1:04d}",
                "plate_number": _build_plate(idx + 1),
                "make": make,
                "model": model,
                "production_year": rng.randint(2012, 2024),
                "engine": rng.choice(["1.6 бензин", "2.0 дизель", "1.8 гібрид", "3.0 бензин"]),
                "transmission": rng.choice(["automatic", "manual"]),
                "color": rng.choice(["White", "Black", "Silver", "Blue", "Gray"]),
                "comfort_class": car_class.value,
                "technical_status": "good",
                "is_active": True,
            }
        )

    driver_keys: list[str] = []
    driver_car_keys: list[str] = []
    for idx, user_key in enumerate(driver_user_keys):
        car_key = cars[idx]["key"]
        driver_key = f"driver_{idx + 1:04d}"
        driver_keys.append(driver_key)
        driver_car_keys.append(car_key)
        car_class = CarComfortClass(cars[idx]["comfort_class"])
        status = rng.choices(
            [DriverStatus.FREE.value, DriverStatus.BREAK.value, DriverStatus.INACTIVE.value],
            weights=[0.6, 0.25, 0.15],
            k=1,
        )[0]
        drivers.append(
            {
                "key": driver_key,
                "user_key": user_key,
                "license_number": f"DRV-{idx + 1:06d}",
                "rating": round(rng.uniform(4.1, 5.0), 2),
                "status": status,
                "car_key": car_key,
                "approved_car_class": car_class.value,
                "requested_car_class": None,
                "uses_own_car": False,
                "current_lat": round(rng.uniform(49.77, 49.9), 6),
                "current_lng": round(rng.uniform(23.9, 24.1), 6),
            }
        )

    for idx in range(records_per_table):
        first_name, last_name = _random_name(rng)
        status = rng.choices(
            [
                DriverApplicationStatus.PENDING.value,
                DriverApplicationStatus.APPROVED.value,
                DriverApplicationStatus.REJECTED.value,
            ],
            weights=[0.3, 0.45, 0.25],
            k=1,
        )[0]
        reviewed_at = _as_iso(_utc_now() - timedelta(days=rng.randint(1, 120))) if status != "pending" else None
        driver_applications.append(
            {
                "first_name": first_name,
                "last_name": last_name,
                "phone": _unique_phone("66", idx),
                "email": f"application{idx + 1:04d}@seed.local",
                "hashed_password": hash_password("seed12345"),
                "license_series": rng.choice(["AA", "AB", "AC", "AE"]),
                "license_number": f"APP-{idx + 1:06d}",
                "status": status,
                "reviewer_key": "user_admin_0001" if status != "pending" else None,
                "reviewed_at": reviewed_at,
                "review_note": "Схвалено адміністратором" if status == "approved" else ("Відхилено" if status == "rejected" else None),
            }
        )

    for idx in range(records_per_table):
        driver_key = driver_keys[idx % len(driver_keys)]
        requested_class = rng.choice(
            [CarComfortClass.STANDARD.value, CarComfortClass.COMFORT.value, CarComfortClass.BUSINESS.value]
        )
        status = rng.choices(
            [
                DriverClassApplicationStatus.PENDING.value,
                DriverClassApplicationStatus.APPROVED.value,
                DriverClassApplicationStatus.REJECTED.value,
            ],
            weights=[0.25, 0.5, 0.25],
            k=1,
        )[0]
        reviewed_at = _as_iso(_utc_now() - timedelta(days=rng.randint(1, 90))) if status != "pending" else None
        own_make, own_model = rng.choice(CAR_MAKES_MODELS[CarComfortClass(requested_class)])
        driver_class_applications.append(
            {
                "driver_key": driver_key,
                "requested_car_class": requested_class,
                "own_car_make": own_make,
                "own_car_model": own_model,
                "own_car_year": rng.randint(2012, 2024),
                "own_car_plate": f"OWN-{idx + 1:04d}",
                "own_car_engine": rng.choice(["1.6 бензин", "2.0 дизель", "2.5 бензин"]),
                "own_car_transmission": rng.choice(["automatic", "manual"]),
                "status": status,
                "reviewer_key": "user_admin_0001" if status != "pending" else None,
                "reviewed_at": reviewed_at,
                "review_note": "Схвалено" if status == "approved" else ("Відхилено" if status == "rejected" else None),
            }
        )

    client_order_seq: dict[str, int] = {key: 0 for key in client_user_keys}
    for idx in range(records_per_table):
        order_key = f"order_{idx + 1:05d}"
        client_key = rng.choice(client_user_keys)
        driver_idx = rng.randint(0, len(driver_keys) - 1)
        driver_key = driver_keys[driver_idx]
        car_key = driver_car_keys[driver_idx]
        requested_class = _random_car_class(rng).value
        pickup_address = rng.choice(ADDRESS_POOL)
        dropoff_address = rng.choice([addr for addr in ADDRESS_POOL if addr != pickup_address])
        distance_km = round(rng.uniform(0.8, 18.5), 3)
        estimated_minutes = max(4, int(distance_km * rng.uniform(2.2, 3.5)))
        estimated_cost = _estimate_cost(distance_km, estimated_minutes, CarComfortClass(requested_class))
        final_cost = round(estimated_cost * rng.uniform(0.95, 1.25), 2)
        created_at = _utc_now() - timedelta(days=rng.randint(0, 180), hours=rng.randint(0, 23))
        client_order_seq[client_key] += 1

        orders.append(
            {
                "key": order_key,
                "client_key": client_key,
                "driver_key": driver_key,
                "car_key": car_key,
                "requested_comfort_class": requested_class,
                "client_order_number": client_order_seq[client_key],
                "pickup_address": pickup_address,
                "dropoff_address": dropoff_address,
                "pickup_lat": round(rng.uniform(49.77, 49.9), 6),
                "pickup_lng": round(rng.uniform(23.9, 24.1), 6),
                "dropoff_lat": round(rng.uniform(49.77, 49.9), 6),
                "dropoff_lng": round(rng.uniform(23.9, 24.1), 6),
                "distance_km": distance_km,
                "estimated_minutes": estimated_minutes,
                "estimated_cost": estimated_cost,
                "driver_payout_ratio": round(rng.uniform(0.65, 0.8), 2),
                "driver_payout": round(final_cost * 0.75, 2),
                "final_cost": final_cost,
                "status": OrderStatus.COMPLETED.value,
                "created_at": _as_iso(created_at),
                "updated_at": _as_iso(created_at + timedelta(minutes=rng.randint(5, 45))),
            }
        )

    for idx, order in enumerate(orders):
        reviews.append(
            {
                "order_key": order["key"],
                "client_key": order["client_key"],
                "driver_key": order["driver_key"],
                "rating": rng.randint(3, 5),
                "comment": rng.choice(ORDER_REVIEW_COMMENTS),
                "created_at": _as_iso(_utc_now() - timedelta(days=rng.randint(0, 180))),
            }
        )

    for idx in range(records_per_table):
        user_key = rng.choice([item["key"] for item in users])
        token_type = rng.choice([TokenType.ACCESS.value, TokenType.REFRESH.value])
        auth_tokens.append(
            {
                "user_key": user_key,
                "jti": uuid.uuid4().hex,
                "token_type": token_type,
                "expires_at": _as_iso(_utc_now() + timedelta(days=rng.randint(1, 30))),
                "is_revoked": False,
            }
        )

    payload = {
        "meta": asdict(meta),
        "users": users,
        "clients": clients,
        "drivers": drivers,
        "cars": cars,
        "driver_applications": driver_applications,
        "driver_class_applications": driver_class_applications,
        "orders": orders,
        "reviews": reviews,
        "auth_tokens": auth_tokens,
        "tariffs": [
            {
                "comfort_class": key.value,
                "base_fare": values[0],
                "price_per_km": values[1],
                "price_per_minute": values[2],
                "night_multiplier": values[3],
            }
            for key, values in TARIFF_PRESETS.items()
        ],
    }

    payload["counts"] = {
        "users": len(users),
        "clients": len(clients),
        "drivers": len(drivers),
        "cars": len(cars),
        "driver_applications": len(driver_applications),
        "driver_class_applications": len(driver_class_applications),
        "orders": len(orders),
        "reviews": len(reviews),
        "auth_tokens": len(auth_tokens),
        "tariffs": len(payload["tariffs"]),
    }

    return payload


def write_seed_file(payload: dict[str, Any], output_path: Path = DEFAULT_BULK_SEED_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def generate_seed_file(
    output_path: Path = DEFAULT_BULK_SEED_PATH,
    records_per_table: int = DEFAULT_SEED_RECORDS,
    random_seed: int = DEFAULT_RANDOM_SEED,
) -> Path:
    payload = generate_seed_payload(records_per_table=records_per_table, random_seed=random_seed)
    return write_seed_file(payload, output_path)


def load_seed_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _has_only_default_seed_data(db: Session) -> bool:
    default_usernames = {item["username"] for item in PREDEFINED_USERS}
    existing_usernames = set(db.scalars(select(User.username)).all())
    if existing_usernames != default_usernames:
        return False

    default_clients = sum(1 for item in PREDEFINED_USERS if item["role"] == UserRole.CLIENT)
    default_drivers = sum(1 for item in PREDEFINED_USERS if item["role"] == UserRole.DRIVER)
    default_cars = len(_fleet_definitions())

    client_count = db.scalar(select(func.count(Client.id))) or 0
    driver_count = db.scalar(select(func.count(Driver.id))) or 0
    car_count = db.scalar(select(func.count(Car.id))) or 0
    order_count = db.scalar(select(func.count(Order.id))) or 0
    review_count = db.scalar(select(func.count(Review.id))) or 0
    driver_app_count = db.scalar(select(func.count(DriverApplication.id))) or 0
    driver_class_app_count = db.scalar(select(func.count(DriverClassApplication.id))) or 0

    if order_count or review_count or driver_app_count or driver_class_app_count:
        return False

    return client_count == default_clients and driver_count == default_drivers and car_count == default_cars


def _purge_default_seed_data(db: Session) -> None:
    default_driver_emails = [item["username"] for item in PREDEFINED_USERS if item["role"] == UserRole.DRIVER]
    default_client_emails = [item["username"] for item in PREDEFINED_USERS if item["role"] == UserRole.CLIENT]
    target_emails = default_driver_emails + default_client_emails

    if not target_emails:
        return

    user_ids = list(db.scalars(select(User.id).where(User.username.in_(target_emails))).all())
    if user_ids:
        db.execute(delete(AuthToken).where(AuthToken.user_id.in_(user_ids)))
        db.execute(delete(Driver).where(Driver.user_id.in_(user_ids)))
        db.execute(delete(Client).where(Client.user_id.in_(user_ids)))
        db.execute(delete(User).where(User.id.in_(user_ids)))

    db.execute(delete(Car))
    db.execute(delete(Tariff))
    db.commit()


def _ensure_empty(db: Session) -> None:
    if _has_only_default_seed_data(db):
        _purge_default_seed_data(db)
        return

    tables = {
        "users": User,
        "clients": Client,
        "drivers": Driver,
        "cars": Car,
        "orders": Order,
        "reviews": Review,
    }
    not_empty = [name for name, model in tables.items() if (db.scalar(select(func.count(model.id))) or 0) > 0]
    if not_empty:
        raise ValueError("Database is not empty. Clear it before importing seed data.")


def import_seed_payload(db: Session, payload: dict[str, Any], *, require_empty: bool = True) -> SeedSummary:
    if require_empty:
        _ensure_empty(db)

    summary = SeedSummary()
    users_map: dict[str, int] = {}
    client_map: dict[str, int] = {}
    car_map: dict[str, int] = {}
    driver_map: dict[str, int] = {}
    order_map: dict[str, int] = {}

    try:
        for item in payload.get("users", []):
            user = User(
                username=item["username"],
                hashed_password=item["hashed_password"],
                first_name=item.get("first_name", ""),
                last_name=item.get("last_name", ""),
                phone=item.get("phone", ""),
                role=UserRole(item["role"]),
                is_blocked=bool(item.get("is_blocked", False)),
            )
            db.add(user)
            db.flush()
            users_map[item["key"]] = user.id
            summary.users += 1

        for item in payload.get("clients", []):
            client = Client(
                user_id=users_map[item["user_key"]],
                phone=item.get("phone", ""),
                balance=item.get("balance", 0),
            )
            db.add(client)
            db.flush()
            client_map[item["user_key"]] = client.id
            summary.clients += 1

        for item in payload.get("cars", []):
            car = Car(
                plate_number=item["plate_number"],
                make=item.get("make", ""),
                model=item.get("model", ""),
                production_year=item.get("production_year", 2020),
                engine=item.get("engine", ""),
                transmission=item.get("transmission", "automatic"),
                color=item.get("color", ""),
                comfort_class=CarComfortClass(item["comfort_class"]),
                technical_status=item.get("technical_status", "good"),
                is_active=bool(item.get("is_active", True)),
            )
            db.add(car)
            db.flush()
            car_map[item["key"]] = car.id
            summary.cars += 1

        for item in payload.get("drivers", []):
            driver = Driver(
                user_id=users_map[item["user_key"]],
                license_number=item["license_number"],
                rating=item.get("rating", 5.0),
                status=DriverStatus(item.get("status", DriverStatus.FREE.value)),
                car_id=car_map.get(item.get("car_key")) if item.get("car_key") else None,
                approved_car_class=CarComfortClass(item.get("approved_car_class", CarComfortClass.ECONOMY.value)),
                requested_car_class=CarComfortClass(item["requested_car_class"]) if item.get("requested_car_class") else None,
                uses_own_car=bool(item.get("uses_own_car", False)),
                own_car_make=item.get("own_car_make"),
                own_car_model=item.get("own_car_model"),
                own_car_year=item.get("own_car_year"),
                own_car_plate=item.get("own_car_plate"),
                own_car_engine=item.get("own_car_engine"),
                own_car_transmission=item.get("own_car_transmission"),
                current_lat=item.get("current_lat"),
                current_lng=item.get("current_lng"),
            )
            db.add(driver)
            db.flush()
            driver_map[item["key"]] = driver.id
            summary.drivers += 1

        for item in payload.get("tariffs", []):
            comfort_class = CarComfortClass(item["comfort_class"])
            existing = db.scalar(select(Tariff).where(Tariff.comfort_class == comfort_class))
            if existing:
                continue
            db.add(
                Tariff(
                    comfort_class=comfort_class,
                    base_fare=item["base_fare"],
                    price_per_km=item["price_per_km"],
                    price_per_minute=item["price_per_minute"],
                    night_multiplier=item.get("night_multiplier", 1.0),
                    is_active=True,
                )
            )
            summary.tariffs += 1

        if summary.tariffs == 0:
            seed_default_tariffs(db)
            summary.tariffs = len(TARIFF_PRESETS)

        for item in payload.get("driver_applications", []):
            application = DriverApplication(
                first_name=item["first_name"],
                last_name=item["last_name"],
                phone=item["phone"],
                email=item["email"],
                hashed_password=item["hashed_password"],
                license_series=item["license_series"],
                license_number=item["license_number"],
                status=DriverApplicationStatus(item["status"]),
                reviewed_by=users_map.get(item.get("reviewer_key")) if item.get("reviewer_key") else None,
                reviewed_at=_parse_iso(item.get("reviewed_at")),
                review_note=item.get("review_note"),
            )
            db.add(application)
            summary.driver_applications += 1

        for item in payload.get("driver_class_applications", []):
            application = DriverClassApplication(
                driver_id=driver_map[item["driver_key"]],
                requested_car_class=CarComfortClass(item["requested_car_class"]),
                own_car_make=item["own_car_make"],
                own_car_model=item["own_car_model"],
                own_car_year=item["own_car_year"],
                own_car_plate=item["own_car_plate"],
                own_car_engine=item["own_car_engine"],
                own_car_transmission=item["own_car_transmission"],
                status=DriverClassApplicationStatus(item["status"]),
                reviewed_by=users_map.get(item.get("reviewer_key")) if item.get("reviewer_key") else None,
                reviewed_at=_parse_iso(item.get("reviewed_at")),
                review_note=item.get("review_note"),
            )
            db.add(application)
            summary.driver_class_applications += 1

        for item in payload.get("orders", []):
            order = Order(
                client_id=client_map[item["client_key"]],
                driver_id=driver_map.get(item.get("driver_key")) if item.get("driver_key") else None,
                car_id=car_map.get(item.get("car_key")) if item.get("car_key") else None,
                requested_comfort_class=CarComfortClass(item["requested_comfort_class"]),
                client_order_number=item.get("client_order_number", 1),
                pickup_address=item["pickup_address"],
                dropoff_address=item["dropoff_address"],
                pickup_lat=item["pickup_lat"],
                pickup_lng=item["pickup_lng"],
                dropoff_lat=item["dropoff_lat"],
                dropoff_lng=item["dropoff_lng"],
                distance_km=item.get("distance_km", 1.0),
                estimated_minutes=item.get("estimated_minutes", 10),
                estimated_cost=item.get("estimated_cost", 100),
                driver_payout=item.get("driver_payout"),
                driver_payout_ratio=item.get("driver_payout_ratio"),
                final_cost=item.get("final_cost"),
                status=OrderStatus(item.get("status", OrderStatus.PENDING.value)),
                created_at=_parse_iso(item.get("created_at")) or _utc_now(),
                updated_at=_parse_iso(item.get("updated_at")) or _utc_now(),
            )
            db.add(order)
            db.flush()
            order_map[item["key"]] = order.id
            summary.orders += 1

        for item in payload.get("reviews", []):
            review = Review(
                order_id=order_map[item["order_key"]],
                client_id=client_map[item["client_key"]],
                driver_id=driver_map[item["driver_key"]],
                rating=item["rating"],
                comment=item.get("comment"),
                created_at=_parse_iso(item.get("created_at")) or _utc_now(),
            )
            db.add(review)
            summary.reviews += 1

        for item in payload.get("auth_tokens", []):
            token = AuthToken(
                user_id=users_map[item["user_key"]],
                jti=item["jti"],
                token_type=TokenType(item["token_type"]),
                expires_at=_parse_iso(item["expires_at"]) or (_utc_now() + timedelta(days=7)),
                is_revoked=bool(item.get("is_revoked", False)),
            )
            db.add(token)
            summary.auth_tokens += 1

        db.commit()
    except Exception:
        db.rollback()
        raise

    return summary


def import_seed_file(db: Session, path: Path = DEFAULT_BULK_SEED_PATH, *, require_empty: bool = True) -> SeedSummary:
    payload = load_seed_file(path)
    return import_seed_payload(db, payload, require_empty=require_empty)


def ensure_minimum_dataset(
    db: Session,
    *,
    target_records: int = DEFAULT_SEED_RECORDS,
    address_csv_path: Path | None = None,
    random_seed: int = DEFAULT_RANDOM_SEED,
) -> SeedSummary:
    summary = SeedSummary()
    rng = random.Random(random_seed)
    addresses = load_addresses_from_csv(address_csv_path)

    users = list(db.scalars(select(User).order_by(User.id.asc())).all())
    existing_usernames = {user.username for user in users}
    existing_phones = {user.phone for user in users if user.phone}
    existing_licenses = {license_number for license_number in db.scalars(select(Driver.license_number)).all() if license_number}
    existing_plates = {plate for plate in db.scalars(select(Car.plate_number)).all() if plate}

    seed_default_tariffs(db)

    clients = list(db.scalars(select(Client).order_by(Client.id.asc())).all())
    while len(clients) < target_records:
        first_name, last_name = _random_name(rng)
        user = User(
            username=f"client.auto.{uuid.uuid4().hex[:10]}@taxi.local",
            hashed_password=hash_password("seed12345"),
            first_name=first_name,
            last_name=last_name,
            phone=_unique_phone("67", len(existing_phones) + len(clients)),
            role=UserRole.CLIENT,
        )
        if user.username in existing_usernames or user.phone in existing_phones:
            continue
        db.add(user)
        db.flush()
        client = Client(user_id=user.id, phone=user.phone, balance=round(rng.uniform(0, 3000), 2))
        db.add(client)
        users.append(user)
        clients.append(client)
        existing_usernames.add(user.username)
        existing_phones.add(user.phone)
        summary.users += 1
        summary.clients += 1

    cars = list(db.scalars(select(Car).order_by(Car.id.asc())).all())
    while len(cars) < target_records:
        comfort_class = _random_car_class(rng)
        make, model = rng.choice(CAR_MAKES_MODELS[comfort_class])
        plate = _build_plate(len(cars) + 1)
        if plate in existing_plates:
            plate = f"UA{rng.randint(1000, 9999)}{rng.choice(['AA', 'AB', 'AC', 'AE'])}"
        if plate in existing_plates:
            continue
        car = Car(
            plate_number=plate,
            make=make,
            model=model,
            production_year=rng.randint(2012, 2024),
            engine=rng.choice(["1.6 бензин", "2.0 дизель", "1.8 гібрид", "3.0 бензин"]),
            transmission=rng.choice(["automatic", "manual"]),
            color=rng.choice(["White", "Black", "Silver", "Blue", "Gray"]),
            comfort_class=comfort_class,
            technical_status="good",
            is_active=True,
        )
        db.add(car)
        db.flush()
        cars.append(car)
        existing_plates.add(plate)
        summary.cars += 1

    drivers = list(db.scalars(select(Driver).order_by(Driver.id.asc())).all())
    car_idx = 0
    while len(drivers) < target_records:
        first_name, last_name = _random_name(rng)
        username = f"driver.auto.{uuid.uuid4().hex[:10]}@taxi.local"
        phone = _unique_phone("50", len(existing_phones) + len(drivers))
        if username in existing_usernames or phone in existing_phones:
            continue
        user = User(
            username=username,
            hashed_password=hash_password("seed12345"),
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role=UserRole.DRIVER,
        )
        db.add(user)
        db.flush()
        lat, lng = _random_ua_latlng(rng)
        selected_car = cars[car_idx % len(cars)]
        car_idx += 1
        license_number = f"AUTO-{uuid.uuid4().hex[:8].upper()}"
        if license_number in existing_licenses:
            continue
        driver = Driver(
            user_id=user.id,
            license_number=license_number,
            rating=round(rng.uniform(4.2, 5.0), 2),
            status=DriverStatus.FREE,
            car_id=selected_car.id,
            approved_car_class=selected_car.comfort_class,
            uses_own_car=False,
            current_lat=lat,
            current_lng=lng,
        )
        db.add(driver)
        drivers.append(driver)
        users.append(user)
        existing_usernames.add(username)
        existing_phones.add(phone)
        existing_licenses.add(license_number)
        summary.users += 1
        summary.drivers += 1

    db.flush()

    # Assign free cars to drivers to keep the fleet occupied.
    occupied_car_ids = {driver.car_id for driver in drivers if driver.car_id is not None}
    available_cars = [car for car in cars if car.id not in occupied_car_ids]
    for driver in drivers:
        if driver.car_id is None and available_cars:
            car = available_cars.pop()
            driver.car_id = car.id
            driver.uses_own_car = False
            driver.approved_car_class = car.comfort_class
            driver.status = DriverStatus.ON_ORDER

    driver_apps_count = db.scalar(select(func.count(DriverApplication.id))) or 0
    while driver_apps_count < target_records:
        email = f"application.auto.{uuid.uuid4().hex[:10]}@taxi.local"
        status = rng.choices(
            [DriverApplicationStatus.PENDING, DriverApplicationStatus.APPROVED, DriverApplicationStatus.REJECTED],
            weights=[0.25, 0.5, 0.25],
            k=1,
        )[0]
        reviewed_at = _utc_now() - timedelta(days=rng.randint(1, 90)) if status != DriverApplicationStatus.PENDING else None
        app = DriverApplication(
            first_name=rng.choice(NAMES),
            last_name=rng.choice(SURNAMES),
            phone=_unique_phone("66", driver_apps_count),
            email=email,
            hashed_password=hash_password("seed12345"),
            license_series=rng.choice(["AA", "AB", "AC", "AE"]),
            license_number=f"APP-AUTO-{uuid.uuid4().hex[:8].upper()}",
            status=status,
            reviewed_at=reviewed_at,
            review_note="Auto-generated review note" if status != DriverApplicationStatus.PENDING else None,
        )
        db.add(app)
        driver_apps_count += 1
        summary.driver_applications += 1

    class_apps_count = db.scalar(select(func.count(DriverClassApplication.id))) or 0
    while class_apps_count < target_records:
        driver = drivers[class_apps_count % len(drivers)]
        requested_class = rng.choice([CarComfortClass.STANDARD, CarComfortClass.COMFORT, CarComfortClass.BUSINESS])
        status = rng.choices(
            [DriverClassApplicationStatus.PENDING, DriverClassApplicationStatus.APPROVED, DriverClassApplicationStatus.REJECTED],
            weights=[0.2, 0.55, 0.25],
            k=1,
        )[0]
        make, model = rng.choice(CAR_MAKES_MODELS[requested_class])
        application = DriverClassApplication(
            driver_id=driver.id,
            requested_car_class=requested_class,
            own_car_make=make,
            own_car_model=model,
            own_car_year=rng.randint(2012, 2024),
            own_car_plate=f"OWN-AUTO-{uuid.uuid4().hex[:6].upper()}",
            own_car_engine=rng.choice(["1.6 бензин", "2.0 дизель", "2.5 бензин"]),
            own_car_transmission=rng.choice(["automatic", "manual"]),
            status=status,
            reviewed_at=_utc_now() - timedelta(days=rng.randint(1, 120))
            if status != DriverClassApplicationStatus.PENDING
            else None,
            review_note="Auto-generated class review" if status != DriverClassApplicationStatus.PENDING else None,
        )
        db.add(application)
        class_apps_count += 1
        summary.driver_class_applications += 1

    order_count = db.scalar(select(func.count(Order.id))) or 0
    per_client_seq = {
        int(client_id): int(max_seq or 0)
        for client_id, max_seq in db.execute(
            select(Order.client_id, func.max(Order.client_order_number)).group_by(Order.client_id)
        ).all()
    }
    while order_count < target_records:
        client = clients[order_count % len(clients)]
        driver = drivers[order_count % len(drivers)]
        comfort_class = driver.approved_car_class or _random_car_class(rng)
        pickup_address, dropoff_address = _distinct_addresses(addresses, order_count)
        pickup_lat, pickup_lng = _random_lviv_latlng(rng)
        dropoff_lat, dropoff_lng = _random_lviv_latlng(rng)
        if pickup_lat == dropoff_lat and pickup_lng == dropoff_lng:
            dropoff_lat, dropoff_lng = _random_lviv_latlng(rng)
        distance_km = round(max(0.3, haversine_km(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)), 3)
        estimated_minutes = max(3, int(distance_km * rng.uniform(2.0, 3.8)))
        estimated_cost = _estimate_cost(distance_km, estimated_minutes, comfort_class)
        final_cost = round(estimated_cost * rng.uniform(0.95, 1.25), 2)
        payout_ratio = round(rng.uniform(0.65, 0.8), 2)
        created_at = _utc_now() - timedelta(days=rng.randint(0, 365), minutes=rng.randint(0, 60 * 24))
        per_client_seq[client.id] = per_client_seq.get(client.id, 0) + 1
        status = rng.choices(
            [OrderStatus.COMPLETED, OrderStatus.CANCELLED, OrderStatus.ASSIGNED, OrderStatus.DRIVER_ARRIVED, OrderStatus.IN_PROGRESS],
            weights=[0.7, 0.12, 0.08, 0.05, 0.05],
            k=1,
        )[0]
        order = Order(
            client_id=client.id,
            driver_id=driver.id if status != OrderStatus.CANCELLED else None,
            car_id=driver.car_id if status != OrderStatus.CANCELLED else None,
            requested_comfort_class=comfort_class,
            client_order_number=per_client_seq[client.id],
            pickup_address=pickup_address,
            dropoff_address=dropoff_address,
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            dropoff_lat=dropoff_lat,
            dropoff_lng=dropoff_lng,
            distance_km=distance_km,
            estimated_minutes=estimated_minutes,
            estimated_cost=estimated_cost,
            driver_payout=round(final_cost * payout_ratio, 2) if status != OrderStatus.CANCELLED else None,
            driver_payout_ratio=payout_ratio if status != OrderStatus.CANCELLED else None,
            final_cost=final_cost if status in {OrderStatus.COMPLETED, OrderStatus.IN_PROGRESS, OrderStatus.DRIVER_ARRIVED} else None,
            status=status,
            created_at=created_at,
            updated_at=created_at + timedelta(minutes=estimated_minutes),
        )
        db.add(order)
        order_count += 1
        summary.orders += 1

    # Ensure dashboard periods (day/week/month/year) are always populated.
    def _ensure_recent_completed_orders() -> None:
        now = _utc_now()
        periods = {
            "day": now.replace(hour=0, minute=0, second=0, microsecond=0),
            "week": (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0),
            "month": now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
            "year": now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0),
        }
        address_pool = addresses if len(addresses) >= 2 else ADDRESS_POOL

        for start_dt in periods.values():
            completed_in_period = int(
                db.scalar(
                    select(func.count(Order.id)).where(
                        Order.status == OrderStatus.COMPLETED,
                        Order.created_at >= start_dt,
                    )
                )
                or 0
            )
            needed = max(0, 5 - completed_in_period)
            for _ in range(needed):
                client = clients[rng.randrange(len(clients))]
                driver = drivers[rng.randrange(len(drivers))]
                comfort_class = driver.approved_car_class or _random_car_class(rng)
                pickup_address, dropoff_address = _distinct_addresses(address_pool, rng.randrange(100000))
                pickup_lat, pickup_lng = _random_lviv_latlng(rng)
                dropoff_lat, dropoff_lng = _random_lviv_latlng(rng)
                if pickup_lat == dropoff_lat and pickup_lng == dropoff_lng:
                    dropoff_lat, dropoff_lng = _random_lviv_latlng(rng)
                distance_km = round(max(0.4, haversine_km(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)), 3)
                estimated_minutes = max(4, int(distance_km * rng.uniform(2.0, 3.5)))
                estimated_cost = _estimate_cost(distance_km, estimated_minutes, comfort_class)
                final_cost = round(estimated_cost * rng.uniform(1.0, 1.22), 2)
                payout_ratio = round(rng.uniform(0.65, 0.8), 2)
                created_at = start_dt + timedelta(minutes=rng.randint(1, 23 * 60))
                per_client_seq[client.id] = per_client_seq.get(client.id, 0) + 1
                db.add(
                    Order(
                        client_id=client.id,
                        driver_id=driver.id,
                        car_id=driver.car_id,
                        requested_comfort_class=comfort_class,
                        client_order_number=per_client_seq[client.id],
                        pickup_address=pickup_address,
                        dropoff_address=dropoff_address,
                        pickup_lat=pickup_lat,
                        pickup_lng=pickup_lng,
                        dropoff_lat=dropoff_lat,
                        dropoff_lng=dropoff_lng,
                        distance_km=distance_km,
                        estimated_minutes=estimated_minutes,
                        estimated_cost=estimated_cost,
                        driver_payout=round(final_cost * payout_ratio, 2),
                        driver_payout_ratio=payout_ratio,
                        final_cost=final_cost,
                        status=OrderStatus.COMPLETED,
                        created_at=created_at,
                        updated_at=created_at + timedelta(minutes=estimated_minutes),
                    )
                )
                summary.orders += 1

    _ensure_recent_completed_orders()

    db.flush()
    review_count = db.scalar(select(func.count(Review.id))) or 0
    reviewed_order_ids = {order_id for order_id in db.scalars(select(Review.order_id)).all()}
    completed_orders = list(db.scalars(select(Order).where(Order.status == OrderStatus.COMPLETED)).all())
    idx = 0
    while review_count < target_records and completed_orders:
        order = completed_orders[idx % len(completed_orders)]
        idx += 1
        if order.id in reviewed_order_ids or order.driver_id is None:
            continue
        review = Review(
            order_id=order.id,
            client_id=order.client_id,
            driver_id=order.driver_id,
            rating=rng.randint(3, 5),
            comment=rng.choice(ORDER_REVIEW_COMMENTS),
            created_at=order.updated_at + timedelta(minutes=rng.randint(5, 240)),
        )
        db.add(review)
        reviewed_order_ids.add(order.id)
        review_count += 1
        summary.reviews += 1

    token_count = db.scalar(select(func.count(AuthToken.id))) or 0
    while token_count < target_records:
        user = users[token_count % len(users)]
        token = AuthToken(
            user_id=user.id,
            jti=uuid.uuid4().hex,
            token_type=TokenType.ACCESS if token_count % 2 == 0 else TokenType.REFRESH,
            expires_at=_utc_now() + timedelta(days=rng.randint(1, 30)),
            is_revoked=False,
        )
        db.add(token)
        token_count += 1
        summary.auth_tokens += 1

    db.commit()
    return summary


def _print_summary(summary: SeedSummary) -> None:
    print("Bulk seed imported")
    for key, value in summary.as_dict().items():
        print(f"- {key}: {value}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate and/or import bulk seed data (1000+ rows per table).")
    parser.add_argument("--output", type=Path, default=DEFAULT_BULK_SEED_PATH, help="Path for JSON seed file")
    parser.add_argument("--records-per-table", type=int, default=DEFAULT_SEED_RECORDS)
    parser.add_argument("--seed", type=int, default=DEFAULT_RANDOM_SEED)
    parser.add_argument("--generate", action="store_true", help="Generate seed file")
    parser.add_argument("--import", dest="do_import", action="store_true", help="Import seed file into DB")
    parser.add_argument("--allow-nonempty", action="store_true", help="Allow import when DB is not empty")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    do_generate = args.generate or not args.do_import
    do_import = args.do_import or not args.generate

    if do_generate:
        path = generate_seed_file(args.output, records_per_table=args.records_per_table, random_seed=args.seed)
        print(f"Seed file generated: {path}")

    if do_import:
        db = SessionLocal()
        try:
            summary = import_seed_file(db, args.output, require_empty=not args.allow_nonempty)
        finally:
            db.close()
        _print_summary(summary)


if __name__ == "__main__":
    main()
