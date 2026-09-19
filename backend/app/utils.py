from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from fastapi import HTTPException, status

from app.models import ADMIN_TRANSITIONS, ALLOWED_TRANSITIONS, STATUS_LABELS, USER_TRANSITIONS

NOW_FMT = "%Y-%m-%dT%H:%M:%SZ"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime(NOW_FMT)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


def row_to_dict(row: Optional[Any]) -> Optional[dict]:
    if row is None:
        return None
    return dict(row)


def fetch_user(conn, user_id: str) -> dict:
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="找不到 Demo 使用者。")
    return dict(row)


def fetch_application(conn, application_id: str) -> dict:
    row = conn.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="找不到申請案。")
    return dict(row)


def assert_transition(current: str, target: str, actor: str) -> None:
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"無法從「{STATUS_LABELS.get(current, current)}」轉換到「{STATUS_LABELS.get(target, target)}」。",
        )
    scoped = USER_TRANSITIONS if actor == "user" else ADMIN_TRANSITIONS
    if target not in scoped.get(current, set()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="這個角色不能執行此狀態轉換。",
        )


def record_event(
    conn,
    application_id: str,
    from_status: Optional[str],
    to_status: str,
    actor: str,
    note: Optional[str] = None,
) -> None:
    conn.execute(
        """
        INSERT INTO application_events (application_id, from_status, to_status, actor, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (application_id, from_status, to_status, actor, note, now_iso()),
    )
