from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_not_found_item():
    r = client.get("/wishes/999")
    assert r.status_code == 404
    body = r.json()
    assert "error" in body and body["error"]["code"] == "not_found"


def test_validation_error():
    r = client.post("/wishes", json={"title": None})
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "validation_error"
