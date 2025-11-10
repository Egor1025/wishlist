from datetime import datetime, timezone
from decimal import Decimal


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


def test_validation_error(client):
    r = client.post("/wishes", json={"title": None})
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "validation_error"


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


def test_title_length_boundaries(client):
    r = client.post("/wishes", json={"title": "a"})
    assert r.status_code == 201

    r = client.post("/wishes", json={"title": "a" * 50})
    assert r.status_code == 201

    r = client.post("/wishes", json={"title": ""})
    assert r.status_code == 422


def test_link_url_validation(client):
    r = client.post(
        "/wishes", json={"title": "with link", "link": "https://example.com"}
    )
    assert r.status_code == 201

    bad_links = [
        "example.com",
        "ftp://example.com",
        "javascript:alert(1)",
        "http//missing-colon.com",
    ]

    for link in bad_links:
        r = client.post("/wishes", json={"title": "bad link", "link": link})
        assert r.status_code == 422, r.text


def test_notes_length_validation(client):
    ok_notes = "x" * 1000
    too_long_notes = "x" * 1001

    r = client.post("/wishes", json={"title": "ok notes", "notes": ok_notes})
    assert r.status_code == 201

    r = client.post(
        "/wishes", json={"title": "too long notes", "notes": too_long_notes}
    )
    assert r.status_code == 422, r.text
