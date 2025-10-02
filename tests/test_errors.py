from random import sample

from fastapi.testclient import TestClient

from app.main import _DB, app

client = TestClient(app)


def clear_db():
    _DB["wishes"].clear()


def test_not_found_and_nonexist_wish():
    def check(r):
        assert r.status_code == 404
        body = r.json()
        assert "error" in body and body["error"]["code"] == "not_found"

    check(client.get("/wishes/999"))
    check(client.patch("/wishes/777", json={"title": "_"}))


def test_validation_error():
    r = client.post("/wishes", json={"title": None})
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "validation_error"


def test_post_and_double_delete():
    cake = {"title": "cheese cake"}
    r = client.post("/wishes", json=cake)
    assert r.status_code == 201

    url = f"/wishes/{r.json()['id']}"
    r = client.delete(url)
    assert r.status_code == 204
    assert r.content == b""

    r = client.delete(url)
    assert r.status_code == 404


def test_crud_wish():
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
        "price_estimate": 5_500_000,
        "notes": notes,
    }

    r = client.delete(url)
    assert r.status_code == 204

    r = client.get(url)
    assert r.status_code == 404


def test_price_lower_filter():
    clear_db()

    for i in sample(range(1, 10), 9):
        client.post("/wishes", json={"title": f"wish{i}", "price_estimate": i})

    r = client.get("/wishes", params={"price<": 6})
    assert r.status_code == 200
    assert len(r.json()) == 5
