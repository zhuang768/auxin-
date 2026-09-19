from __future__ import annotations

from app.db import db_session, reset_database
from app.models import DEMO_APPLICATION_ID, DEMO_SESSION_ID, DEMO_USER_ID
from app.utils import now_iso

DEMO_USER = {
    "id": DEMO_USER_ID,
    "display_name": "林小竹",
    "email": "demo@example.test",
    "phone": "0912-000-111",
}


def seed_demo_data() -> None:
    timestamp = now_iso()
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO users (
                id, display_name, email, phone, notify_in_app, notify_line, notify_email, notify_sms,
                consent_version, created_at
            ) VALUES (?, ?, ?, ?, 1, 1, 0, 0, 'demo-1', ?)
            """,
            (
                DEMO_USER["id"],
                DEMO_USER["display_name"],
                DEMO_USER["email"],
                DEMO_USER["phone"],
                timestamp,
            ),
        )
        conn.execute(
            """
            INSERT INTO applications (
                id, user_id, status, identity_type, tool_category, tool_name, purpose,
                revision_reason, created_at, updated_at
            ) VALUES (?, ?, 'submitted', 'general', 'conversational_llm', 'ChatGPT Plus（Demo）',
                      '練習使用生成式 AI 撰寫企劃摘要，僅使用合成資料。', NULL, ?, ?)
            """,
            (DEMO_APPLICATION_ID, DEMO_USER_ID, timestamp, timestamp),
        )
        conn.execute(
            """
            INSERT INTO application_events (application_id, from_status, to_status, actor, note, created_at)
            VALUES (?, NULL, 'draft', 'system', 'Demo 重設：建立草稿', ?),
                   (?, 'draft', 'submitted', 'user', 'Demo 重設：已送出申請', ?)
            """,
            (DEMO_APPLICATION_ID, timestamp, DEMO_APPLICATION_ID, timestamp),
        )
        conn.execute(
            """
            INSERT INTO notifications (
                user_id, event_type, channel, title, body, delivery_status, preview, created_at
            ) VALUES (?, 'submitted', 'in_app', '申請已送出',
                      '你的竹青安心GO Demo 申請已送出，請回到安全入口查看進度。',
                      'delivered', NULL, ?)
            """,
            (DEMO_USER_ID, timestamp),
        )
        conn.execute(
            """
            INSERT INTO risk_events (category, action, occurred_at, client_version, demo_session_id, created_at)
            VALUES
              ('phone', 'masked', ?, '1.0.0', ?, ?),
              ('email', 'cancelled', ?, '1.0.0', ?, ?)
            """,
            (timestamp, DEMO_SESSION_ID, timestamp, timestamp, DEMO_SESSION_ID, timestamp),
        )


def reset_and_seed() -> None:
    reset_database()
    seed_demo_data()
