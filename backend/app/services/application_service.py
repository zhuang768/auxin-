from __future__ import annotations

from typing import Optional

from app.db import db_session
from app.models import DEMO_APPLICATION_ID, DEMO_USER_ID, LEARNING_MODULES, MODULE_LABELS, STATUS_LABELS
from app.schemas import ApplicationCreate
from app.utils import assert_transition, fetch_application, fetch_user, new_id, now_iso, record_event


def list_applications(status: Optional[str] = None) -> list[dict]:
    sql = "SELECT * FROM applications"
    params: list = []
    if status:
        sql += " WHERE status = ?"
        params.append(status)
    sql += " ORDER BY updated_at DESC"
    with db_session() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def get_application(application_id: str) -> dict:
    with db_session() as conn:
        application = fetch_application(conn, application_id)
        user = fetch_user(conn, application["user_id"])
        events = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM application_events WHERE application_id = ? ORDER BY id ASC",
                (application_id,),
            ).fetchall()
        ]
        completions = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM learning_completions WHERE user_id = ? ORDER BY completed_at ASC",
                (application["user_id"],),
            ).fetchall()
        ]
    completed_modules = {item["module"] for item in completions}
    application["user"] = user
    application["events"] = events
    application["completions"] = completions
    application["learning_progress"] = [
        {
            "module": module,
            "label": MODULE_LABELS[module],
            "done": module in completed_modules,
        }
        for module in LEARNING_MODULES
    ]
    application["status_label"] = STATUS_LABELS[application["status"]]
    application["next_step"] = next_step_copy(application)
    return application


def next_step_copy(application: dict) -> str:
    status = application["status"]
    mapping = {
        "draft": "請確認資料後送出申請。",
        "submitted": "已送出，等待承辦人員開始審查。",
        "under_review": "案件審查中，請留意站內通知。",
        "needs_revision": application.get("revision_reason") or "請回到申請頁補充資料後再次送出。",
        "rejected": "本案未通過，詳情請見通知，不顯示敏感審查內容。",
        "approved": "已核准。承辦人員完成結案後會再通知。",
        "completed": "Demo 案件已完成，此狀態不代表正式撥款。",
    }
    return mapping[status]


def create_application(user_id: str, payload: ApplicationCreate) -> dict:
    application_id = new_id("app")
    timestamp = now_iso()
    with db_session() as conn:
        fetch_user(conn, user_id)
        conn.execute(
            """
            UPDATE users
            SET display_name = ?, email = ?, phone = ?,
                notify_in_app = ?, notify_line = ?, notify_email = ?, notify_sms = ?
            WHERE id = ?
            """,
            (
                payload.display_name,
                payload.email,
                payload.phone,
                int(payload.notify_in_app),
                int(payload.notify_line),
                int(payload.notify_email),
                int(payload.notify_sms),
                user_id,
            ),
        )
        conn.execute(
            """
            INSERT INTO applications (
                id, user_id, status, identity_type, tool_category, tool_name, purpose,
                revision_reason, created_at, updated_at
            ) VALUES (?, ?, 'draft', ?, ?, ?, ?, NULL, ?, ?)
            """,
            (
                application_id,
                user_id,
                payload.identity_type,
                payload.tool_category,
                payload.tool_name,
                payload.purpose,
                timestamp,
                timestamp,
            ),
        )
        record_event(conn, application_id, None, "draft", "user", "建立 Demo 申請草稿")
    return get_application(application_id)


def transition_application(application_id: str, to_status: str, actor: str, note: Optional[str] = None, revision_reason: Optional[str] = None) -> dict:
    with db_session() as conn:
        application = fetch_application(conn, application_id)
        assert_transition(application["status"], to_status, actor)
        timestamp = now_iso()
        reason = revision_reason if to_status == "needs_revision" else None
        conn.execute(
            """
            UPDATE applications
            SET status = ?, revision_reason = ?, updated_at = ?
            WHERE id = ?
            """,
            (to_status, reason, timestamp, application_id),
        )
        record_event(conn, application_id, application["status"], to_status, actor, note)
    from app.services.notification_service import notify_status_change

    notify_status_change(application_id, to_status)
    return get_application(application_id)


def user_latest_application(user_id: str) -> Optional[dict]:
    with db_session() as conn:
        row = conn.execute(
            "SELECT id FROM applications WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    if not row:
        return None
    return get_application(row["id"])


def demo_primary_application() -> dict:
    return get_application(DEMO_APPLICATION_ID)


def demo_user() -> dict:
    with db_session() as conn:
        return fetch_user(conn, DEMO_USER_ID)
