from datetime import datetime
from math import asin, cos, radians, sin, sqrt

from app.models.entities import Tariff


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return radius * c


def estimate_minutes(distance_km: float, avg_speed_kmh: int = 32) -> int:
    if distance_km <= 0:
        return 1
    return max(1, int((distance_km / avg_speed_kmh) * 60))


def calculate_price(distance_km: float, minutes: int, tariff: Tariff, date_time: datetime | None = None) -> float:
    date_time = date_time or datetime.now()
    is_night = date_time.hour >= 22 or date_time.hour < 6

    base = float(tariff.base_fare)
    km_cost = float(tariff.price_per_km) * distance_km
    minute_cost = float(tariff.price_per_minute) * minutes
    raw_total = base + km_cost + minute_cost
    if is_night:
        raw_total *= float(tariff.night_multiplier)

    return round(raw_total, 2)
