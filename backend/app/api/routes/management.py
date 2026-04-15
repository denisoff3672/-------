from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.entities import Car, Driver, DriverStatus, Order, OrderStatus, Tariff, User, UserRole
from app.schemas.dto import CarCreate, CarOut, DriverStatusUpdate, ReportOut, TariffCreate, TariffOut, UserOut

router = APIRouter(prefix="/management", tags=["Management"])


@router.post("/cars", response_model=CarOut)
def create_car(
    payload: CarCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.DISPATCHER)),
):
    existing = db.scalar(select(Car).where(Car.plate_number == payload.plate_number))
    if existing:
        raise HTTPException(status_code=400, detail="Car with this plate already exists")
    car = Car(**payload.model_dump())
    db.add(car)
    db.commit()
    db.refresh(car)
    return car


@router.get("/cars", response_model=list[CarOut])
def list_cars(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.DISPATCHER, UserRole.DRIVER)),
):
    return list(db.scalars(select(Car).order_by(Car.id.desc())).all())


@router.post("/tariffs", response_model=TariffOut)
def upsert_tariff(
    payload: TariffCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.DISPATCHER)),
):
    tariff = db.scalar(select(Tariff).where(Tariff.comfort_class == payload.comfort_class))
    if not tariff:
        tariff = Tariff(**payload.model_dump())
        db.add(tariff)
    else:
        tariff.base_fare = payload.base_fare
        tariff.price_per_km = payload.price_per_km
        tariff.price_per_minute = payload.price_per_minute
        tariff.night_multiplier = payload.night_multiplier
        tariff.is_active = True

    db.commit()
    db.refresh(tariff)
    return tariff


@router.get("/tariffs", response_model=list[TariffOut])
def list_tariffs(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list(db.scalars(select(Tariff).order_by(Tariff.id.desc())).all())


@router.patch("/drivers/me/status", response_model=dict)
def update_my_driver_status(
    payload: DriverStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DRIVER)),
):
    driver = db.scalar(select(Driver).where(Driver.user_id == current_user.id))
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    driver.status = payload.status
    db.commit()
    return {"message": "Status updated", "status": driver.status}


@router.get("/drivers", response_model=list[dict])
def list_drivers(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.DISPATCHER)),
):
    drivers = db.scalars(select(Driver).order_by(Driver.id.desc())).all()
    return [
        {
            "id": driver.id,
            "user_id": driver.user_id,
            "license_number": driver.license_number,
            "rating": driver.rating,
            "status": driver.status,
            "car_id": driver.car_id,
        }
        for driver in drivers
    ]


@router.patch("/drivers/{driver_id}/assign-car", response_model=dict)
def assign_car_to_driver(
    driver_id: int,
    car_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.DISPATCHER)),
):
    driver = db.get(Driver, driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    car = db.get(Car, car_id)
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")
    if not car.is_active:
        raise HTTPException(status_code=400, detail="Car is not active")

    driver.car_id = car_id
    db.commit()
    return {"message": "Car assigned to driver", "driver_id": driver_id, "car_id": car_id}


@router.get("/users", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.DISPATCHER)),
):
    return list(db.scalars(select(User).order_by(User.id.desc())).all())


@router.patch("/users/{user_id}/block", response_model=UserOut)
def block_user(
    user_id: int,
    blocked: bool,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_blocked = blocked
    db.commit()
    db.refresh(user)
    return user


@router.get("/reports/summary", response_model=ReportOut)
def summary_report(
    start: datetime = Query(...),
    end: datetime = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.DISPATCHER)),
):
    total_orders = db.scalar(
        select(func.count(Order.id)).where(and_(Order.created_at >= start, Order.created_at <= end))
    )

    completed_orders = db.scalar(
        select(func.count(Order.id)).where(
            and_(
                Order.created_at >= start,
                Order.created_at <= end,
                Order.status == OrderStatus.COMPLETED,
            )
        )
    )

    revenue = db.scalar(
        select(func.coalesce(func.sum(Order.final_cost), 0)).where(
            and_(
                Order.created_at >= start,
                Order.created_at <= end,
                Order.status == OrderStatus.COMPLETED,
            )
        )
    )

    route_rows = db.execute(
        select(
            Order.pickup_address,
            Order.dropoff_address,
            func.count(Order.id).label("route_count"),
        )
        .where(and_(Order.created_at >= start, Order.created_at <= end))
        .group_by(Order.pickup_address, Order.dropoff_address)
        .order_by(desc("route_count"))
        .limit(5)
    ).all()

    driver_rows = db.execute(
        select(Order.driver_id, func.count(Order.id).label("completed_count"))
        .where(
            and_(
                Order.created_at >= start,
                Order.created_at <= end,
                Order.status == OrderStatus.COMPLETED,
                Order.driver_id.is_not(None),
            )
        )
        .group_by(Order.driver_id)
        .order_by(desc("completed_count"))
        .limit(10)
    ).all()

    return ReportOut(
        period_start=start,
        period_end=end,
        total_orders=total_orders or 0,
        completed_orders=completed_orders or 0,
        revenue=float(revenue or 0),
        top_routes=[
            {"pickup": row.pickup_address, "dropoff": row.dropoff_address, "count": row.route_count}
            for row in route_rows
        ],
        driver_activity=[
            {"driver_id": row.driver_id, "completed_orders": row.completed_count} for row in driver_rows
        ],
    )
