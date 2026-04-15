from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.entities import CarComfortClass, DriverStatus, OrderStatus, UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    role: UserRole
    phone: str | None = None
    license_number: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: UserRole
    is_blocked: bool


class CarCreate(BaseModel):
    plate_number: str
    model: str
    color: str
    comfort_class: CarComfortClass
    technical_status: str = "good"


class CarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plate_number: str
    model: str
    color: str
    comfort_class: CarComfortClass
    technical_status: str
    is_active: bool


class DriverStatusUpdate(BaseModel):
    status: DriverStatus


class TariffCreate(BaseModel):
    comfort_class: CarComfortClass
    base_fare: Decimal
    price_per_km: Decimal
    price_per_minute: Decimal
    night_multiplier: float = 1.0


class TariffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    comfort_class: CarComfortClass
    base_fare: Decimal
    price_per_km: Decimal
    price_per_minute: Decimal
    night_multiplier: float
    is_active: bool


class OrderCreate(BaseModel):
    client_id: int | None = None
    pickup_address: str
    dropoff_address: str
    pickup_lat: float
    pickup_lng: float
    dropoff_lat: float
    dropoff_lng: float
    comfort_class: CarComfortClass


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    driver_id: int | None
    car_id: int | None
    pickup_address: str
    dropoff_address: str
    distance_km: float
    estimated_minutes: int
    estimated_cost: Decimal
    final_cost: Decimal | None
    status: OrderStatus
    created_at: datetime


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class ReviewCreate(BaseModel):
    order_id: int
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    client_id: int
    driver_id: int
    rating: int
    comment: str | None
    created_at: datetime


class ReportOut(BaseModel):
    period_start: datetime
    period_end: datetime
    total_orders: int
    completed_orders: int
    revenue: float
    top_routes: list[dict]
    driver_activity: list[dict]
