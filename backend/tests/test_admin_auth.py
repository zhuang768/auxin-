from __future__ import annotations

from app.models import DEMO_APPLICATION_ID


def test_admin_requires_login(client):
    dashboard = client.get("/admin", follow_redirects=False)
    assert dashboard.status_code == 303
    assert "/admin/login" in dashboard.headers["location"]

    review = client.post(
        f"/api/applications/{DEMO_APPLICATION_ID}/review",
        json={"to_status": "under_review"},
    )
    assert review.status_code == 401
