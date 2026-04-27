from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.entities import (
    Car,
    CarComfortClass,
    Client,
    Driver,
    DriverStatus,
    Order,
    OrderStatus,
    Review,
    User,
    UserRole,
)
from app.schemas.dto import (
    DriverOrderDecision,
    OrderCreate,
    OrderOut,
    OrderQuoteOut,
    OrderQuoteRequest,
    OrderStatusUpdate,
    ReviewCreate,
    ReviewOut,
)
from app.services.geo import is_within_lviv
from app.services.pricing import estimate_minutes, haversine_km

router = APIRouter(prefix="/orders", tags=["Orders"])

PER_KM_RATES = {
    CarComfortClass.ECONOMY: 25,
    CarComfortClass.STANDARD: 35,
    CarComfortClass.COMFORT: 35,
    CarComfortClass.BUSINESS: 50,
}
ACTIVE_ORDER_STATUSES = (
    OrderStatus.PENDING,
    OrderStatus.ASSIGNED,
    OrderStatus.DRIVER_ARRIVED,
    OrderStatus.IN_PROGRESS,
)


def _class_rank(comfort_class: CarComfortClass) -> int:
    rank = {
        CarComfortClass.ECONOMY: 1,
        CarComfortClass.STANDARD: 2,
        CarComfortClass.COMFORT: 3,
        CarComfortClass.BUSINESS: 4,
    }
    return rank.get(comfort_class, 1)


def _estimate_cost(distance_km: float, comfort_class: CarComfortClass) -> float:
    return round(distance_km * PER_KM_RATES.get(comfort_class, 25), 2)


def _ensure_lviv_route(pickup_lat: float, pickup_lng: float, dropoff_lat: float, dropoff_lng: float) -> None:
    if not is_within_lviv(pickup_lat, pickup_lng):
        raise HTTPException(status_code=400, detail="Pickup point must be within Lviv")
    if not is_within_lviv(dropoff_lat, dropoff_lng):
        raise HTTPException(status_code=400, detail="Dropoff point must be within Lviv")


def _next_client_order_number(db: Session, client_id: int) -> int:
    current_max = db.scalar(select(func.max(Order.client_order_number)).where(Order.client_id == client_id))
    return int(current_max or 0) + 1


def _find_nearest_driver(
    db: Session,
    pickup_lat: float,
    pickup_lng: float,
    requested_class: CarComfortClass,
    exclude_driver_id: int | None = None,
) -> Driver | None:
    drivers = db.scalars(select(Driver).where(Driver.status == DriverStatus.FREE)).all()

    nearest: Driver | None = None
    nearest_distance = float("inf")

    for driver in drivers:
        if exclude_driver_id and driver.id == exclude_driver_id:
            continue

        if _class_rank(driver.approved_car_class) < _class_rank(requested_class):
            continue

        if driver.current_lat is None or driver.current_lng is None:
            continue

        if not driver.uses_own_car:
            if not driver.car_id:
                continue
            if not driver.car or not driver.car.is_active:
                continue

        distance = haversine_km(driver.current_lat, driver.current_lng, pickup_lat, pickup_lng)
        if distance < nearest_distance:
            nearest_distance = distance
            nearest = driver

    return nearest


@router.post("/quote", response_model=OrderQuoteOut)
def quote_order(payload: OrderQuoteRequest):
    _ensure_lviv_route(payload.pickup_lat, payload.pickup_lng, payload.dropoff_lat, payload.dropoff_lng)
    distance_km = round(
        haversine_km(payload.pickup_lat, payload.pickup_lng, payload.dropoff_lat, payload.dropoff_lng), 2
    )
    return OrderQuoteOut(
        distance_km=distance_km,
        prices={
            "economy": round(distance_km * PER_KM_RATES[CarComfortClass.ECONOMY], 2),
            "standard": round(distance_km * PER_KM_RATES[CarComfortClass.STANDARD], 2),
            "comfort": round(distance_km * PER_KM_RATES[CarComfortClass.COMFORT], 2),
            "business": round(distance_km * PER_KM_RATES[CarComfortClass.BUSINESS], 2),
        },
    )


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLIENT, UserRole.ADMIN)),
):
    if current_user.role == UserRole.CLIENT:
        client = db.scalar(select(Client).where(Client.user_id == current_user.id))
        if not client:
            raise HTTPException(status_code=400, detail="Client profile is missing")
    else:
        if payload.client_id is None:
            raise HTTPException(status_code=400, detail="Admin must provide client_id")
        client = db.get(Client, payload.client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

    _ensure_lviv_route(payload.pickup_lat, payload.pickup_lng, payload.dropoff_lat, payload.dropoff_lng)

    existing_active_order = db.scalar(
        select(Order)
        .where(
            Order.client_id == client.id,
            Order.status.in_(ACTIVE_ORDER_STATUSES),
        )
        .order_by(Order.created_at.desc())
    )
    if existing_active_order:
        raise HTTPException(status_code=400, detail="Client already has an active order")

    distance_km = round(
        haversine_km(payload.pickup_lat, payload.pickup_lng, payload.dropoff_lat, payload.dropoff_lng), 2
    )
    duration_minutes = estimate_minutes(distance_km)
    estimated_cost = _estimate_cost(distance_km, payload.comfort_class)

    available_driver = _find_nearest_driver(
        db,
        pickup_lat=payload.pickup_lat,
        pickup_lng=payload.pickup_lng,
        requested_class=payload.comfort_class,
    )

    order = Order(
        client_id=client.id,
        client_order_number=_next_client_order_number(db, client.id),
        pickup_address=payload.pickup_address,
        dropoff_address=payload.dropoff_address,
        pickup_lat=payload.pickup_lat,
        pickup_lng=payload.pickup_lng,
        dropoff_lat=payload.dropoff_lat,
        dropoff_lng=payload.dropoff_lng,
        requested_comfort_class=payload.comfort_class,
        distance_km=distance_km,
        estimated_minutes=duration_minutes,
        estimated_cost=estimated_cost,
        status=OrderStatus.PENDING,
    )

    if available_driver:
        order.driver_id = available_driver.id
        order.car_id = available_driver.car_id
        payout_ratio = 0.75 if available_driver.uses_own_car else 0.5
        order.driver_payout_ratio = payout_ratio
        order.driver_payout = round(estimated_cost * payout_ratio, 2)
        available_driver.status = DriverStatus.ON_ORDER

    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.patch("/{order_id}/decision", response_model=OrderOut)
def driver_order_decision(
    order_id: int,
    payload: DriverOrderDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DRIVER)),
):
    driver = db.scalar(select(Driver).where(Driver.user_id == current_user.id))
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.driver_id != driver.id:
        raise HTTPException(status_code=403, detail="Order is not assigned to current driver")
    if order.status not in [OrderStatus.PENDING, OrderStatus.ASSIGNED]:
        raise HTTPException(status_code=400, detail="Decision already taken for this order")

    if payload.accept:
        order.status = OrderStatus.ASSIGNED
        db.commit()
        db.refresh(order)
        return order

    driver.status = DriverStatus.FREE
    next_driver = _find_nearest_driver(
        db,
        pickup_lat=order.pickup_lat,
        pickup_lng=order.pickup_lng,
        requested_class=order.requested_comfort_class,
        exclude_driver_id=driver.id,
    )

    if not next_driver:
        order.driver_id = None
        order.car_id = None
        order.driver_payout = None
        order.driver_payout_ratio = None
        order.status = OrderStatus.PENDING
    else:
        order.driver_id = next_driver.id
        order.car_id = next_driver.car_id
        order.driver_payout_ratio = 0.75 if next_driver.uses_own_car else 0.5
        order.driver_payout = round(float(order.estimated_cost) * order.driver_payout_ratio, 2)
        next_driver.status = DriverStatus.ON_ORDER
        order.status = OrderStatus.PENDING

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

    if current_user.role == UserRole.DRIVER:
        allowed_statuses = {
            OrderStatus.DRIVER_ARRIVED,
            OrderStatus.IN_PROGRESS,
            OrderStatus.COMPLETED,
            OrderStatus.CANCELLED,
        }
        if payload.status not in allowed_statuses:
            raise HTTPException(status_code=400, detail="Driver cannot set this status")

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


@router.patch("/{order_id}/cancel", response_model=OrderOut)
def cancel_order_search(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLIENT, UserRole.ADMIN)),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if current_user.role == UserRole.CLIENT:
        client = db.scalar(select(Client).where(Client.user_id == current_user.id))
        if not client or order.client_id != client.id:
            raise HTTPException(status_code=403, detail="You can cancel only your own orders")

    cancellable_statuses = {OrderStatus.PENDING, OrderStatus.ASSIGNED, OrderStatus.DRIVER_ARRIVED}
    if order.status not in cancellable_statuses:
        raise HTTPException(status_code=400, detail="Order cannot be cancelled at this stage")

    order.status = OrderStatus.CANCELLED
    if order.driver_id:
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
    db.flush()

    avg_rating = db.scalar(
        select(func.coalesce(func.avg(Review.rating), 0)).where(Review.driver_id == order.driver_id)
    )
    driver = db.get(Driver, order.driver_id)
    if driver:
        driver.rating = min(5.0, max(0.0, float(avg_rating or 0)))

    db.commit()
    db.refresh(review)
    return review
