"""HTTP-level tests. Skipped if FastAPI/httpx are not installed."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from parking.api.app import create_app  # noqa: E402
from parking.application.container import Services  # noqa: E402


@pytest.fixture
def client(reservations, access, sensors, occupancy):
    app = create_app(Services(reservations, access, sensors, occupancy))
    return TestClient(app)


def test_map_lists_zones(client):
    body = client.get("/api/map").json()
    assert [z["zone"] for z in body["zones"]] == ["A", "B"]
    assert body["zones"][0]["free"] == 3


def test_reserve_enter_exit_flow(client):
    r = client.post("/api/reservations", json={"user_code": "u1", "spot_code": "A-01"})
    assert r.status_code == 201
    rid = r.json()["id"]
    assert client.post(f"/api/reservations/{rid}/entry").json()["status"] == "CONFIRMED"
    assert client.post(f"/api/reservations/{rid}/exit").json()["status"] == "COMPLETED"
    assert client.get("/api/reservations").json() == []


def test_double_reservation_returns_409(client):
    client.post("/api/reservations", json={"user_code": "u1", "spot_code": "A-01"})
    r = client.post("/api/reservations", json={"user_code": "u2", "spot_code": "A-01"})
    assert r.status_code == 409


def test_unknown_spot_returns_404(client):
    r = client.post("/api/reservations", json={"user_code": "u1", "spot_code": "Z-99"})
    assert r.status_code == 404


def test_expired_entry_returns_410(client, clock):
    rid = client.post("/api/reservations", json={"user_code": "u1", "spot_code": "A-01"}).json()["id"]
    clock.advance(minutes=61)
    assert client.post(f"/api/reservations/{rid}/entry").status_code == 410


def test_index_page_served(client):
    assert "Campus Parking Monitor" in client.get("/").text


def test_open_data_not_configured_returns_404(client):
    assert client.get("/api/open-data/sources").status_code == 404
