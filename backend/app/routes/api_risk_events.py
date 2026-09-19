from __future__ import annotations

from fastapi import APIRouter

from app.db import FORBIDDEN_RISK_COLUMNS, db_session, table_columns
from app.schemas import RiskEventIn
from app.utils import now_iso

router = APIRouter(prefix="/api/risk-events", tags=["risk-events"])


@router.post("")
def create_risk_event(payload: RiskEventIn):
    with db_session() as conn:
        columns = table_columns(conn, "risk_events")
        for forbidden in FORBIDDEN_RISK_COLUMNS:
            if forbidden in columns:
                raise RuntimeError("資料庫 schema 含有禁止欄位")
        conn.execute(
            """
            INSERT INTO risk_events (category, action, occurred_at, client_version, demo_session_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload.category,
                payload.action,
                payload.occurred_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                payload.client_version,
                payload.demo_session_id,
                now_iso(),
            ),
        )
        new_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        row = conn.execute(
            "SELECT id, category, action, occurred_at, client_version, demo_session_id, created_at FROM risk_events WHERE id = ?",
            (new_id,),
        ).fetchone()
    return {"ok": True, "event": dict(row)}


@router.get("")
def list_risk_events():
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT id, category, action, occurred_at, client_version, demo_session_id, created_at
            FROM risk_events
            ORDER BY id DESC
            """
        ).fetchall()
        columns = table_columns(conn, "risk_events")
    return {
        "events": [dict(row) for row in rows],
        "columns": columns,
        "note": "此列表不含原始 Prompt、命中文字或完整 URL。",
    }


@router.get("/summary")
def summary():
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT category, action, COUNT(*) AS count
            FROM risk_events
            GROUP BY category, action
            ORDER BY count DESC
            """
        ).fetchall()
    return {"items": [dict(row) for row in rows]}
