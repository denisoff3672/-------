from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.entities import (
    Car,
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
    User,
    UserRole,
)
from app.schemas.dto import (
    AdminDashboardOut,
    AdminAnalyticsOverviewOut,
    AdminDriverDetailsOut,
    AdminDriverStatsOut,
    AdminOrderLogOut,
    AssignFleetCarRequest,
    CarCreate,
    CarOut,
    DriverClassApprovalRequest,
    DriverApplicationOut,
    DriverClassApplicationOut,
    DriverClassApplicationReview,
    DriverApplicationReview,
    DriverLocationUpdate,
    DriverOwnCarRequest,
    DriverProfileOut,
    DriverStatusUpdate,
    FleetCarOut,
    ReportOut,
    ReviewOut,
    TariffCreate,
    TariffOut,
    UserOut,
)
from app.services.geo import is_within_lviv

router = APIRouter(prefix="/management", tags=["Management"])


def _class_rank(comfort_class):
    rank = {
        "economy": 1,
        "standard": 2,
        "comfort": 3,
        "business": 4,
    }
    return rank.get(str(comfort_class.value if hasattr(comfort_class, "value") else comfort_class), 1)


def _driver_name(driver: Driver) -> str:
    if driver.user:
        return f"{driver.user.first_name} {driver.user.last_name}".strip()
    return f"Driver #{driver.id}"


def _period_starts(now: datetime) -> dict[str, datetime]:
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        "day": now.replace(hour=0, minute=0, second=0, microsecond=0),
        "week": week_start,
        "month": now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
        "year": now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0),
    }


@router.post("/cars", response_model=CarOut)
def create_car(
    payload: CarCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
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
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.DRIVER)),
):
    return list(db.scalars(select(Car).order_by(Car.id.desc())).all())


@router.get("/fleet/cars", response_model=list[FleetCarOut])
def list_fleet_cars(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    cars = db.scalars(select(Car).order_by(Car.id.asc())).all()
    occupied_by_car_id = {
        driver.car_id: driver for driver in db.scalars(select(Driver).where(Driver.car_id.is_not(None))).all()
    }

    result: list[FleetCarOut] = []
    for car in cars:
        assigned_driver = occupied_by_car_id.get(car.id)
        result.append(
            FleetCarOut(
                id=car.id,
                plate_number=car.plate_number,
                make=car.make,
                model=car.model,
                production_year=car.production_year,
                engine=car.engine,
                transmission=car.transmission,
                color=car.color,
                comfort_class=car.comfort_class,
                technical_status=car.technical_status,
                is_active=car.is_active,
                is_occupied=assigned_driver is not None,
                assigned_driver_id=assigned_driver.id if assigned_driver else None,
                assigned_driver_name=_driver_name(assigned_driver) if assigned_driver else None,
            )
        )
    return result


@router.post("/tariffs", response_model=TariffOut)
def upsert_tariff(
    payload: TariffCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
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
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    drivers = db.scalars(select(Driver).order_by(Driver.id.desc())).all()
    return [
        {
            "id": driver.id,
            "user_id": driver.user_id,
            "driver_name": _driver_name(driver),
            "email": driver.user.username if driver.user else None,
            "license_number": driver.license_number,
            "rating": driver.rating,
            "status": driver.status,
            "car_id": driver.car_id,
            "approved_car_class": driver.approved_car_class,
            "requested_car_class": driver.requested_car_class,
            "uses_own_car": driver.uses_own_car,
        }
        for driver in drivers
    ]


@router.patch("/drivers/{driver_id}/assign-car", response_model=dict)
def assign_car_to_driver(
    driver_id: int,
    payload: AssignFleetCarRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    driver = db.get(Driver, driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    car = db.get(Car, payload.car_id)
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")
    if not car.is_active:
        raise HTTPException(status_code=400, detail="Car is not active")

    occupied_driver = db.scalar(select(Driver).where(Driver.car_id == car.id, Driver.id != driver.id))
    if occupied_driver:
        raise HTTPException(status_code=400, detail="Car is already assigned to another driver")

    driver.car_id = car.id
    driver.uses_own_car = False
    driver.approved_car_class = car.comfort_class
    driver.status = DriverStatus.FREE
    db.commit()
    return {"message": "Car assigned to driver", "driver_id": driver_id, "car_id": car.id}


@router.patch("/drivers/{driver_id}/approve-class", response_model=dict)
def approve_driver_class(
    driver_id: int,
    payload: DriverClassApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    driver = db.get(Driver, driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    pending_application = db.scalar(
        select(DriverClassApplication).where(
            DriverClassApplication.driver_id == driver.id,
            DriverClassApplication.status == DriverClassApplicationStatus.PENDING,
        )
    )
    requested_class = pending_application.requested_car_class if pending_application else driver.requested_car_class

    if not payload.approve:
        if not requested_class:
            raise HTTPException(status_code=400, detail="No pending class request to reject")

        review_note = payload.review_note or "Rejected by administrator"
        driver.status = DriverStatus.INACTIVE
        driver.requested_car_class = requested_class

        if pending_application:
            pending_application.status = DriverClassApplicationStatus.REJECTED
            pending_application.review_note = review_note
            pending_application.reviewed_by = current_user.id
            pending_application.reviewed_at = datetime.now(timezone.utc)
        else:
            db.add(
                DriverClassApplication(
                    driver_id=driver.id,
                    requested_car_class=requested_class,
                    own_car_make=driver.own_car_make or "",
                    own_car_model=driver.own_car_model or "",
                    own_car_year=driver.own_car_year or 0,
                    own_car_plate=driver.own_car_plate or "",
                    own_car_engine=driver.own_car_engine or "",
                    own_car_transmission=driver.own_car_transmission or "",
                    status=DriverClassApplicationStatus.REJECTED,
                    reviewed_by=current_user.id,
                    review_note=review_note,
                    reviewed_at=datetime.now(timezone.utc),
                )
            )

        db.commit()
        return {
            "message": "Driver class request rejected",
            "driver_id": driver.id,
            "approved_car_class": driver.approved_car_class,
        }

    approved_class = payload.approved_car_class or requested_class or driver.approved_car_class
    if requested_class and _class_rank(approved_class) > _class_rank(requested_class):
        raise HTTPException(status_code=400, detail="Cannot approve class higher than requested class")

    driver.approved_car_class = approved_class
    driver.status = DriverStatus.FREE
    review_note = payload.review_note or "Approved by administrator"

    if pending_application:
        pending_application.status = DriverClassApplicationStatus.APPROVED
        pending_application.review_note = review_note
        pending_application.reviewed_by = current_user.id
        pending_application.reviewed_at = datetime.now(timezone.utc)
    else:
        db.add(
            DriverClassApplication(
                driver_id=driver.id,
                requested_car_class=approved_class,
                own_car_make=driver.own_car_make or "",
                own_car_model=driver.own_car_model or "",
                own_car_year=driver.own_car_year or 0,
                own_car_plate=driver.own_car_plate or "",
                own_car_engine=driver.own_car_engine or "",
                own_car_transmission=driver.own_car_transmission or "",
                status=DriverClassApplicationStatus.APPROVED,
                reviewed_by=current_user.id,
                review_note=review_note,
                reviewed_at=datetime.now(timezone.utc),
            )
        )

    db.commit()
    return {
        "message": "Driver class approved",
        "driver_id": driver.id,
        "approved_car_class": driver.approved_car_class,
    }


@router.get("/drivers/me/profile", response_model=DriverProfileOut)
def driver_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DRIVER)),
):
    driver = db.scalar(select(Driver).where(Driver.user_id == current_user.id))
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    assigned_company_car = driver.car
    own_car = None
    if driver.uses_own_car:
        own_car = {
            "make": driver.own_car_make,
            "model": driver.own_car_model,
            "production_year": driver.own_car_year,
            "plate_number": driver.own_car_plate,
            "engine": driver.own_car_engine,
            "transmission": driver.own_car_transmission,
        }

    last_application = db.scalar(
        select(DriverClassApplication)
        .where(DriverClassApplication.driver_id == driver.id)
        .order_by(DriverClassApplication.created_at.desc())
    )

    return DriverProfileOut(
        driver_id=driver.id,
        status=driver.status,
        approved_car_class=driver.approved_car_class,
        requested_car_class=driver.requested_car_class,
        uses_own_car=driver.uses_own_car,
        current_lat=driver.current_lat,
        current_lng=driver.current_lng,
        assigned_company_car=assigned_company_car,
        own_car=own_car,
        last_class_application_status=last_application.status if last_application else None,
        last_class_application_note=last_application.review_note if last_application else None,
    )


@router.patch("/drivers/me/own-car", response_model=dict)
def save_driver_own_car(
    payload: DriverOwnCarRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DRIVER)),
):
    driver = db.scalar(select(Driver).where(Driver.user_id == current_user.id))
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    driver.uses_own_car = True
    driver.car_id = None
    driver.own_car_make = payload.make
    driver.own_car_model = payload.model
    driver.own_car_year = payload.production_year
    driver.own_car_plate = payload.plate_number
    driver.own_car_engine = payload.engine
    driver.own_car_transmission = payload.transmission
    driver.requested_car_class = payload.requested_car_class
    driver.status = DriverStatus.INACTIVE

    pending_application = db.scalar(
        select(DriverClassApplication).where(
            DriverClassApplication.driver_id == driver.id,
            DriverClassApplication.status == DriverClassApplicationStatus.PENDING,
        )
    )
    if pending_application:
        pending_application.status = DriverClassApplicationStatus.REJECTED
        pending_application.review_note = "Автоматично закрито: подано нову заявку"
        pending_application.reviewed_at = datetime.now(timezone.utc)
        pending_application.reviewed_by = None

    class_application = DriverClassApplication(
        driver_id=driver.id,
        requested_car_class=payload.requested_car_class,
        own_car_make=payload.make,
        own_car_model=payload.model,
        own_car_year=payload.production_year,
        own_car_plate=payload.plate_number,
        own_car_engine=payload.engine,
        own_car_transmission=payload.transmission,
        status=DriverClassApplicationStatus.PENDING,
    )
    db.add(class_application)
    db.commit()

    return {
        "message": "Own car submitted for approval",
        "requested_car_class": driver.requested_car_class,
    }


@router.get("/drivers/me/class-applications", response_model=list[DriverClassApplicationOut])
def driver_my_class_applications(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DRIVER)),
):
    driver = db.scalar(select(Driver).where(Driver.user_id == current_user.id))
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    return list(
        db.scalars(
            select(DriverClassApplication)
            .where(DriverClassApplication.driver_id == driver.id)
            .order_by(DriverClassApplication.created_at.desc())
            .limit(limit)
        ).all()
    )


@router.get("/driver-class-applications", response_model=list[DriverClassApplicationOut])
def list_driver_class_applications(
    status_filter: DriverClassApplicationStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    query = select(DriverClassApplication).order_by(DriverClassApplication.created_at.desc()).limit(limit)
    if status_filter:
        query = query.where(DriverClassApplication.status == status_filter)
    return list(db.scalars(query).all())


@router.patch("/driver-class-applications/{application_id}", response_model=DriverClassApplicationOut)
def review_driver_class_application(
    application_id: int,
    payload: DriverClassApplicationReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    application = db.get(DriverClassApplication, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Driver class application not found")
    if application.status != DriverClassApplicationStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only pending class applications can be reviewed")

    driver = db.get(Driver, application.driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    application.reviewed_by = current_user.id
    application.review_note = payload.review_note
    application.reviewed_at = datetime.now(timezone.utc)

    if payload.approve:
        approved_class = payload.approved_car_class or application.requested_car_class
        if _class_rank(approved_class) > _class_rank(application.requested_car_class):
            raise HTTPException(status_code=400, detail="Cannot approve class higher than requested")

        application.status = DriverClassApplicationStatus.APPROVED
        driver.approved_car_class = approved_class
        driver.requested_car_class = application.requested_car_class
        driver.status = DriverStatus.FREE
    else:
        application.status = DriverClassApplicationStatus.REJECTED
        driver.status = DriverStatus.INACTIVE

    db.commit()
    db.refresh(application)
    return application


@router.patch("/drivers/me/location", response_model=dict)
def update_driver_location(
    payload: DriverLocationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DRIVER)),
):
    driver = db.scalar(select(Driver).where(Driver.user_id == current_user.id))
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    if not is_within_lviv(payload.lat, payload.lng):
        raise HTTPException(status_code=400, detail="Driver location must be within Lviv")

    driver.current_lat = payload.lat
    driver.current_lng = payload.lng
    db.commit()
    return {"message": "Driver location updated", "lat": driver.current_lat, "lng": driver.current_lng}


@router.get("/users", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
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
    _: User = Depends(require_roles(UserRole.ADMIN)),
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


@router.get("/driver-applications", response_model=list[DriverApplicationOut])
def list_driver_applications(
    status_filter: DriverApplicationStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    query = select(DriverApplication).order_by(DriverApplication.created_at.desc())
    if status_filter:
        query = query.where(DriverApplication.status == status_filter)
    return list(db.scalars(query).all())


@router.patch("/driver-applications/{application_id}", response_model=DriverApplicationOut)
def review_driver_application(
    application_id: int,
    payload: DriverApplicationReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    application = db.get(DriverApplication, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.status != DriverApplicationStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only pending application can be reviewed")

    application.reviewed_by = current_user.id
    application.reviewed_at = datetime.now(timezone.utc)
    application.review_note = payload.review_note

    if not payload.approve:
        application.status = DriverApplicationStatus.REJECTED
        db.commit()
        db.refresh(application)
        return application

    existing_user = db.scalar(select(User).where(User.username == application.email))
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    existing_driver = db.scalar(select(Driver).where(Driver.license_number == application.license_number))
    if existing_driver:
        raise HTTPException(status_code=400, detail="Driver with this license already exists")

    user = User(
        username=application.email,
        hashed_password=application.hashed_password,
        first_name=application.first_name,
        last_name=application.last_name,
        phone=application.phone,
        role=UserRole.DRIVER,
    )
    db.add(user)
    db.flush()

    db.add(Driver(user_id=user.id, license_number=application.license_number))
    application.status = DriverApplicationStatus.APPROVED

    db.commit()
    db.refresh(application)
    return application


@router.get("/analytics/dashboard", response_model=AdminDashboardOut)
def admin_dashboard_stats(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    avg_distance = db.scalar(
        select(func.coalesce(func.avg(Order.distance_km), 0)).where(Order.status == OrderStatus.COMPLETED)
    )

    rides_by_class_rows = db.execute(
        select(Car.comfort_class, func.count(Order.id))
        .join(Order, Order.car_id == Car.id)
        .where(Order.status == OrderStatus.COMPLETED)
        .group_by(Car.comfort_class)
    ).all()

    daily = db.scalar(
        select(func.coalesce(func.sum(Order.final_cost), 0)).where(
            and_(
                Order.status == OrderStatus.COMPLETED,
                Order.created_at >= day_start,
            )
        )
    )
    monthly = db.scalar(
        select(func.coalesce(func.sum(Order.final_cost), 0)).where(
            and_(
                Order.status == OrderStatus.COMPLETED,
                Order.created_at >= month_start,
            )
        )
    )
    yearly = db.scalar(
        select(func.coalesce(func.sum(Order.final_cost), 0)).where(
            and_(
                Order.status == OrderStatus.COMPLETED,
                Order.created_at >= year_start,
            )
        )
    )

    return AdminDashboardOut(
        avg_distance_km=round(float(avg_distance or 0), 2),
        rides_by_car_class={str(row[0].value): int(row[1]) for row in rides_by_class_rows},
        earnings_by_period={
            "day": float(daily or 0),
            "month": float(monthly or 0),
            "year": float(yearly or 0),
        },
    )


@router.get("/analytics/overview", response_model=AdminAnalyticsOverviewOut)
def admin_analytics_overview(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    now = datetime.now(timezone.utc)
    starts = _period_starts(now)

    revenue_by_period: dict[str, float] = {}
    orders_count_by_period: dict[str, int] = {}
    for period, start_dt in starts.items():
        revenue_by_period[period] = float(
            db.scalar(
                select(func.coalesce(func.sum(Order.final_cost), 0)).where(
                    and_(Order.status == OrderStatus.COMPLETED, Order.created_at >= start_dt)
                )
            )
            or 0
        )
        orders_count_by_period[period] = int(
            db.scalar(select(func.count(Order.id)).where(Order.created_at >= start_dt)) or 0
        )

    by_class_rows = db.execute(
        select(Order.requested_comfort_class, func.count(Order.id))
        .group_by(Order.requested_comfort_class)
        .order_by(desc(func.count(Order.id)))
    ).all()

    return AdminAnalyticsOverviewOut(
        revenue_by_period=revenue_by_period,
        orders_count_by_period=orders_count_by_period,
        orders_by_car_class={row[0].value: int(row[1]) for row in by_class_rows},
    )


@router.get("/analytics/order-logs", response_model=list[AdminOrderLogOut])
def admin_order_logs(
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    rows = db.scalars(select(Order).order_by(Order.created_at.desc()).limit(limit)).all()
    return [
        AdminOrderLogOut(
            order_id=row.id,
            status=row.status,
            created_at=row.created_at,
            pickup_address=row.pickup_address,
            dropoff_address=row.dropoff_address,
            distance_km=row.distance_km,
            estimated_cost=float(row.estimated_cost),
            final_cost=float(row.final_cost) if row.final_cost is not None else None,
            driver_id=row.driver_id,
            client_id=row.client_id,
        )
        for row in rows
    ]


@router.get("/analytics/drivers/{driver_id}", response_model=AdminDriverDetailsOut)
def admin_driver_details(
    driver_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    driver = db.get(Driver, driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    total_trips = int(
        db.scalar(
            select(func.count(Order.id)).where(
                and_(Order.driver_id == driver.id, Order.status == OrderStatus.COMPLETED)
            )
        )
        or 0
    )
    avg_rating = float(
        db.scalar(select(func.coalesce(func.avg(Review.rating), 0)).where(Review.driver_id == driver.id)) or 0
    )
    reviews = list(
        db.scalars(
            select(Review).where(Review.driver_id == driver.id).order_by(Review.created_at.desc()).limit(20)
        ).all()
    )

    active_car = None
    if driver.uses_own_car:
        active_car = " ".join(
            str(part)
            for part in [driver.own_car_make, driver.own_car_model, f"({driver.own_car_plate})"]
            if part
        )
    elif driver.car:
        active_car = f"{driver.car.make} {driver.car.model} ({driver.car.plate_number})".strip()

    return AdminDriverDetailsOut(
        driver_id=driver.id,
        driver_name=_driver_name(driver),
        email=driver.user.username if driver.user else "",
        total_trips=total_trips,
        active_car=active_car,
        avg_rating=min(5.0, max(0.0, round(avg_rating, 2))),
        recent_reviews=reviews,
    )


@router.get("/analytics/drivers", response_model=list[AdminDriverStatsOut])
def admin_driver_statistics(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    rows = db.execute(
        select(
            Driver.id,
            Driver.user_id,
            User.first_name,
            User.last_name,
            func.count(Order.id).label("completed_orders"),
            func.coalesce(func.sum(Order.final_cost), 0).label("earned_amount"),
            Driver.rating,
            User.username,
        )
        .join(User, User.id == Driver.user_id)
        .outerjoin(Order, and_(Order.driver_id == Driver.id, Order.status == OrderStatus.COMPLETED))
        .group_by(Driver.id, Driver.user_id, User.first_name, User.last_name, Driver.rating, User.username)
        .order_by(desc("earned_amount"))
    ).all()

    return [
        AdminDriverStatsOut(
            driver_id=row.id,
            user_id=row.user_id,
            driver_name=f"{row.first_name} {row.last_name}".strip(),
            completed_orders=int(row.completed_orders or 0),
            earned_amount=float(row.earned_amount or 0),
            avg_rating=float(row.rating or 0),
            email=row.username,
        )
        for row in rows
    ]


@router.get("/reviews", response_model=list[ReviewOut])
def list_reviews(
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    return list(db.scalars(select(Review).order_by(Review.created_at.desc()).limit(limit)).all())


@router.get("/reviews/me", response_model=list[ReviewOut])
def list_my_driver_reviews(
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DRIVER)),
):
    driver = db.scalar(select(Driver).where(Driver.user_id == current_user.id))
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    return list(
        db.scalars(
            select(Review).where(Review.driver_id == driver.id).order_by(Review.created_at.desc()).limit(limit)
        ).all()
    )
