import enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    CLIENT = "client"
    DRIVER = "driver"
    ADMIN = "admin"


class DriverApplicationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class DriverClassApplicationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class DriverStatus(str, enum.Enum):
    FREE = "free"
    ON_ORDER = "on_order"
    BREAK = "break"
    INACTIVE = "inactive"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    DRIVER_ARRIVED = "driver_arrived"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CarComfortClass(str, enum.Enum):
    ECONOMY = "economy"
    STANDARD = "standard"
    COMFORT = "comfort"
    BUSINESS = "business"


class TokenType(str, enum.Enum):
    ACCESS = "access"
    REFRESH = "refresh"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(80), default="")
    last_name: Mapped[str] = mapped_column(String(80), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    client_profile: Mapped["Client"] = relationship(back_populates="user", uselist=False)
    driver_profile: Mapped["Driver"] = relationship(back_populates="user", uselist=False)
    reviewed_driver_applications: Mapped[list["DriverApplication"]] = relationship(
        back_populates="reviewer", foreign_keys="DriverApplication.reviewed_by"
    )
    reviewed_driver_class_applications: Mapped[list["DriverClassApplication"]] = relationship(
        back_populates="reviewer", foreign_keys="DriverClassApplication.reviewed_by"
    )
    auth_tokens: Mapped[list["AuthToken"]] = relationship(back_populates="user")


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    token_type: Mapped[TokenType] = mapped_column(Enum(TokenType), nullable=False)
    expires_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="auth_tokens")


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    phone: Mapped[str] = mapped_column(String(20))
    balance: Mapped[float] = mapped_column(Numeric(10, 2), default=0)

    user: Mapped[User] = relationship(back_populates="client_profile")
    orders: Mapped[list["Order"]] = relationship(back_populates="client")


class Car(Base):
    __tablename__ = "cars"

    id: Mapped[int] = mapped_column(primary_key=True)
    plate_number: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    make: Mapped[str] = mapped_column(String(60), default="")
    model: Mapped[str] = mapped_column(String(100))
    production_year: Mapped[int] = mapped_column(Integer, default=2020)
    engine: Mapped[str] = mapped_column(String(80), default="")
    transmission: Mapped[str] = mapped_column(String(40), default="automatic")
    color: Mapped[str] = mapped_column(String(30))
    comfort_class: Mapped[CarComfortClass] = mapped_column(Enum(CarComfortClass), nullable=False)
    technical_status: Mapped[str] = mapped_column(String(100), default="good")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    drivers: Mapped[list["Driver"]] = relationship(back_populates="car")
    orders: Mapped[list["Order"]] = relationship(back_populates="car")


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    license_number: Mapped[str] = mapped_column(String(30), unique=True)
    rating: Mapped[float] = mapped_column(Float, default=5.0)
    status: Mapped[DriverStatus] = mapped_column(Enum(DriverStatus), default=DriverStatus.FREE)
    car_id: Mapped[int | None] = mapped_column(ForeignKey("cars.id"), nullable=True)
    approved_car_class: Mapped[CarComfortClass] = mapped_column(
        Enum(CarComfortClass), default=CarComfortClass.ECONOMY, nullable=False
    )
    requested_car_class: Mapped[CarComfortClass | None] = mapped_column(Enum(CarComfortClass), nullable=True)
    uses_own_car: Mapped[bool] = mapped_column(Boolean, default=False)
    own_car_make: Mapped[str | None] = mapped_column(String(60), nullable=True)
    own_car_model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    own_car_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    own_car_plate: Mapped[str | None] = mapped_column(String(20), nullable=True)
    own_car_engine: Mapped[str | None] = mapped_column(String(80), nullable=True)
    own_car_transmission: Mapped[str | None] = mapped_column(String(40), nullable=True)
    current_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    user: Mapped[User] = relationship(back_populates="driver_profile")
    car: Mapped[Car | None] = relationship(back_populates="drivers")
    orders: Mapped[list["Order"]] = relationship(back_populates="driver")
    class_applications: Mapped[list["DriverClassApplication"]] = relationship(back_populates="driver")


class DriverApplication(Base):
    __tablename__ = "driver_applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    phone: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    license_series: Mapped[str] = mapped_column(String(20))
    license_number: Mapped[str] = mapped_column(String(30), unique=True)
    status: Mapped[DriverApplicationStatus] = mapped_column(
        Enum(DriverApplicationStatus),
        default=DriverApplicationStatus.PENDING,
        nullable=False,
    )
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    reviewer: Mapped[User | None] = relationship(back_populates="reviewed_driver_applications")


class Tariff(Base):
    __tablename__ = "tariffs"
    __table_args__ = (UniqueConstraint("comfort_class", name="uq_tariff_comfort_class"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    comfort_class: Mapped[CarComfortClass] = mapped_column(Enum(CarComfortClass), nullable=False)
    base_fare: Mapped[float] = mapped_column(Numeric(10, 2), default=40)
    price_per_km: Mapped[float] = mapped_column(Numeric(10, 2), default=15)
    price_per_minute: Mapped[float] = mapped_column(Numeric(10, 2), default=2)
    night_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("client_id", "client_order_number", name="uq_order_client_sequence"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("drivers.id"), nullable=True)
    car_id: Mapped[int | None] = mapped_column(ForeignKey("cars.id"), nullable=True)
    requested_comfort_class: Mapped[CarComfortClass] = mapped_column(
        Enum(CarComfortClass), nullable=False, default=CarComfortClass.ECONOMY
    )
    client_order_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    pickup_address: Mapped[str] = mapped_column(String(255))
    dropoff_address: Mapped[str] = mapped_column(String(255))
    pickup_lat: Mapped[float] = mapped_column(Float)
    pickup_lng: Mapped[float] = mapped_column(Float)
    dropoff_lat: Mapped[float] = mapped_column(Float)
    dropoff_lng: Mapped[float] = mapped_column(Float)

    distance_km: Mapped[float] = mapped_column(Float)
    estimated_minutes: Mapped[int] = mapped_column(Integer)
    estimated_cost: Mapped[float] = mapped_column(Numeric(10, 2))
    driver_payout: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    driver_payout_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_cost: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    client: Mapped[Client] = relationship(back_populates="orders")
    driver: Mapped[Driver | None] = relationship(back_populates="orders")
    car: Mapped[Car | None] = relationship(back_populates="orders")
    review: Mapped["Review"] = relationship(back_populates="order", uselist=False)


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"))
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped[Order] = relationship(back_populates="review")


class DriverClassApplication(Base):
    __tablename__ = "driver_class_applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False, index=True)
    requested_car_class: Mapped[CarComfortClass] = mapped_column(Enum(CarComfortClass), nullable=False)
    own_car_make: Mapped[str] = mapped_column(String(60))
    own_car_model: Mapped[str] = mapped_column(String(80))
    own_car_year: Mapped[int] = mapped_column(Integer)
    own_car_plate: Mapped[str] = mapped_column(String(20))
    own_car_engine: Mapped[str] = mapped_column(String(80))
    own_car_transmission: Mapped[str] = mapped_column(String(40))
    status: Mapped[DriverClassApplicationStatus] = mapped_column(
        Enum(DriverClassApplicationStatus),
        nullable=False,
        default=DriverClassApplicationStatus.PENDING,
    )
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    driver: Mapped[Driver] = relationship(back_populates="class_applications")
    reviewer: Mapped[User | None] = relationship(back_populates="reviewed_driver_class_applications")
