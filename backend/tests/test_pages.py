from __future__ import annotations


def test_core_pages_ok(client):
    for path in [
        "/",
        "/eligibility",
        "/apply",
        "/learning",
        "/privacy",
        "/demo-chat",
        "/events",
        "/notifications",
        "/admin/login",
        "/demo/readiness",
        "/attestation",
        "/applications/app_demo_001",
    ]:
        response = client.get(path)
        assert response.status_code == 200, path
        assert "合成資料" in response.text or "Demo" in response.text


def test_security_headers(client):
    response = client.get("/")
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "content-security-policy" in response.headers
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
