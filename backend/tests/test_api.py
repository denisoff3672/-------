from fastapi.testclient import TestClient


def register_user(client: TestClient, username: str, role: str, phone: str = "", license_number: str = ""):
    payload = {
        "username": username,
        "password": "secret123",
        "role": role,
    }
    if phone:
        payload["phone"] = phone
    if license_number:
        payload["license_number"] = license_number

    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201, response.text


def login(client: TestClient, username: str):
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "secret123"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_register_and_me(client: TestClient):
    register_user(client, "client1", "client", phone="+380501112233")

    token = login(client, "client1")
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "client1"
    assert data["role"] == "client"


def test_order_flow_with_auto_driver_assignment(client: TestClient):
    register_user(client, "admin1", "admin")
    register_user(client, "driver1", "driver", license_number="DRV-001")
    register_user(client, "client2", "client", phone="+380502224455")

    admin_token = login(client, "admin1")
    driver_token = login(client, "driver1")
    client_token = login(client, "client2")

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
        f"/api/management/drivers/{driver_id}/assign-car?car_id={car_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert assign_response.status_code == 200, assign_response.text

    status_response = client.patch(
        "/api/management/drivers/me/status",
        json={"status": "free"},
        headers={"Authorization": f"Bearer {driver_token}"},
    )
    assert status_response.status_code == 200

    order_response = client.post(
        "/api/orders",
        json={
            "pickup_address": "Kyiv Railway Station",
            "dropoff_address": "Boryspil Airport",
            "pickup_lat": 50.4412,
            "pickup_lng": 30.4888,
            "dropoff_lat": 50.345,
            "dropoff_lng": 30.8947,
            "comfort_class": "standard",
        },
        headers={"Authorization": f"Bearer {client_token}"},
    )

    assert order_response.status_code == 201, order_response.text
    order = order_response.json()
    assert order["driver_id"] is not None
    assert order["status"] == "in_progress"


def test_client_requires_phone(client: TestClient):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "bad_client",
            "password": "secret123",
            "role": "client",
        },
    )
    assert response.status_code == 400
