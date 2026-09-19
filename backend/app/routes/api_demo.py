from __future__ import annotations

from fastapi import APIRouter, Request

from app.models import DEMO_USER_ID
from app.schemas import NotificationTestIn
from app.seed import reset_and_seed
from app.services.demo_service import collect_readiness
from app.services.notification_service import send_test_notification

router = APIRouter(prefix="/api", tags=["demo"])


@router.post("/demo/reset")
def reset_demo(request: Request):
    reset_and_seed()
    request.session["user_id"] = DEMO_USER_ID
    return {"ok": True, "user_id": DEMO_USER_ID}


@router.get("/health")
def health():
    report = collect_readiness()
    return {"status": "ok" if report["ok"] else "degraded", "checks": report["checks"]}


@router.get("/demo/readiness")
def readiness():
    return collect_readiness()


@router.post("/notifications/test")
def test_notification(request: Request, payload: NotificationTestIn):
    result = send_test_notification(DEMO_USER_ID, payload.event_type, payload.channel)
    return {"ok": True, "result": result, "disclaimer": "LINE 為 PoC 通知介面，尚未連接新竹市政府正式帳號。"}
