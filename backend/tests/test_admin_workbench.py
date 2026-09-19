from __future__ import annotations

from app.config import settings
from app.db import db_session
from app.models import DEMO_APPLICATION_ID, DEMO_USER_ID
from app.utils import now_iso


def login_admin(client) -> str:
    page = client.get("/admin/login")
    token = page.text.split('name="csrf_token" value="')[1].split('"')[0]
    response = client.post(
        "/admin/login",
        data={
            "csrf_token": token,
            "username": settings.admin_username,
            "password": settings.admin_password,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    return token


def add_case(application_id: str, status: str, tool_name: str) -> None:
    timestamp = now_iso()
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO applications (
                id, user_id, status, identity_type, tool_category, tool_name, purpose,
                revision_reason, created_at, updated_at
            ) VALUES (?, ?, ?, 'general', 'conversational_llm', ?, '合成測試用途', NULL, ?, ?)
            """,
            (application_id, DEMO_USER_ID, status, tool_name, timestamp, timestamp),
        )


def test_workbench_prioritizes_cases_and_excludes_drafts(client):
    add_case("app_unsubmitted", "draft", "尚未送出工具")
    timestamp = now_iso()
    with db_session() as conn:
        conn.execute(
            "INSERT INTO line_sessions (user_hash, state, created_at, updated_at) VALUES (?, ?, ?, ?)",
            ("synthetic-line-draft-hash", "tool_name", timestamp, timestamp),
        )
    login_admin(client)

    page = client.get("/admin")
    assert page.status_code == 200
    assert DEMO_APPLICATION_ID in page.text
    assert "app_unsubmitted" not in page.text
    assert "synthetic-line-draft-hash" not in page.text
    assert "案件列表" in page.text
    assert "已送出案件" in page.text
    assert "匿名風險彙總" not in page.text
    assert "LINE 正式送出與市府系統串接尚未啟用" in page.text


def test_workbench_search_and_status_filter(client):
    add_case("app_review_002", "under_review", "Notion AI")
    login_admin(client)

    searched = client.get("/admin", params={"q": "notion"})
    assert "app_review_002" in searched.text
    assert DEMO_APPLICATION_ID not in searched.text

    filtered = client.get("/admin", params={"status": "submitted"})
    assert DEMO_APPLICATION_ID in filtered.text
    assert "app_review_002" not in filtered.text

    empty = client.get("/admin", params={"q": "no-such-case"})
    assert "沒有符合條件的已送出案件" in empty.text


def test_case_page_shows_history_and_only_allowed_actions(client):
    token = login_admin(client)
    page = client.get(f"/admin/applications/{DEMO_APPLICATION_ID}")
    assert page.status_code == 200
    assert "狀態歷程" in page.text
    assert "舊版安全教材紀錄" in page.text
    assert "這不是 LINE Phase 5 六題資安檢核結果" in page.text
    assert '<option value="under_review">' in page.text
    assert '<option value="approved">' not in page.text

    changed = client.post(
        f"/admin/applications/{DEMO_APPLICATION_ID}/review",
        data={"csrf_token": token, "to_status": "under_review", "revision_reason": "", "note": "開始審查"},
        follow_redirects=False,
    )
    assert changed.status_code == 303
    updated = client.get(f"/admin/applications/{DEMO_APPLICATION_ID}")
    assert "開始審查" in updated.text
    assert '<option value="approved">' in updated.text


def test_direct_draft_page_is_labelled_not_reviewable(client):
    add_case("app_unsubmitted", "draft", "尚未送出工具")
    login_admin(client)
    page = client.get("/admin/applications/app_unsubmitted")
    assert page.status_code == 200
    assert "尚未送出的草稿，不列入案件總覽或正式審查" in page.text
    assert "此案件目前沒有可執行的行政狀態轉換" in page.text
