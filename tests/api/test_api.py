"""HTTP-level tests. Skipped if FastAPI/httpx are not installed."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from parking.api.app import create_app  # noqa: E402
from parking.application.auth_service import AuthService  # noqa: E402
from parking.application.container import Services  # noqa: E402
from parking.infrastructure.in_memory import InMemoryUserRepository  # noqa: E402
from parking.infrastructure.security import InMemoryTokenDenylist  # noqa: E402
from tests.fakes import FakeHasher, FakeTokenService  # noqa: E402

PASSWORD = "secret123"


@pytest.fixture
def client(reservations, access, sensors, occupancy):
    auth = AuthService(InMemoryUserRepository(), FakeHasher(), FakeTokenService(), InMemoryTokenDenylist())
    return TestClient(create_app(Services(reservations, access, sensors, occupancy, auth=auth)))


def login(client, username="ana"):
    client.post("/api/auth/register", json={"username": username, "password": PASSWORD})
    token = client.post("/api/auth/login", json={"username": username, "password": PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_map_requires_token(client):
    r = client.get("/api/map")
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


def test_map_lists_zones_for_logged_in_user(client):
    body = client.get("/api/map", headers=login(client)).json()
    assert [z["zone"] for z in body["zones"]] == ["A", "B"]
    assert body["zones"][0]["free"] == 3


def test_security_headers_present(client):
    r = client.get("/api/map", headers=login(client))
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"


def test_reservation_requires_token(client):
    r = client.post("/api/reservations", json={"spot_code": "A-01"})
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


def test_register_login_me_logout(client):
    h = login(client)
    assert client.get("/api/auth/me", headers=h).json() == {"username": "ana"}
    assert client.post("/api/auth/logout", headers=h).status_code == 204
    assert client.get("/api/auth/me", headers=h).status_code == 401


def test_wrong_password_returns_401(client):
    client.post("/api/auth/register", json={"username": "ana", "password": PASSWORD})
    r = client.post("/api/auth/login", json={"username": "ana", "password": "wrong-pass-1"})
    assert r.status_code == 401


def test_weak_password_returns_400(client):
    r = client.post("/api/auth/register", json={"username": "ana", "password": "abc"})
    assert r.status_code == 400


def test_reserve_enter_exit_flow(client):
    h = login(client)
    r = client.post("/api/reservations", json={"spot_code": "A-01"}, headers=h)
    assert r.status_code == 201 and r.json()["user_code"] == "ana"
    rid = r.json()["id"]
    assert client.post(f"/api/reservations/{rid}/entry", headers=h).json()["status"] == "CONFIRMED"
    assert client.post(f"/api/reservations/{rid}/exit", headers=h).json()["status"] == "COMPLETED"
    assert client.get("/api/reservations", headers=h).json() == []


def test_user_cannot_touch_someone_elses_reservation(client):
    ana, bob = login(client, "ana"), login(client, "bob")
    rid = client.post("/api/reservations", json={"spot_code": "A-01"}, headers=ana).json()["id"]
    assert client.get(f"/api/reservations/{rid}", headers=bob).status_code == 403
    assert client.post(f"/api/reservations/{rid}/entry", headers=bob).status_code == 403
    assert client.get("/api/reservations", headers=bob).json() == []


def test_double_reservation_returns_409(client):
    ana, bob = login(client, "ana"), login(client, "bob")
    client.post("/api/reservations", json={"spot_code": "A-01"}, headers=ana)
    assert client.post("/api/reservations", json={"spot_code": "A-01"}, headers=bob).status_code == 409


def test_unknown_spot_returns_404(client):
    h = login(client)
    assert client.post("/api/reservations", json={"spot_code": "Z-99"}, headers=h).status_code == 404


def test_expired_entry_returns_410(client, clock):
    h = login(client)
    rid = client.post("/api/reservations", json={"spot_code": "A-01"}, headers=h).json()["id"]
    clock.advance(minutes=61)
    assert client.post(f"/api/reservations/{rid}/entry", headers=h).status_code == 410


def test_index_page_served(client):
    assert "Campus Parking Monitor" in client.get("/").text


def test_open_data_not_configured_returns_404(client):
    assert client.get("/api/open-data/sources").status_code == 404
