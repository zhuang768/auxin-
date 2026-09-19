from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from app.config import settings
from app.db import db_session
from app.models import LEARNING_MODULES
from app.security import sign_payload, verify_mac
from app.utils import fetch_user, new_id, now_iso


def canonical_json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def issue_nonce(purpose: str = "learning_attestation") -> dict:
    nonce_id = new_id("nonce")
    created = datetime.now(timezone.utc)
    expires = created + timedelta(seconds=settings.nonce_ttl_seconds)
    with db_session() as conn:
        conn.execute(
            "INSERT INTO nonces (id, purpose, created_at, expires_at, used_at) VALUES (?, ?, ?, ?, NULL)",
            (
                nonce_id,
                purpose,
                created.strftime("%Y-%m-%dT%H:%M:%SZ"),
                expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
        )
    return {
        "nonce_id": nonce_id,
        "expires_at": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "purpose": purpose,
    }


def complete_attestation(user_id: str, nonce_id: str) -> dict:
    now = datetime.now(timezone.utc)
    with db_session() as conn:
        fetch_user(conn, user_id)
        nonce = conn.execute("SELECT * FROM nonces WHERE id = ?", (nonce_id,)).fetchone()
        if nonce is None:
            raise HTTPException(status_code=400, detail="找不到這組 nonce。")
        if nonce["used_at"]:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="nonce 已被使用，不可重放。")
        expires = datetime.strptime(nonce["expires_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if now > expires:
            raise HTTPException(status_code=400, detail="nonce 已過期，請重新取得挑戰。")
        completions = [
            dict(row)
            for row in conn.execute(
                "SELECT module, version, completed_at FROM learning_completions WHERE user_id = ?",
                (user_id,),
            ).fetchall()
        ]
        completed_modules = sorted({item["module"] for item in completions})
        payload = {
            "type": "zhuqing_demo_attestation",
            "user_id": user_id,
            "modules_completed": completed_modules,
            "required_modules": list(LEARNING_MODULES),
            "issued_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "nonce_id": nonce_id,
            "disclaimer": "這是 Demo 完整性憑證，不是政府身分驗證，也不能保證使用者永遠遵守安全行為。",
        }
        payload_text = canonical_json(payload)
        mac = sign_payload(payload_text)
        attestation_id = new_id("att")
        att_expires = now + timedelta(days=7)
        conn.execute("UPDATE nonces SET used_at = ? WHERE id = ?", (now_iso(), nonce_id))
        conn.execute(
            """
            INSERT INTO attestations (id, user_id, nonce_id, payload, mac, issued_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attestation_id,
                user_id,
                nonce_id,
                payload_text,
                mac,
                payload["issued_at"],
                att_expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
        )
    return {
        "id": attestation_id,
        "payload": payload,
        "mac": mac,
        "expires_at": att_expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def verify_attestation(attestation_id: str, payload_text: str, mac: str) -> dict:
    with db_session() as conn:
        row = conn.execute("SELECT * FROM attestations WHERE id = ?", (attestation_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="找不到憑證。")
    intact = row["payload"] == payload_text and verify_mac(payload_text, mac) and row["mac"] == mac
    return {
        "id": attestation_id,
        "valid": intact,
        "tampered": not intact,
        "disclaimer": "這是 Demo 完整性憑證，不是政府身分驗證。",
    }
