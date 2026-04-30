from __future__ import annotations

import argparse
import csv
import itertools
import random
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.seed import seed_default_tariffs, seed_fleet_cars, seed_predefined_users
from app.db.session import SessionLocal
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

LVIV_BOUNDS = {
    "min_lat": 49.77,
    "max_lat": 49.9,
    "min_lng": 23.9,
    "max_lng": 24.1,
}

CAR_CLASS_RANK: dict[CarComfortClass, int] = {
    CarComfortClass.ECONOMY: 1,
    CarComfortClass.STANDARD: 2,
    CarComfortClass.COMFORT: 3,
    CarComfortClass.BUSINESS: 4,
}

NAMES = [
    "Андрій",
    "Олег",
    "Іван",
    "Максим",
    "Тарас",
    "Юрій",
    "Роман",
    "Богдан",
    "Василь",
    "Сергій",
    "Марія",
    "Оксана",
    "Ірина",
    "Наталія",
    "Софія",
    "Катерина",
    "Олена",
    "Юлія",
]

SURNAMES = [
    "Коваль",
    "Шевченко",
    "Мельник",
    "Бойко",
    "Кравець",
    "Данилюк",
    "Іванюк",
    "Гнатюк",
    "Козак",
    "Білик",
    "Левицький",
    "Савчук",
    "Гуменюк",
    "Федорів",
    "Петренко",
]

CAR_MAKES_MODELS: dict[CarComfortClass, list[tuple[str, str]]] = {
    CarComfortClass.ECONOMY: [("Dacia", "Logan"), ("Skoda", "Fabia"), ("Renault", "Symbol")],
    CarComfortClass.STANDARD: [("Toyota", "Corolla"), ("Skoda", "Octavia"), ("Kia", "Ceed")],
    CarComfortClass.COMFORT: [("Volkswagen", "Passat"), ("Toyota", "Camry"), ("Mazda", "6")],
    CarComfortClass.BUSINESS: [("BMW", "5 Series"), ("Mercedes", "E Class"), ("Audi", "A6")],
}

ORDER_REVIEW_COMMENTS = [
    "Все чудово, рекомендую.",
    "Швидко і комфортно.",
    "Водій приїхав вчасно.",
    "Поїздка пройшла добре.",
    "Дякую за сервіс.",
    "Було трохи довге очікування, але загалом ок.",
]


@dataclass(slots=True)
class TripRow:
    trip_duration: float
    distance_traveled: float
    num_of_passengers: int
    fare: float
    tip: float
    miscellaneous_fees: float
    total_fare: float
    surge_applied: bool


@dataclass(slots=True)
class SeedSummary:
    trips_loaded: int = 0
    addresses_loaded: int = 0
    created_clients: int = 0
    created_drivers: int = 0
    created_cars: int = 0
    created_orders: int = 0
    created_reviews: int = 0
    created_driver_applications: int = 0
    created_driver_class_applications: int = 0
    created_auth_tokens: int = 0


def _class_rank(car_class: CarComfortClass) -> int:
    return CAR_CLASS_RANK[car_class]


def _to_float(value: str | float | int | None, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (float, int)):
        return float(value)
    normalized = str(value).strip().replace(" ", "").replace(",", ".")
    if not normalized:
        return default
    try:
        return float(normalized)
    except ValueError:
        return default


def _to_int(value: str | float | int | None, default: int = 0) -> int:
    return int(round(_to_float(value, float(default))))


def _to_bool(value: str | float | int | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return float(value) > 0
    normalized = str(value).strip().lower()
    return normalized in {"1", "true", "yes", "y", "так", "t"}


def _normalize_duration_minutes(raw_duration: float) -> int:
    if raw_duration <= 0:
        return 1
    # Для багатьох публічних датасетів duration часто в секундах.
    if raw_duration > 240:
        return max(1, int(round(raw_duration / 60)))
    return max(1, int(round(raw_duration)))


def _normalize_header(header: str) -> str:
    return re.sub(r"\s+", "", header.strip().lower())


def _read_text_with_fallback(path: Path) -> str:
    encodings = ("utf-8-sig", "utf-8", "cp1251", "windows-1251", "latin-1")
    for enc in encodings:
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def load_addresses(path: Path) -> list[str]:
    raw_text = _read_text_with_fallback(path)
    addresses: list[str] = []
    seen: set[str] = set()

    for raw_line in raw_text.splitlines():
        line = raw_line.strip().lstrip("\ufeff")
        if not line:
            continue

        line = re.sub(r"^\d+[\.)]\s*", "", line)

        if "," not in line:
            continue

        street, house = line.rsplit(",", 1)
        street = street.strip(" .")
        house = house.strip(" .")

        if not street or not re.search(r"\d", house):
            continue

        normalized = f"{street}, {house}"
        if normalized not in seen:
            seen.add(normalized)
            addresses.append(normalized)

    if addresses:
        return addresses

    # Fallback якщо файл не зчитався коректно
    return [
        "вул. Шевченка, 1",
        "вул. Городоцька, 25",
        "вул. Стрийська, 111",
        "просп. Чорновола, 45",
        "вул. Личаківська, 80",
        "вул. Наукова, 7",
        "вул. Франка, 12",
        "вул. Кульпарківська, 95",
    ]


def load_trip_rows(path: Path, limit: int | None = None) -> list[TripRow]:
    required = [
        "trip_duration",
        "distance_traveled",
        "num_of_passengers",
        "fare",
        "tip",
        "miscellaneous_fees",
        "total_fare",
        "surge_applied",
    ]

    encodings = ("utf-8-sig", "utf-8", "cp1251", "windows-1251", "latin-1")
    last_error: Exception | None = None

    for encoding in encodings:
        try:
            with path.open("r", encoding=encoding, errors="strict", newline="") as handle:
                reader = csv.reader(handle)
                first_row = next(reader, None)
                if not first_row:
                    return []

                header = [_normalize_header(item) for item in first_row]
                has_header = all(col in header for col in required)
                indexed_rows: list[TripRow] = []

                if has_header:
                    idx = {name: header.index(name) for name in required}
                    data_iter = reader
                    expected_len = len(header)
                else:
                    data_iter = itertools.chain([first_row], reader)
                    expected_len = 8

                for row in data_iter:
                    if len(row) < expected_len:
                        continue
                    if has_header:
                        indexed_rows.append(
                            TripRow(
                                trip_duration=_to_float(row[idx["trip_duration"]], 8.0),
                                distance_traveled=max(0.3, _to_float(row[idx["distance_traveled"]], 2.5)),
                                num_of_passengers=max(1, _to_int(row[idx["num_of_passengers"]], 1)),
                                fare=max(20.0, _to_float(row[idx["fare"]], 70.0)),
                                tip=max(0.0, _to_float(row[idx["tip"]], 0.0)),
                                miscellaneous_fees=max(0.0, _to_float(row[idx["miscellaneous_fees"]], 0.0)),
                                total_fare=max(25.0, _to_float(row[idx["total_fare"]], 75.0)),
                                surge_applied=_to_bool(row[idx["surge_applied"]]),
                            )
                        )
                    else:
                        indexed_rows.append(
                            TripRow(
                                trip_duration=_to_float(row[0], 8.0),
                                distance_traveled=max(0.3, _to_float(row[1], 2.5)),
                                num_of_passengers=max(1, _to_int(row[2], 1)),
                                fare=max(20.0, _to_float(row[3], 70.0)),
                                tip=max(0.0, _to_float(row[4], 0.0)),
                                miscellaneous_fees=max(0.0, _to_float(row[5], 0.0)),
                                total_fare=max(25.0, _to_float(row[6], 75.0)),
                                surge_applied=_to_bool(row[7]),
                            )
                        )

                    if limit is not None and len(indexed_rows) >= limit:
                        break

                return indexed_rows
        except UnicodeDecodeError as error:
            last_error = error
            continue

    if last_error:
        raise last_error

    return []


def _random_lat_lng(rng: random.Random) -> tuple[float, float]:
    return (
        round(rng.uniform(LVIV_BOUNDS["min_lat"], LVIV_BOUNDS["max_lat"]), 6),
        round(rng.uniform(LVIV_BOUNDS["min_lng"], LVIV_BOUNDS["max_lng"]), 6),
    )


def _infer_comfort_class(trip: TripRow, rng: random.Random) -> CarComfortClass:
    if trip.num_of_passengers >= 4 or trip.total_fare >= 650:
        return CarComfortClass.BUSINESS
    if trip.surge_applied and trip.total_fare >= 400:
        return CarComfortClass.COMFORT
    if trip.distance_traveled >= 12 or trip.total_fare >= 250:
        return CarComfortClass.STANDARD
    # Невелика випадковість, щоб розподіл був природніший
    if rng.random() < 0.1:
        return CarComfortClass.STANDARD
    return CarComfortClass.ECONOMY


def _unique_username(prefix: str, existing: set[str], rng: random.Random) -> str:
    while True:
        candidate = f"{prefix}-{rng.randint(100000, 999999)}@seed.local"
        if candidate not in existing:
            existing.add(candidate)
            return candidate


def _unique_phone(existing: set[str], rng: random.Random) -> str:
    while True:
        candidate = f"+38067{rng.randint(1000000, 9999999)}"
        if candidate not in existing:
            existing.add(candidate)
            return candidate


def _unique_license(existing: set[str], rng: random.Random) -> str:
    while True:
        candidate = f"SEED-{rng.randint(100000, 999999)}"
        if candidate not in existing:
            existing.add(candidate)
            return candidate


def _unique_plate(existing: set[str], rng: random.Random) -> str:
    letters = ["A", "B", "C", "E", "H", "I", "K", "M", "O", "P", "T", "X"]
    while True:
        candidate = (
            f"{rng.choice(letters)}{rng.choice(letters)}"
            f"{rng.randint(1000, 9999)}"
            f"{rng.choice(letters)}{rng.choice(letters)}"
        )
        if candidate not in existing:
            existing.add(candidate)
            return candidate


def _ensure_clients(db: Session, target_count: int, rng: random.Random, summary: SeedSummary) -> list[Client]:
    existing_clients = list(db.scalars(select(Client)).all())
    existing_usernames = set(db.scalars(select(User.username)).all())
    existing_phones = {phone for phone in db.scalars(select(User.phone)).all() if phone}

    for _ in range(max(0, target_count - len(existing_clients))):
        first_name = rng.choice(NAMES)
        last_name = rng.choice(SURNAMES)
        user = User(
            username=_unique_username("client", existing_usernames, rng),
            hashed_password=hash_password("seed12345"),
            first_name=first_name,
            last_name=last_name,
            phone=_unique_phone(existing_phones, rng),
            role=UserRole.CLIENT,
        )
        db.add(user)
        db.flush()

        client = Client(user_id=user.id, phone=user.phone, balance=round(rng.uniform(0, 2000), 2))
        db.add(client)
        existing_clients.append(client)
        summary.created_clients += 1

    db.commit()
    return list(db.scalars(select(Client)).all())


def _create_car(db: Session, desired_class: CarComfortClass, rng: random.Random, plate_registry: set[str]) -> Car:
    make, model = rng.choice(CAR_MAKES_MODELS[desired_class])
    car = Car(
        plate_number=_unique_plate(plate_registry, rng),
        make=make,
        model=model,
        production_year=rng.randint(2012, 2024),
        engine=rng.choice(["1.6 бензин", "2.0 дизель", "1.8 гібрид", "3.0 бензин"]),
        transmission=rng.choice(["automatic", "manual"]),
        color=rng.choice(["White", "Black", "Silver", "Blue", "Gray"]),
        comfort_class=desired_class,
        technical_status="good",
        is_active=True,
    )
    db.add(car)
    db.flush()
    return car


def _ensure_drivers(
    db: Session,
    target_count: int,
    rng: random.Random,
    summary: SeedSummary,
) -> list[Driver]:
    drivers = list(db.scalars(select(Driver)).all())
    users_by_id = {user.id: user for user in db.scalars(select(User)).all()}
    existing_usernames = {user.username for user in users_by_id.values()}
    existing_phones = {user.phone for user in users_by_id.values() if user.phone}
    existing_licenses = {lic for lic in db.scalars(select(Driver.license_number)).all() if lic}
    plate_registry = {plate for plate in db.scalars(select(Car.plate_number)).all() if plate}

    cars = list(db.scalars(select(Car).where(Car.is_active.is_(True))).all())

    for _ in range(max(0, target_count - len(drivers))):
        first_name = rng.choice(NAMES)
        last_name = rng.choice(SURNAMES)
        user = User(
            username=_unique_username("driver", existing_usernames, rng),
            hashed_password=hash_password("seed12345"),
            first_name=first_name,
            last_name=last_name,
            phone=_unique_phone(existing_phones, rng),
            role=UserRole.DRIVER,
        )
        db.add(user)
        db.flush()

        approved_class = rng.choices(
            [CarComfortClass.ECONOMY, CarComfortClass.STANDARD, CarComfortClass.COMFORT, CarComfortClass.BUSINESS],
            weights=[0.35, 0.3, 0.25, 0.1],
            k=1,
        )[0]

        eligible_cars = [
            car
            for car in cars
            if _class_rank(car.comfort_class) >= _class_rank(approved_class)
            and not db.scalar(select(Driver).where(Driver.car_id == car.id))
        ]
        if eligible_cars:
            selected_car = rng.choice(eligible_cars)
        else:
            selected_car = _create_car(db, approved_class, rng, plate_registry)
            cars.append(selected_car)
            summary.created_cars += 1

        lat, lng = _random_lat_lng(rng)
        driver = Driver(
            user_id=user.id,
            license_number=_unique_license(existing_licenses, rng),
            rating=round(rng.uniform(4.2, 5.0), 2),
            status=rng.choices(
                [DriverStatus.FREE, DriverStatus.BREAK, DriverStatus.INACTIVE],
                weights=[0.7, 0.2, 0.1],
                k=1,
            )[0],
            car_id=selected_car.id,
            approved_car_class=approved_class,
            current_lat=lat,
            current_lng=lng,
            uses_own_car=False,
        )
        db.add(driver)
        drivers.append(driver)
        summary.created_drivers += 1

    db.commit()
    return list(db.scalars(select(Driver)).all())


def _ensure_driver_applications(
    db: Session,
    target_count: int,
    admin_user: User | None,
    rng: random.Random,
    summary: SeedSummary,
) -> None:
    existing_count = db.scalar(select(func.count(DriverApplication.id))) or 0
    existing_app_emails = {email for email in db.scalars(select(DriverApplication.email)).all() if email}
    existing_licenses = {lic for lic in db.scalars(select(DriverApplication.license_number)).all() if lic}

    for _ in range(max(0, target_count - existing_count)):
        status = rng.choices(
            [
                DriverApplicationStatus.PENDING,
                DriverApplicationStatus.APPROVED,
                DriverApplicationStatus.REJECTED,
            ],
            weights=[0.3, 0.45, 0.25],
            k=1,
        )[0]

        email = _unique_username("driver-application", existing_app_emails, rng)
        license_number = _unique_license(existing_licenses, rng)

        reviewed_at = None
        reviewed_by = None
        review_note = None
        if status != DriverApplicationStatus.PENDING and admin_user:
            reviewed_by = admin_user.id
            reviewed_at = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 120))
            review_note = (
                "Схвалено адміністратором"
                if status == DriverApplicationStatus.APPROVED
                else "Відхилено: надайте повний пакет документів"
            )

        app = DriverApplication(
            first_name=rng.choice(NAMES),
            last_name=rng.choice(SURNAMES),
            phone=_unique_phone(set(), rng),
            email=email,
            hashed_password=hash_password("seed12345"),
            license_series=f"{rng.choice(['AA', 'AB', 'AC', 'AE'])}",
            license_number=license_number,
            status=status,
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at,
            review_note=review_note,
        )
        db.add(app)
        summary.created_driver_applications += 1

    db.commit()


def _ensure_driver_class_applications(
    db: Session,
    target_count: int,
    drivers: list[Driver],
    admin_user: User | None,
    rng: random.Random,
    summary: SeedSummary,
) -> None:
    existing_count = db.scalar(select(func.count(DriverClassApplication.id))) or 0
    if not drivers:
        return

    plate_registry = {plate for plate in db.scalars(select(Car.plate_number)).all() if plate}

    for _ in range(max(0, target_count - existing_count)):
        driver = rng.choice(drivers)
        requested_class = rng.choices(
            [CarComfortClass.STANDARD, CarComfortClass.COMFORT, CarComfortClass.BUSINESS],
            weights=[0.45, 0.4, 0.15],
            k=1,
        )[0]

        status = rng.choices(
            [
                DriverClassApplicationStatus.PENDING,
                DriverClassApplicationStatus.APPROVED,
                DriverClassApplicationStatus.REJECTED,
            ],
            weights=[0.25, 0.5, 0.25],
            k=1,
        )[0]

        reviewed_by = None
        reviewed_at = None
        review_note = None
        if status != DriverClassApplicationStatus.PENDING and admin_user:
            reviewed_by = admin_user.id
            reviewed_at = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 90))
            review_note = (
                "Схвалено: клас підтверджено"
                if status == DriverClassApplicationStatus.APPROVED
                else "Відхилено: оновіть фото авто і техпаспорта"
            )

        own_car_make, own_car_model = rng.choice(CAR_MAKES_MODELS[requested_class])
        own_car_plate = _unique_plate(plate_registry, rng)

        application = DriverClassApplication(
            driver_id=driver.id,
            requested_car_class=requested_class,
            own_car_make=own_car_make,
            own_car_model=own_car_model,
            own_car_year=rng.randint(2012, 2024),
            own_car_plate=own_car_plate,
            own_car_engine=rng.choice(["1.6 бензин", "2.0 дизель", "2.5 бензин"]),
            own_car_transmission=rng.choice(["automatic", "manual"]),
            status=status,
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at,
            review_note=review_note,
        )
        db.add(application)

        # Підтримуємо логіку профілю водія
        driver.requested_car_class = requested_class
        if status == DriverClassApplicationStatus.APPROVED:
            driver.approved_car_class = requested_class
            driver.status = DriverStatus.FREE
        elif status == DriverClassApplicationStatus.REJECTED:
            driver.status = DriverStatus.INACTIVE

        summary.created_driver_class_applications += 1

    db.commit()


def _ensure_auth_tokens(
    db: Session,
    users: list[User],
    target_count: int,
    rng: random.Random,
    summary: SeedSummary,
) -> None:
    existing_count = db.scalar(select(func.count(AuthToken.id))) or 0
    if not users:
        return

    for _ in range(max(0, target_count - existing_count)):
        user = rng.choice(users)
        token_type = rng.choice([TokenType.ACCESS, TokenType.REFRESH])
        expires_at = datetime.now(timezone.utc) + timedelta(days=rng.randint(1, 30))

        token = AuthToken(
            user_id=user.id,
            jti=uuid.uuid4().hex,
            token_type=token_type,
            expires_at=expires_at,
            is_revoked=False,
        )
        db.add(token)
        summary.created_auth_tokens += 1

    db.commit()


def _client_order_sequence(db: Session) -> dict[int, int]:
    rows = db.execute(
        select(Order.client_id, func.max(Order.client_order_number)).group_by(Order.client_id)
    ).all()
    return {int(client_id): int(max_seq or 0) for client_id, max_seq in rows}


def _pick_driver_for_class(drivers: list[Driver], requested_class: CarComfortClass, rng: random.Random) -> Driver | None:
    eligible = [
        driver
        for driver in drivers
        if driver.car_id is not None and _class_rank(driver.approved_car_class) >= _class_rank(requested_class)
    ]
    if eligible:
        return rng.choice(eligible)
    fallback = [driver for driver in drivers if driver.car_id is not None]
    return rng.choice(fallback) if fallback else None


def _resolve_estimated_cost(trip: TripRow, tariff_by_class: dict[CarComfortClass, Tariff], comfort_class: CarComfortClass) -> float:
    tariff = tariff_by_class.get(comfort_class)
    if tariff is None:
        # fallback на випадок порожніх тарифів
        km_price = {
            CarComfortClass.ECONOMY: 25.0,
            CarComfortClass.STANDARD: 35.0,
            CarComfortClass.COMFORT: 35.0,
            CarComfortClass.BUSINESS: 50.0,
        }[comfort_class]
        return round(max(25.0, trip.distance_traveled * km_price), 2)

    base = float(tariff.base_fare)
    distance_cost = float(tariff.price_per_km) * max(0.3, trip.distance_traveled)
    minutes_cost = float(tariff.price_per_minute) * _normalize_duration_minutes(trip.trip_duration)
    return round(max(25.0, base + distance_cost + minutes_cost), 2)


def _seed_orders_and_reviews(
    db: Session,
    trips: list[TripRow],
    addresses: list[str],
    clients: list[Client],
    drivers: list[Driver],
    rng: random.Random,
    summary: SeedSummary,
) -> None:
    if not trips or not clients:
        return

    if len(addresses) < 2:
        addresses = addresses + ["вул. Шевченка, 1", "просп. Чорновола, 45"]

    tariff_by_class = {tariff.comfort_class: tariff for tariff in db.scalars(select(Tariff)).all()}
    order_seq_map = _client_order_sequence(db)

    new_orders: list[Order] = []
    created_completed_orders: list[Order] = []

    now = datetime.now(timezone.utc)

    for trip in trips:
        client = rng.choice(clients)
        requested_class = _infer_comfort_class(trip, rng)
        driver = _pick_driver_for_class(drivers, requested_class, rng)

        pickup_address = rng.choice(addresses)
        dropoff_address = rng.choice(addresses)
        if dropoff_address == pickup_address:
            dropoff_address = rng.choice(addresses)

        pickup_lat, pickup_lng = _random_lat_lng(rng)
        dropoff_lat, dropoff_lng = _random_lat_lng(rng)

        trip_minutes = _normalize_duration_minutes(trip.trip_duration)
        distance_km = max(0.3, trip.distance_traveled)

        estimated_cost = _resolve_estimated_cost(trip, tariff_by_class, requested_class)
        candidate_final = trip.total_fare if trip.total_fare > 0 else (trip.fare + trip.tip + trip.miscellaneous_fees)
        final_cost = round(max(estimated_cost, candidate_final), 2)

        order_status = rng.choices(
            [
                OrderStatus.COMPLETED,
                OrderStatus.CANCELLED,
                OrderStatus.PENDING,
                OrderStatus.ASSIGNED,
                OrderStatus.DRIVER_ARRIVED,
                OrderStatus.IN_PROGRESS,
            ],
            weights=[0.72, 0.12, 0.06, 0.04, 0.03, 0.03],
            k=1,
        )[0]

        if order_status in {OrderStatus.PENDING, OrderStatus.CANCELLED}:
            assigned_driver_id = None
            assigned_car_id = None
            payout = None
            payout_ratio = None
            if order_status == OrderStatus.CANCELLED:
                final_cost = None
        else:
            assigned_driver_id = driver.id if driver else None
            assigned_car_id = driver.car_id if driver else None
            payout_ratio = round(rng.uniform(0.65, 0.8), 2) if final_cost else None
            payout = round(final_cost * payout_ratio, 2) if payout_ratio else None

        order_seq_map[client.id] = order_seq_map.get(client.id, 0) + 1

        created_at = now - timedelta(
            days=rng.randint(0, 160),
            hours=rng.randint(0, 23),
            minutes=rng.randint(0, 59),
        )

        order = Order(
            client_id=client.id,
            driver_id=assigned_driver_id,
            car_id=assigned_car_id,
            requested_comfort_class=requested_class,
            client_order_number=order_seq_map[client.id],
            pickup_address=pickup_address,
            dropoff_address=dropoff_address,
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            dropoff_lat=dropoff_lat,
            dropoff_lng=dropoff_lng,
            distance_km=round(distance_km, 3),
            estimated_minutes=trip_minutes,
            estimated_cost=estimated_cost,
            driver_payout=payout,
            driver_payout_ratio=payout_ratio,
            final_cost=final_cost if order_status == OrderStatus.COMPLETED else (final_cost if order_status in {OrderStatus.IN_PROGRESS, OrderStatus.DRIVER_ARRIVED} else None),
            status=order_status,
            created_at=created_at,
            updated_at=created_at + timedelta(minutes=rng.randint(1, max(2, trip_minutes))),
        )
        db.add(order)
        new_orders.append(order)

        if order_status == OrderStatus.COMPLETED and assigned_driver_id:
            created_completed_orders.append(order)

    db.flush()

    existing_review_order_ids = {order_id for order_id in db.scalars(select(Review.order_id)).all()}

    for order in created_completed_orders:
        if order.id in existing_review_order_ids:
            continue
        if rng.random() > 0.55:
            continue

        rating_base = 5 if (order.driver_payout_ratio or 0) >= 0.7 else 4
        rating = max(3, min(5, rating_base + rng.choice([-1, 0, 0, 1])))

        review = Review(
            order_id=order.id,
            client_id=order.client_id,
            driver_id=order.driver_id,
            rating=rating,
            comment=rng.choice(ORDER_REVIEW_COMMENTS),
            created_at=order.updated_at + timedelta(minutes=rng.randint(5, 180)),
        )
        db.add(review)
        summary.created_reviews += 1

    db.commit()
    summary.created_orders += len(new_orders)


def run_seed_from_sources(
    trips_file: Path,
    addresses_file: Path,
    *,
    limit: int | None = None,
    random_seed: int = 42,
) -> SeedSummary:
    rng = random.Random(random_seed)

    if not trips_file.exists():
        raise FileNotFoundError(f"Trips file not found: {trips_file}")
    if not addresses_file.exists():
        raise FileNotFoundError(f"Addresses file not found: {addresses_file}")

    trips = load_trip_rows(trips_file, limit=limit)
    addresses = load_addresses(addresses_file)

    summary = SeedSummary(trips_loaded=len(trips), addresses_loaded=len(addresses))

    db = SessionLocal()
    try:
        # База-каркас
        seed_default_tariffs(db)
        seed_predefined_users(db)
        seed_fleet_cars(db)

        admin_user = db.scalar(
            select(User)
            .where(User.role.in_([UserRole.ADMIN, UserRole.DISPATCHER]))
            .order_by(User.id.asc())
        )

        client_target = max(40, min(300, max(1, len(trips) // 12)))
        driver_target = max(25, min(180, max(1, len(trips) // 20)))

        clients = _ensure_clients(db, client_target, rng, summary)
        drivers = _ensure_drivers(db, driver_target, rng, summary)

        _ensure_driver_applications(
            db,
            target_count=max(20, driver_target // 2),
            admin_user=admin_user,
            rng=rng,
            summary=summary,
        )

        _ensure_driver_class_applications(
            db,
            target_count=max(30, driver_target),
            drivers=drivers,
            admin_user=admin_user,
            rng=rng,
            summary=summary,
        )

        _seed_orders_and_reviews(
            db,
            trips=trips,
            addresses=addresses,
            clients=clients,
            drivers=drivers,
            rng=rng,
            summary=summary,
        )

        users = list(db.scalars(select(User)).all())
        _ensure_auth_tokens(
            db,
            users=users,
            target_count=max(15, len(users) // 3),
            rng=rng,
            summary=summary,
        )

        return summary
    finally:
        db.close()


def _print_summary(summary: SeedSummary) -> None:
    print("Seed completed successfully")
    print(f"- trips loaded: {summary.trips_loaded}")
    print(f"- addresses loaded: {summary.addresses_loaded}")
    print(f"- created clients: {summary.created_clients}")
    print(f"- created drivers: {summary.created_drivers}")
    print(f"- created cars: {summary.created_cars}")
    print(f"- created driver applications: {summary.created_driver_applications}")
    print(f"- created driver class applications: {summary.created_driver_class_applications}")
    print(f"- created orders: {summary.created_orders}")
    print(f"- created reviews: {summary.created_reviews}")
    print(f"- created auth tokens: {summary.created_auth_tokens}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fill taxi_dispatch DB from trip dataset and addresses file with logical random completion."
    )
    parser.add_argument(
        "--trips-file",
        required=True,
        type=Path,
        help="Path to CSV with format: trip_duration,distance_traveled,num_of_passengers,fare,tip,miscellaneous_fees,total_fare,surge_applied",
    )
    parser.add_argument(
        "--addresses-file",
        required=True,
        type=Path,
        help="Path to addresses file (one address per line, optionally numbered).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of trip rows to import.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible synthetic data.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_seed_from_sources(
        trips_file=args.trips_file,
        addresses_file=args.addresses_file,
        limit=args.limit,
        random_seed=args.seed,
    )
    _print_summary(summary)


if __name__ == "__main__":
    main()
