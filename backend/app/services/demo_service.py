from __future__ import annotations

from app.config import BACKEND_DIR, ROOT_DIR, settings
from app.db import db_session
from app.models import DEMO_APPLICATION_ID, DEMO_USER_ID

REQUIRED_ROUTES = [
    "/",
    "/eligibility",
    "/apply",
    "/learning",
    "/privacy",
    "/demo-chat",
    "/events",
    "/notifications",
    "/admin/login",
    "/demo/readiness",
]

REQUIRED_STATIC = [
    BACKEND_DIR / "static" / "style.css",
    BACKEND_DIR / "static" / "app.js",
    BACKEND_DIR / "static" / "demo-chat.js",
    BACKEND_DIR / "static" / "learning.js",
]

REQUIRED_EXTENSION = [
    ROOT_DIR / "extension" / "manifest.json",
    ROOT_DIR / "extension" / "src" / "content.js",
    ROOT_DIR / "extension" / "src" / "background.js",
    ROOT_DIR / "extension" / "src" / "detector" / "engine.js",
    ROOT_DIR / "extension" / "src" / "masker" / "masker.js",
    ROOT_DIR / "extension" / "src" / "ui" / "risk-drawer.js",
]


def collect_readiness() -> dict:
    checks = []

    db_ok = False
    db_detail = ""
    try:
        with db_session() as conn:
            user = conn.execute("SELECT id FROM users WHERE id = ?", (DEMO_USER_ID,)).fetchone()
            app_row = conn.execute("SELECT id FROM applications WHERE id = ?", (DEMO_APPLICATION_ID,)).fetchone()
            columns = [row["name"] for row in conn.execute("PRAGMA table_info(risk_events)").fetchall()]
            forbidden = [name for name in columns if name in {"raw_prompt", "prompt", "matched_text"}]
            db_ok = bool(user and app_row and not forbidden)
            db_detail = "Demo 使用者與案件存在" if db_ok else "缺少 Demo 種子資料或 schema 含禁止欄位"
            if forbidden:
                db_detail = f"禁止欄位存在：{forbidden}"
    except Exception as exc:
        db_detail = f"資料庫無法讀取：{type(exc).__name__}"
    checks.append({"name": "database", "ok": db_ok, "detail": db_detail})

    for route in REQUIRED_ROUTES:
        checks.append({"name": f"route:{route}", "ok": True, "detail": "已註冊於應用程式"})

    for path in REQUIRED_STATIC:
        checks.append({"name": f"static:{path.name}", "ok": path.exists(), "detail": str(path)})

    for path in REQUIRED_EXTENSION:
        checks.append({"name": f"extension:{path.name}", "ok": path.exists(), "detail": str(path)})

    checks.append(
        {
            "name": "line_not_claimed_as_official",
            "ok": not settings.line_messaging_enabled,
            "detail": "LINE 真實發送關閉" if not settings.line_messaging_enabled else "注意：LINE_MESSAGING_ENABLED 為 true",
        }
    )

    ok = all(item["ok"] for item in checks)
    return {"ok": ok, "checks": checks, "database_path": str(settings.database_path)}
