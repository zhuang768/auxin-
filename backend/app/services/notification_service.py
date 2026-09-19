from __future__ import annotations

from typing import Optional, Protocol

from app.config import settings
from app.db import db_session
from app.utils import fetch_application, fetch_user, now_iso


class NotificationAdapter(Protocol):
    channel: str

    def send(self, event: str, recipient: dict, template_data: dict) -> dict:
        ...


LOW_SENSITIVITY_TEMPLATES = {
    "submitted": {
        "title": "申請已送出",
        "body": "你的竹青安心GO Demo 申請已送出，請回到安全入口查看進度。",
    },
    "under_review": {
        "title": "申請進入審查",
        "body": "你的竹青安心GO Demo 申請已進入審查。",
    },
    "needs_revision": {
        "title": "申請需要補充資料",
        "body": "申請需要補充資料，請回到安全入口查看。",
    },
    "rejected": {
        "title": "申請狀態已更新",
        "body": "申請狀態已更新，請回到安全入口查看詳情。",
    },
    "approved": {
        "title": "申請狀態已更新",
        "body": "申請狀態已更新，請回到安全入口查看詳情。",
    },
    "completed": {
        "title": "申請狀態已更新",
        "body": "申請狀態已更新，請回到安全入口查看詳情。",
    },
}


class InAppAdapter:
    channel = "in_app"

    def send(self, event: str, recipient: dict, template_data: dict) -> dict:
        template = LOW_SENSITIVITY_TEMPLATES.get(event, LOW_SENSITIVITY_TEMPLATES["approved"])
        record = {
            "user_id": recipient["id"],
            "event_type": event,
            "channel": self.channel,
            "title": template["title"],
            "body": template["body"],
            "delivery_status": "delivered",
            "preview": None,
            "created_at": now_iso(),
        }
        _insert_notification(record)
        return record


class LineMockAdapter:
    channel = "line"

    def send(self, event: str, recipient: dict, template_data: dict) -> dict:
        template = LOW_SENSITIVITY_TEMPLATES.get(event, LOW_SENSITIVITY_TEMPLATES["approved"])
        preview = (
            "【PoC 模擬，未連接新竹市政府正式 LINE】\n"
            f"收件人：{recipient['display_name']}（Demo）\n"
            f"訊息：{template['body']}\n"
            "結果：dry-run 已記錄，未對外發送。"
        )
        really_send = (
            settings.line_messaging_enabled
            and not settings.line_dry_run
            and bool(settings.line_channel_access_token)
        )
        status = "sent" if really_send else "dry_run"
        if really_send:
            # 真實發送預設關閉；此處刻意不呼叫外部 API，避免競賽環境誤送。
            status = "blocked_no_authorization"
            preview += "\n系統拒絕真實發送：尚未取得市府正式授權。"
        record = {
            "user_id": recipient["id"],
            "event_type": event,
            "channel": self.channel,
            "title": template["title"],
            "body": template["body"],
            "delivery_status": status,
            "preview": preview,
            "created_at": now_iso(),
        }
        _insert_notification(record)
        return record


class EmailMockAdapter:
    channel = "email"

    def send(self, event: str, recipient: dict, template_data: dict) -> dict:
        template = LOW_SENSITIVITY_TEMPLATES.get(event, LOW_SENSITIVITY_TEMPLATES["approved"])
        record = {
            "user_id": recipient["id"],
            "event_type": event,
            "channel": self.channel,
            "title": template["title"],
            "body": template["body"],
            "delivery_status": "poc_disabled",
            "preview": "Email 通知為 PoC／未啟用，僅站內通知為完整可用通路。",
            "created_at": now_iso(),
        }
        _insert_notification(record)
        return record


class SmsMockAdapter:
    channel = "sms"

    def send(self, event: str, recipient: dict, template_data: dict) -> dict:
        template = LOW_SENSITIVITY_TEMPLATES.get(event, LOW_SENSITIVITY_TEMPLATES["approved"])
        record = {
            "user_id": recipient["id"],
            "event_type": event,
            "channel": self.channel,
            "title": template["title"],
            "body": template["body"],
            "delivery_status": "poc_disabled",
            "preview": "簡訊通知為 PoC／未啟用，僅站內通知為完整可用通路。",
            "created_at": now_iso(),
        }
        _insert_notification(record)
        return record


ADAPTERS = {
    "in_app": InAppAdapter(),
    "line": LineMockAdapter(),
    "email": EmailMockAdapter(),
    "sms": SmsMockAdapter(),
}


def _insert_notification(record: dict) -> None:
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO notifications (
                user_id, event_type, channel, title, body, delivery_status, preview, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["user_id"],
                record["event_type"],
                record["channel"],
                record["title"],
                record["body"],
                record["delivery_status"],
                record["preview"],
                record["created_at"],
            ),
        )


def notify_status_change(application_id: str, to_status: str) -> list[dict]:
    with db_session() as conn:
        application = fetch_application(conn, application_id)
        user = fetch_user(conn, application["user_id"])
    results = []
    if user["notify_in_app"]:
        results.append(ADAPTERS["in_app"].send(to_status, user, {"application_id": application_id}))
    if user["notify_line"]:
        results.append(ADAPTERS["line"].send(to_status, user, {"application_id": application_id}))
    if user["notify_email"]:
        results.append(ADAPTERS["email"].send(to_status, user, {"application_id": application_id}))
    if user["notify_sms"]:
        results.append(ADAPTERS["sms"].send(to_status, user, {"application_id": application_id}))
    return results


def list_notifications(user_id: str) -> list[dict]:
    with db_session() as conn:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC",
                (user_id,),
            ).fetchall()
        ]


def latest_line_preview(user_id: str) -> Optional[dict]:
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT * FROM notifications
            WHERE user_id = ? AND channel = 'line'
            ORDER BY id DESC LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def send_test_notification(user_id: str, event_type: str, channel: str) -> dict:
    with db_session() as conn:
        user = fetch_user(conn, user_id)
    adapter = ADAPTERS.get(channel)
    if adapter is None:
        raise ValueError("不支援的通知通路")
    return adapter.send(event_type, user, {})
