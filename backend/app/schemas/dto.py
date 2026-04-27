from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.entities import (
    CarComfortClass,
    DriverApplicationStatus,
    DriverClassApplicationStatus,
    DriverStatus,
    OrderStatus,
    UserRole,
)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=2, max_length=80)
    last_name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=8, max_length=20)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=6, max_length=128)


class DriverApplicationCreate(BaseModel):
    first_name: str = Field(min_length=2, max_length=80)
    last_name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=8, max_length=20)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=6, max_length=128)
    license_series: str = Field(min_length=2, max_length=20)
    license_number: str = Field(min_length=4, max_length=30)


class DriverApplicationReview(BaseModel):
    approve: bool
    review_note: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    first_name: str
    last_name: str
    phone: str
    role: UserRole
    is_blocked: bool


class AuthResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    role: UserRole
    is_blocked: bool
    accessToken: str


class DriverApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    phone: str
    email: str
    license_series: str
    license_number: str
    status: DriverApplicationStatus
    reviewed_by: int | None
    review_note: str | None
    created_at: datetime
    reviewed_at: datetime | None


class CarCreate(BaseModel):
    plate_number: str
    make: str = ""
    model: str
    production_year: int = 2020
    engine: str = ""
    transmission: str = "automatic"
    color: str
    comfort_class: CarComfortClass
    technical_status: str = "good"


class CarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plate_number: str
    make: str
    model: str
    production_year: int
    engine: str
    transmission: str
    color: str
    comfort_class: CarComfortClass
    technical_status: str
    is_active: bool


class FleetCarOut(CarOut):
    is_occupied: bool
    assigned_driver_id: int | None
    assigned_driver_name: str | None


class AssignFleetCarRequest(BaseModel):
    car_id: int


class DriverClassApprovalRequest(BaseModel):
    approve: bool = True
    approved_car_class: CarComfortClass | None = None
    review_note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_rejection_note(self):
        if not self.approve:
            note = (self.review_note or "").strip()
            if len(note) < 3:
                raise ValueError("Review note is required when rejecting class request")
        return self


class DriverClassApplicationReview(BaseModel):
    approve: bool
    approved_car_class: CarComfortClass | None = None
    review_note: str = Field(min_length=3, max_length=1000)


class DriverOwnCarRequest(BaseModel):
    make: str
    model: str
    production_year: int
    plate_number: str
    engine: str
    transmission: str
    requested_car_class: CarComfortClass


class DriverLocationUpdate(BaseModel):
    lat: float
    lng: float


class DriverProfileOut(BaseModel):
    driver_id: int
    status: DriverStatus
    approved_car_class: CarComfortClass
    requested_car_class: CarComfortClass | None
    uses_own_car: bool
    current_lat: float | None
    current_lng: float | None
    assigned_company_car: CarOut | None
    own_car: dict | None
    last_class_application_status: DriverClassApplicationStatus | None = None
    last_class_application_note: str | None = None


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


class OrderQuoteRequest(BaseModel):
    pickup_lat: float
    pickup_lng: float
    dropoff_lat: float
    dropoff_lng: float


class OrderQuoteOut(BaseModel):
    distance_km: float
    prices: dict[str, float]


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_order_number: int
    client_id: int
    driver_id: int | None
    car_id: int | None
    requested_comfort_class: CarComfortClass
    pickup_address: str
    dropoff_address: str
    distance_km: float
    estimated_minutes: int
    estimated_cost: Decimal
    driver_payout: Decimal | None
    driver_payout_ratio: float | None
    final_cost: Decimal | None
    status: OrderStatus
    created_at: datetime
    review: "ReviewBriefOut | None" = None


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class DriverOrderDecision(BaseModel):
    accept: bool


class ReviewCreate(BaseModel):
    order_id: int
    rating: int = Field(ge=0, le=5)
    comment: str | None = None


class ReviewBriefOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rating: int
    comment: str | None
    created_at: datetime


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    client_id: int
    driver_id: int
    rating: int
    comment: str | None
    created_at: datetime


class AdminDriverStatsOut(BaseModel):
    driver_id: int
    user_id: int
    driver_name: str
    completed_orders: int
    earned_amount: float
    avg_rating: float
    email: str


class AdminOrderLogOut(BaseModel):
    order_id: int
    status: OrderStatus
    created_at: datetime
    pickup_address: str
    dropoff_address: str
    distance_km: float
    estimated_cost: float
    final_cost: float | None
    driver_id: int | None
    client_id: int


class AdminDashboardOut(BaseModel):
    avg_distance_km: float
    rides_by_car_class: dict[str, int]
    earnings_by_period: dict[str, float]


class AdminAnalyticsOverviewOut(BaseModel):
    revenue_by_period: dict[str, float]
    orders_count_by_period: dict[str, int]
    orders_by_car_class: dict[str, int]


class AdminDriverDetailsOut(BaseModel):
    driver_id: int
    driver_name: str
    email: str
    total_trips: int
    active_car: str | None
    avg_rating: float
    recent_reviews: list[ReviewOut]


class DriverClassApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    driver_id: int
    requested_car_class: CarComfortClass
    own_car_make: str
    own_car_model: str
    own_car_year: int
    own_car_plate: str
    own_car_engine: str
    own_car_transmission: str
    status: DriverClassApplicationStatus
    reviewed_by: int | None
    review_note: str | None
    reviewed_at: datetime | None
    created_at: datetime


class ReportOut(BaseModel):
    period_start: datetime
    period_end: datetime
    total_orders: int
    completed_orders: int
    revenue: float
    top_routes: list[dict]
    driver_activity: list[dict]


OrderOut.model_rebuild()
