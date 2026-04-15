from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.entities import (
    Car,
    Client,
    Driver,
    DriverStatus,
    Order,
    OrderStatus,
    Review,
    Tariff,
    User,
    UserRole,
)
from app.schemas.dto import OrderCreate, OrderOut, OrderStatusUpdate, ReviewCreate, ReviewOut
from app.services.pricing import calculate_price, estimate_minutes, haversine_km

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLIENT, UserRole.DISPATCHER, UserRole.ADMIN)),
):
    if current_user.role == UserRole.CLIENT:
        client = db.scalar(select(Client).where(Client.user_id == current_user.id))
        if not client:
            raise HTTPException(status_code=400, detail="Client profile is missing")
    else:
        if payload.client_id is None:
            raise HTTPException(status_code=400, detail="Dispatcher/Admin must provide client_id")
        client = db.get(Client, payload.client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

    tariff = db.scalar(
        select(Tariff).where(and_(Tariff.comfort_class == payload.comfort_class, Tariff.is_active.is_(True)))
    )
    if not tariff:
        raise HTTPException(status_code=404, detail="No active tariff for this comfort class")

    distance_km = round(
        haversine_km(payload.pickup_lat, payload.pickup_lng, payload.dropoff_lat, payload.dropoff_lng), 2
    )
    duration_minutes = estimate_minutes(distance_km)
    estimated_cost = calculate_price(distance_km, duration_minutes, tariff)

    available_driver = db.scalar(
        select(Driver)
        .join(Car, Driver.car_id == Car.id)
        .where(
            and_(
                Driver.status == DriverStatus.FREE,
                Car.is_active.is_(True),
                Car.comfort_class == payload.comfort_class,
            )
        )
        .limit(1)
    )

    order = Order(
        client_id=client.id,
        pickup_address=payload.pickup_address,
        dropoff_address=payload.dropoff_address,
        pickup_lat=payload.pickup_lat,
        pickup_lng=payload.pickup_lng,
        dropoff_lat=payload.dropoff_lat,
        dropoff_lng=payload.dropoff_lng,
        distance_km=distance_km,
        estimated_minutes=duration_minutes,
        estimated_cost=estimated_cost,
        status=OrderStatus.PENDING,
    )

    if available_driver:
        order.driver_id = available_driver.id
        order.car_id = available_driver.car_id
        order.status = OrderStatus.IN_PROGRESS
        available_driver.status = DriverStatus.ON_ORDER

    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.get("", response_model=list[OrderOut])
def list_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    driver_id: int | None = Query(default=None),
    min_cost: float | None = Query(default=None),
    max_cost: float | None = Query(default=None),
):
    query = select(Order)

    if current_user.role == UserRole.CLIENT:
        client = db.scalar(select(Client).where(Client.user_id == current_user.id))
        if not client:
            return []
        query = query.where(Order.client_id == client.id)

    if current_user.role == UserRole.DRIVER:
        driver = db.scalar(select(Driver).where(Driver.user_id == current_user.id))
        if not driver:
            return []
        query = query.where(Order.driver_id == driver.id)

    if date_from:
        query = query.where(Order.created_at >= date_from)
    if date_to:
        query = query.where(Order.created_at <= date_to)
    if driver_id:
        query = query.where(Order.driver_id == driver_id)
    if min_cost is not None:
        query = query.where(Order.estimated_cost >= min_cost)
    if max_cost is not None:
        query = query.where(Order.estimated_cost <= max_cost)

    query = query.order_by(Order.created_at.desc())
    return list(db.scalars(query).all())


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if current_user.role == UserRole.DRIVER:
        driver = db.scalar(select(Driver).where(Driver.user_id == current_user.id))
        if not driver or order.driver_id != driver.id:
            raise HTTPException(status_code=403, detail="You can only manage your own orders")

    if current_user.role == UserRole.CLIENT:
        raise HTTPException(status_code=403, detail="Client cannot update order status")

    order.status = payload.status

    if payload.status == OrderStatus.COMPLETED:
        order.final_cost = order.estimated_cost
        if order.driver_id:
            driver = db.get(Driver, order.driver_id)
            if driver:
                driver.status = DriverStatus.FREE

    if payload.status == OrderStatus.CANCELLED and order.driver_id:
        driver = db.get(Driver, order.driver_id)
        if driver:
            driver.status = DriverStatus.FREE

    db.commit()
    db.refresh(order)
    return order


@router.post("/review", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def create_review(
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLIENT)),
):
    client = db.scalar(select(Client).where(Client.user_id == current_user.id))
    if not client:
        raise HTTPException(status_code=404, detail="Client profile not found")

    order = db.get(Order, payload.order_id)
    if not order or order.client_id != client.id:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != OrderStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Review can be left only for completed order")
    if order.review:
        raise HTTPException(status_code=400, detail="Review already exists")
    if not order.driver_id:
        raise HTTPException(status_code=400, detail="Cannot review order without driver")

    review = Review(
        order_id=order.id,
        client_id=client.id,
        driver_id=order.driver_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review
