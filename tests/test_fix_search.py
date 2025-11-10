import pytest


def test_search_finds_matching_titles(client):
    r1 = client.post("/wishes", json={"title": "Nintendo Switch"})
    assert r1.status_code == 201
    r2 = client.post("/wishes", json={"title": "PlayStation 5"})
    assert r2.status_code == 201

    r = client.get("/wishes/search", params={"q": "Switch"})
    assert r.status_code == 200

    data = r.json()
    assert len(data) == 1
    assert data[0]["title"] == "Nintendo Switch"


@pytest.mark.parametrize(
    "payload",
    [
        "%' OR 1=1--",
        "%' UNION SELECT 1,2,3--",
        "%'; DROP TABLE wishes;--",
    ],
)
def test_search_sql_injection(client, payload):
    r1 = client.post("/wishes", json={"title": "Safe Item"})
    assert r1.status_code == 201

    r = client.get("/wishes/search", params={"q": payload})
    assert r.status_code == 200

    data = r.json()
    assert isinstance(data, list)


def test_search_rejects_too_long_query(client):
    q = "x" * 101
    r = client.get("/wishes/search", params={"q": q})
    assert r.status_code == 422
