from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def login(username="alice", password="123456"):
    response = client.post(
        "/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["data"]["token"]


def test_login_returns_token():
    token = login()

    assert token == "demo-token-alice"


def test_user_can_read_own_profile():
    token = login()

    response = client.get("/users/1", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["data"]["username"] == "alice"


def test_user_cannot_read_another_user_profile():
    token = login()

    response = client.get("/users/2", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert response.json()["code"] == 1004


def test_user_cannot_read_another_user_orders():
    token = login()

    response = client.get(
        "/orders",
        params={"user_id": 2},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == 1004


def test_orders_require_user_id_query_param():
    token = login()

    response = client.get("/orders", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 422
