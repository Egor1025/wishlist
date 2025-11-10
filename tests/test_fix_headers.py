def test_security_headers_present(client):
    r = client.get("/health")
    assert r.status_code == 200
    headers = r.headers

    expected = [
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
        "Permissions-Policy",
        "Strict-Transport-Security",
        "Content-Security-Policy",
    ]
    for h in expected:
        assert h in headers, f"{h} missing"
