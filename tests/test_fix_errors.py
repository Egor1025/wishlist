def test_not_found_and_nonexist_wish(client):
    def check(r):
        assert r.status_code == 404
        body = r.json()
        assert "error" in body and body["error"]["code"] == "not_found"

    check(client.get("/wishes/999"))
    check(client.patch("/wishes/777", json={"title": "_"}))


def test_error_envelope_safe_output(client):
    r = client.get("/wishes/999")
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


def test_error_has_correlation_id(client):
    r = client.get("/wishes/999")
    assert r.status_code == 404

    cid_header = r.headers.get("x-correlation-id")
    assert cid_header

    body = r.json()
    assert "error" in body
    assert body["error"].get("correlation_id") == cid_header


def test_error_logs_do_not_contain_request_body(client, caplog):
    secret = "VERY-SECRET-NOTES"
    with caplog.at_level("INFO", logger="app.api"):
        r = client.post("/wishes", json={"title": None, "notes": secret})

    assert 400 <= r.status_code < 500

    messages = " ".join(
        rec.getMessage() for rec in caplog.records if rec.name == "app.api"
    )
    assert secret not in messages
