import json
from datetime import datetime, timezone
from decimal import Decimal
from random import sample

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.database import get_db as _get_db
from app.main import app


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[_get_db] = override_get_db

    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def test_invalid_inputs_return_4xx(client):

    first = {"title": "first"}
    client.post("/wishes", json=first)

    bad_params = [
        {"title": ""},
        {"title": 0},
        {"title": None},
        {"title": "a" * 51},
        {"title": [], "notes": "some text here"},
        {"title": "title", "price_estimate": -1},
        {"title": "title", "link": 0, "notes": 0},
    ]

    for param in bad_params:
        r = client.patch("/wishes/1", json=param)
        assert 400 <= r.status_code < 500, r.text

    bad_params += [
        {},
        {1: "one"},
        {"notes": "some text"},
        {"param1": 1, "param2": 2, "param3": 3},
        {"link": "https://google.com/", "price_estimate": 9999999999},
    ]

    for param in bad_params:
        r = client.patch("/wishes/0", json=param)
        assert 400 <= r.status_code < 500, r.text

        r = client.post("/wishes", json=param)
        assert 400 <= r.status_code < 500, r.text


def test_audit_log_emitted_on_delete(client, caplog):
    wid = client.post("/wishes", json={"title": "x"}).json()["id"]
    with caplog.at_level("INFO", logger="app.audit"):
        r = client.delete(f"/wishes/{wid}")
    assert r.status_code == 204

    records = [rec for rec in caplog.records if rec.name == "app.audit"]
    assert records
    event = json.loads(records[-1].message)
    assert event["action"] == "delete" and event["object_id"] == wid


def test_not_found_and_nonexist_wish(client):
    def check(r):
        assert r.status_code == 404
        body = r.json()
        assert "error" in body and body["error"]["code"] == "not_found"

    check(client.get("/wishes/999"))
    check(client.patch("/wishes/777", json={"title": "_"}))


def test_validation_error(client):
    r = client.post("/wishes", json={"title": None})
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "validation_error"


def test_post_and_double_delete(client):
    cake = {"title": "cheese cake"}
    r = client.post("/wishes", json=cake)
    assert r.status_code == 201

    url = f"/wishes/{r.json()['id']}"
    r = client.delete(url)
    assert r.status_code == 204
    assert r.content == b""

    r = client.delete(url)
    assert r.status_code == 404


def test_crud_wish(client):
    bmw = {
        "title": "bmw 430i",
        "price_estimate": 5_000_000,
    }
    r = client.post("/wishes", json=bmw)
    assert r.status_code == 201

    notes = "BMW 4 серии 430i xDrive G22, G23, G26, 2021\nЦвет: белый/черный"
    bmw_extra = {
        "link": "https://www.bmw.de/",
        "price_estimate": 5_500_000,
        "notes": notes,
    }
    _id = r.json()["id"]
    url = f"/wishes/{_id}"
    r = client.patch(url, json=bmw_extra)
    assert r.status_code == 200

    r = client.get(url)
    assert r.status_code == 200
    assert r.json() == {
        "id": _id,
        "title": "bmw 430i",
        "link": "https://www.bmw.de/",
        "price_estimate": "5500000.00",
        "updated_at": r.json()["updated_at"],
        "notes": notes,
    }

    r = client.delete(url)
    assert r.status_code == 204

    r = client.get(url)
    assert r.status_code == 404


def test_price_lower_filter(client):

    for i in sample(range(1, 10), 9):
        client.post("/wishes", json={"title": f"wish{i}", "price_estimate": i})

    r = client.get("/wishes", params={"price<": 6})
    assert r.status_code == 200
    assert len(r.json()) == 5


def test_error_envelope_safe_output(client):
    r = client.get("/wishes/424242")
    assert r.status_code == 404, r.text
    assert r.headers.get("content-type", "").startswith("application/json")

    body = r.json()
    assert "error" in body, body
    forbidden_error_keys = {"trace", "stack", "debug", "exception", "details"}
    assert not (forbidden_error_keys & set(body["error"].keys())), body["error"]
    assert "Traceback" not in r.text

    r = client.post("/wishes", json={"title": None})
    assert r.status_code == 422, r.text
    assert r.headers.get("content-type", "").startswith("application/json")

    body = r.json()
    assert "error" in body, body
    assert not (forbidden_error_keys & set(body["error"].keys())), body["error"]
    assert "Traceback" not in r.text


def test_price_normalization(client):
    r = client.post(
        "/wishes", json={"title": "Нормализация цены", "price_estimate": 10.127}
    )
    assert r.status_code == 201
    data = r.json()

    price = Decimal(str(data["price_estimate"]))
    assert price == Decimal("10.13")


def test_datetime_normalization(client):
    r = client.post("/wishes", json={"title": "UTC"})
    assert r.status_code == 201
    updated_at = r.json()["updated_at"]

    ts = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    assert ts.tzinfo is not None
    assert ts.utcoffset() == timezone.utc.utcoffset(ts)


def test_decimal_serialization(client):
    r = client.post(
        "/wishes", json={"title": "decimal->float", "price_estimate": 19.995}
    )
    assert r.status_code == 201
    data = r.json()

    price = data["price_estimate"]
    assert isinstance(price, str)
    assert Decimal(price).quantize(Decimal("0.01")) == Decimal("20.00")
