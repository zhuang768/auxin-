from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from app.db import db_session
from app.security import sign_payload
from app.services.attestation_service import canonical_json


def test_nonce_replay_and_hmac(client):
    challenge = client.post("/api/attestations/challenge").json()
    first = client.post("/api/attestations/complete", json={"nonce_id": challenge["nonce_id"]})
    assert first.status_code == 200
    replay = client.post("/api/attestations/complete", json={"nonce_id": challenge["nonce_id"]})
    assert replay.status_code == 409

    payload = first.json()["payload"]
    mac = first.json()["mac"]
    attestation_id = first.json()["id"]
    verify_ok = client.post(
        f"/api/attestations/{attestation_id}/verify",
        json={"payload": canonical_json(payload), "mac": mac},
    )
    assert verify_ok.json()["valid"] is True

    tampered = dict(payload)
    tampered["modules_completed"] = ["forged"]
    verify_bad = client.post(
        f"/api/attestations/{attestation_id}/verify",
        json={"payload": canonical_json(tampered), "mac": mac},
    )
    assert verify_bad.json()["valid"] is False
    assert verify_bad.json()["tampered"] is True


def test_expired_nonce(client):
    challenge = client.post("/api/attestations/challenge").json()
    past = (datetime.now(timezone.utc) - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with db_session() as conn:
        conn.execute("UPDATE nonces SET expires_at = ? WHERE id = ?", (past, challenge["nonce_id"]))
    expired = client.post("/api/attestations/complete", json={"nonce_id": challenge["nonce_id"]})
    assert expired.status_code == 400
    assert "過期" in expired.json()["detail"]


def test_hmac_mismatch_detected(tmp_path):
    payload = {"hello": "world"}
    text = canonical_json(payload)
    mac = sign_payload(text)
    bad = sign_payload(json.dumps({"hello": "tampered"}))
    assert mac != bad
