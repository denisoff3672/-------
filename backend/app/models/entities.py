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
    DISPATCHER = "dispatcher"
    ADMIN = "admin"


class DriverStatus(str, enum.Enum):
    FREE = "free"
    ON_ORDER = "on_order"
    BREAK = "break"
    INACTIVE = "inactive"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CarComfortClass(str, enum.Enum):
    ECONOMY = "economy"
    STANDARD = "standard"
    BUSINESS = "business"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    client_profile: Mapped["Client"] = relationship(back_populates="user", uselist=False)
    driver_profile: Mapped["Driver"] = relationship(back_populates="user", uselist=False)


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
    model: Mapped[str] = mapped_column(String(100))
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

    user: Mapped[User] = relationship(back_populates="driver_profile")
    car: Mapped[Car | None] = relationship(back_populates="drivers")
    orders: Mapped[list["Order"]] = relationship(back_populates="driver")


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

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("drivers.id"), nullable=True)
    car_id: Mapped[int | None] = mapped_column(ForeignKey("cars.id"), nullable=True)

    pickup_address: Mapped[str] = mapped_column(String(255))
    dropoff_address: Mapped[str] = mapped_column(String(255))
    pickup_lat: Mapped[float] = mapped_column(Float)
    pickup_lng: Mapped[float] = mapped_column(Float)
    dropoff_lat: Mapped[float] = mapped_column(Float)
    dropoff_lng: Mapped[float] = mapped_column(Float)

    distance_km: Mapped[float] = mapped_column(Float)
    estimated_minutes: Mapped[int] = mapped_column(Integer)
    estimated_cost: Mapped[float] = mapped_column(Numeric(10, 2))
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
