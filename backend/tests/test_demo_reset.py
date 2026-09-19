from __future__ import annotations

from app.models import DEMO_APPLICATION_ID, DEMO_USER_ID


def test_reset_is_idempotent(client):
    first = client.post("/api/demo/reset").json()
    second = client.post("/api/demo/reset").json()
    assert first == second
    assert first["user_id"] == DEMO_USER_ID
    app_row = client.get(f"/api/applications/{DEMO_APPLICATION_ID}").json()
    assert app_row["status"] == "submitted"
    assert app_row["user"]["display_name"] == "林小竹"
