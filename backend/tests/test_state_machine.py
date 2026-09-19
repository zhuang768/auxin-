from __future__ import annotations

from app.models import DEMO_APPLICATION_ID


def test_legal_and_illegal_transitions(client):
    current = client.get(f"/api/applications/{DEMO_APPLICATION_ID}").json()
    assert current["status"] == "submitted"

    illegal = client.post(f"/api/applications/{DEMO_APPLICATION_ID}/review", json={"to_status": "approved"})
    assert illegal.status_code in {401, 403}

    login_page = client.get("/admin/login")
    token = login_page.text.split('name="csrf_token" value="')[1].split('"')[0]
    login = client.post(
        "/admin/login",
        data={"csrf_token": token, "username": "demo-admin", "password": "demo-admin-not-for-production"},
        follow_redirects=True,
    )
    assert login.status_code == 200

    jumped = client.post(f"/api/applications/{DEMO_APPLICATION_ID}/review", json={"to_status": "approved"})
    assert jumped.status_code in {403, 409}

    ok = client.post(f"/api/applications/{DEMO_APPLICATION_ID}/review", json={"to_status": "under_review"})
    assert ok.status_code == 200
    assert ok.json()["status"] == "under_review"

    ok2 = client.post(
        f"/api/applications/{DEMO_APPLICATION_ID}/review",
        json={"to_status": "needs_revision", "revision_reason": "請回到安全入口查看。"},
    )
    assert ok2.status_code == 200
    assert ok2.json()["status"] == "needs_revision"

    resubmit = client.post(f"/api/applications/{DEMO_APPLICATION_ID}/submit")
    assert resubmit.status_code == 200
    assert resubmit.json()["status"] == "submitted"
