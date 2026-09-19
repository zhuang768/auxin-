from __future__ import annotations

import pytest

from app.db import FORBIDDEN_RISK_COLUMNS, db_session, table_columns


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] in {"ok", "degraded"}


def test_home_and_demo_chat_render(client):
    home = client.get("/")
    chat = client.get("/demo-chat")
    assert home.status_code == 200
    assert "竹青安心GO" in home.text
    assert "合成資料" in home.text
    assert chat.status_code == 200
    assert "demo-chat-input" in chat.text


def test_risk_event_accepts_whitelist(client):
    response = client.post(
        "/api/risk-events",
        json={
            "category": "phone",
            "action": "masked",
            "occurred_at": "2026-09-18T12:00:00Z",
            "client_version": "1.0.0",
            "demo_session_id": "demo-session-linxiaozhu",
        },
    )
    assert response.status_code == 200
    event = response.json()["event"]
    assert "prompt" not in event
    assert event["category"] == "phone"


@pytest.mark.parametrize(
    "payload",
    [
        {"raw_prompt": "secret", "category": "phone", "action": "masked", "occurred_at": "2026-09-18T12:00:00Z", "client_version": "1.0.0", "demo_session_id": "demo-session-x"},
        {"prompt": "secret", "category": "phone", "action": "masked", "occurred_at": "2026-09-18T12:00:00Z", "client_version": "1.0.0", "demo_session_id": "demo-session-x"},
        {"matched_text": "0912000111", "category": "phone", "action": "masked", "occurred_at": "2026-09-18T12:00:00Z", "client_version": "1.0.0", "demo_session_id": "demo-session-x"},
        {"clipboard": "x", "category": "phone", "action": "masked", "occurred_at": "2026-09-18T12:00:00Z", "client_version": "1.0.0", "demo_session_id": "demo-session-x"},
    ],
)
def test_risk_event_rejects_forbidden_fields(client, payload):
    response = client.post("/api/risk-events", json=payload)
    assert response.status_code == 422


def test_risk_event_schema_has_no_prompt_columns(client):
    with db_session() as conn:
        columns = table_columns(conn, "risk_events")
    for name in FORBIDDEN_RISK_COLUMNS:
        assert name not in columns
    assert "raw_prompt" not in columns
    assert "prompt" not in columns
