from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.entities import User, UserRole


def login(client: TestClient, email: str, password: str):
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    return data["accessToken"]


def create_admin(db_session: Session, email: str = "admin@taxi.local", password: str = "admin123") -> None:
    admin = User(
        username=email,
        hashed_password=hash_password(password),
        first_name="System",
        last_name="Admin",
        phone="+380500000000",
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    db_session.commit()


def test_predefined_client_login_and_me(client: TestClient):
    token = login(client, "client@taxi.local", "client123")
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "client@taxi.local"
    assert data["role"] == "client"


def test_register_login_and_refresh_cookie(client: TestClient):
    register_response = client.post(
        "/api/auth/register",
        json={
            "first_name": "New",
            "last_name": "Client",
            "phone": "+380501111111",
            "email": "newuser@example.com",
            "password": "secret123",
        },
    )
    assert register_response.status_code == 201, register_response.text
    assert register_response.json()["role"] == "client"
    assert "refreshToken" in register_response.headers.get("set-cookie", "")

    refresh_response = client.post("/api/auth/refresh")
    assert refresh_response.status_code == 200, refresh_response.text
    payload = refresh_response.json()
    assert payload["email"] == "newuser@example.com"
    assert payload["role"] == "client"
    assert payload.get("accessToken")


def test_order_flow_with_auto_driver_assignment(client: TestClient, db_session: Session):
    create_admin(db_session)
    admin_token = login(client, "admin@taxi.local", "admin123")
    driver_token = login(client, "driver@taxi.local", "driver123")
    client_token = login(client, "client@taxi.local", "client123")

    car_response = client.post(
        "/api/management/cars",
        json={
            "plate_number": "AA1234BB",
            "model": "Toyota Prius",
            "color": "White",
            "comfort_class": "standard",
            "technical_status": "good",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert car_response.status_code == 200, car_response.text
    car_id = car_response.json()["id"]

    tariffs_response = client.post(
        "/api/management/tariffs",
        json={
            "comfort_class": "standard",
            "base_fare": 45,
            "price_per_km": 15,
            "price_per_minute": 2,
            "night_multiplier": 1.15,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert tariffs_response.status_code == 200, tariffs_response.text

    drivers_response = client.get(
        "/api/management/drivers",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert drivers_response.status_code == 200
    driver_id = drivers_response.json()[0]["id"]

    assign_response = client.patch(
        f"/api/management/drivers/{driver_id}/assign-car",
        json={"car_id": car_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert assign_response.status_code == 200, assign_response.text

    location_response = client.patch(
        "/api/management/drivers/me/location",
        json={"lat": 49.8397, "lng": 24.0297},
        headers={"Authorization": f"Bearer {driver_token}"},
    )
    assert location_response.status_code == 200, location_response.text

    status_response = client.patch(
        "/api/management/drivers/me/status",
        json={"status": "free"},
        headers={"Authorization": f"Bearer {driver_token}"},
    )
    assert status_response.status_code == 200

    order_response = client.post(
        "/api/orders",
        json={
            "pickup_address": "Lviv Railway Station",
            "dropoff_address": "Lviv Airport",
            "pickup_lat": 49.8397,
            "pickup_lng": 24.0297,
            "dropoff_lat": 49.8125,
            "dropoff_lng": 23.9722,
            "comfort_class": "standard",
        },
        headers={"Authorization": f"Bearer {client_token}"},
    )

    assert order_response.status_code == 201, order_response.text
    order = order_response.json()
    assert order["driver_id"] is not None
    assert order["status"] == "pending"

    second_order_response = client.post(
        "/api/orders",
        json={
            "pickup_address": "Lviv Center",
            "dropoff_address": "Stryiskyi Park",
            "pickup_lat": 49.8397,
            "pickup_lng": 24.0297,
            "dropoff_lat": 49.8257,
            "dropoff_lng": 24.0299,
            "comfort_class": "standard",
        },
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert second_order_response.status_code == 400
    assert second_order_response.json()["detail"] == "Client already has an active order"


def test_login_invalid_email_or_password(client: TestClient):
    response = client.post(
        "/api/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "wrongpass",
        },
    )
    assert response.status_code == 401


def test_driver_application_approve_flow(client: TestClient, db_session: Session):
    create_admin(db_session)
    admin_token = login(client, "admin@taxi.local", "admin123")

    create_application = client.post(
        "/api/auth/driver-applications",
        json={
            "first_name": "Ivan",
            "last_name": "Driver",
            "phone": "+380509999999",
            "email": "pending-driver@example.com",
            "password": "secret123",
            "license_series": "LV",
            "license_number": "AB123456",
        },
    )
    assert create_application.status_code == 201, create_application.text
    application_id = create_application.json()["id"]
    assert create_application.json()["status"] == "pending"

    review_response = client.patch(
        f"/api/management/driver-applications/{application_id}",
        json={"approve": True, "review_note": "Документи валідні"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert review_response.status_code == 200, review_response.text
    assert review_response.json()["status"] == "approved"

    login_driver_response = client.post(
        "/api/auth/login",
        json={"email": "pending-driver@example.com", "password": "secret123"},
    )
    assert login_driver_response.status_code == 200, login_driver_response.text
    assert login_driver_response.json()["role"] == "driver"


def test_order_points_must_be_within_lviv(client: TestClient):
    client_token = login(client, "client@taxi.local", "client123")
    response = client.post(
        "/api/orders",
        json={
            "pickup_address": "Kyiv Railway Station",
            "dropoff_address": "Lviv Airport",
            "pickup_lat": 50.4412,
            "pickup_lng": 30.4888,
            "dropoff_lat": 49.8125,
            "dropoff_lng": 23.9722,
            "comfort_class": "standard",
        },
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Pickup point must be within Lviv"
