from __future__ import annotations

from app.db import db_session
from app.models import LEARNING_MODULES, MODULE_LABELS
from app.utils import fetch_user, now_iso


def record_completion(user_id: str, module: str, version: str = "demo-1") -> dict:
    if module not in LEARNING_MODULES:
        raise ValueError("未知教材模組")
    timestamp = now_iso()
    with db_session() as conn:
        fetch_user(conn, user_id)
        existing = conn.execute(
            "SELECT id FROM learning_completions WHERE user_id = ? AND module = ?",
            (user_id, module),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE learning_completions SET version = ?, completed_at = ? WHERE id = ?",
                (version, timestamp, existing["id"]),
            )
        else:
            conn.execute(
                """
                INSERT INTO learning_completions (user_id, module, version, completed_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, module, version, timestamp),
            )
    return get_progress(user_id)


def get_progress(user_id: str) -> dict:
    with db_session() as conn:
        fetch_user(conn, user_id)
        rows = [
            dict(row)
            for row in conn.execute(
                "SELECT module, version, completed_at FROM learning_completions WHERE user_id = ?",
                (user_id,),
            ).fetchall()
        ]
    done = {row["module"] for row in rows}
    items = [
        {
            "module": module,
            "label": MODULE_LABELS[module],
            "done": module in done,
        }
        for module in LEARNING_MODULES
    ]
    return {
        "items": items,
        "completed_count": sum(1 for item in items if item["done"]),
        "total": len(items),
        "all_done": all(item["done"] for item in items),
        "disclaimer": "完成狀態只表示完成課程與操作，不代表使用者已完全安全。",
    }
