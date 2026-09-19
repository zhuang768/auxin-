from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import BACKEND_DIR
from app.content import CASES, GUIDE_STEPS, QUIZ
from app.models import DEMO_USER_ID, STATUS_LABELS
from app.schemas import ApplicationCreate
from app.security import current_user_id, ensure_csrf_token, validate_csrf
from app.services import application_service, learning_service
from app.services.attestation_service import complete_attestation, issue_nonce
from app.services.notification_service import latest_line_preview, list_notifications

router = APIRouter()
templates = Jinja2Templates(directory=str(BACKEND_DIR / "templates"))


def base_context(request: Request, **extra):
    user_id = current_user_id(request)
    try:
        user = application_service.demo_user()
        latest = application_service.user_latest_application(user_id)
        progress = learning_service.get_progress(user_id)
        notes = list_notifications(user_id)
    except Exception:
        user = {"display_name": "林小竹", "email": "demo@example.test", "phone": "0912-000-111"}
        latest = None
        progress = {"items": [], "completed_count": 0, "total": 3, "all_done": False, "disclaimer": ""}
        notes = []
    ctx = {
        "request": request,
        "csrf_token": ensure_csrf_token(request),
        "user": user,
        "latest_application": latest,
        "progress": progress,
        "unread_count": len(notes),
        "status_labels": STATUS_LABELS,
        "demo_user_id": DEMO_USER_ID,
    }
    ctx.update(extra)
    return ctx


@router.get("/")
def home(request: Request):
    return templates.TemplateResponse("home.html", base_context(request, page="home"))


@router.get("/eligibility")
def eligibility(request: Request):
    return templates.TemplateResponse("eligibility.html", base_context(request, page="eligibility"))


@router.get("/apply")
def apply_form(request: Request):
    return templates.TemplateResponse("apply.html", base_context(request, page="apply"))


@router.post("/apply")
def apply_submit(
    request: Request,
    csrf_token: str = Form(...),
    display_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    identity_type: str = Form(...),
    tool_category: str = Form(...),
    tool_name: str = Form(...),
    purpose: str = Form(...),
    notify_in_app: str = Form("on"),
    notify_line: str = Form(None),
    notify_email: str = Form(None),
    notify_sms: str = Form(None),
):
    validate_csrf(request, csrf_token)
    payload = ApplicationCreate(
        display_name=display_name,
        email=email,
        phone=phone,
        identity_type=identity_type,  # type: ignore[arg-type]
        tool_category=tool_category,  # type: ignore[arg-type]
        tool_name=tool_name,
        purpose=purpose,
        notify_in_app=notify_in_app == "on",
        notify_line=notify_line == "on",
        notify_email=notify_email == "on",
        notify_sms=notify_sms == "on",
    )
    created = application_service.create_application(current_user_id(request), payload)
    submitted = application_service.transition_application(created["id"], "submitted", "user", "青年送出 Demo 申請")
    return RedirectResponse(url=f"/applications/{submitted['id']}", status_code=303)


@router.get("/applications/{application_id}")
def application_detail(request: Request, application_id: str):
    application = application_service.get_application(application_id)
    return templates.TemplateResponse(
        "application_status.html",
        base_context(request, page="status", application=application),
    )


@router.post("/applications/{application_id}/resubmit")
def resubmit(request: Request, application_id: str, csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token)
    application_service.transition_application(application_id, "submitted", "user", "青年補件後再次送出")
    return RedirectResponse(url=f"/applications/{application_id}", status_code=303)


@router.get("/notifications")
def notifications_page(request: Request):
    user_id = current_user_id(request)
    return templates.TemplateResponse(
        "notifications.html",
        base_context(
            request,
            page="notifications",
            notifications=list_notifications(user_id),
            line_preview=latest_line_preview(user_id),
        ),
    )


@router.get("/learning")
def learning_page(request: Request):
    return templates.TemplateResponse(
        "learning.html",
        base_context(request, page="learning", cases=CASES, quiz=QUIZ, guide_steps=GUIDE_STEPS),
    )


@router.get("/privacy")
def privacy_page(request: Request):
    return templates.TemplateResponse("privacy.html", base_context(request, page="privacy"))


@router.get("/demo-chat")
def demo_chat(request: Request):
    return templates.TemplateResponse("demo_chat.html", base_context(request, page="demo-chat"))


@router.get("/events")
def events_page(request: Request):
    from app.db import db_session

    with db_session() as conn:
        rows = [dict(row) for row in conn.execute("SELECT * FROM risk_events ORDER BY id DESC").fetchall()]
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(risk_events)").fetchall()]
    return templates.TemplateResponse(
        "events.html",
        base_context(request, page="events", events=rows, columns=columns),
    )


@router.get("/attestation")
def attestation_page(request: Request):
    progress = learning_service.get_progress(current_user_id(request))
    return templates.TemplateResponse(
        "attestation.html",
        base_context(request, page="attestation", challenge=None, result=None, progress=progress),
    )


@router.post("/attestation/complete")
def attestation_complete(request: Request, csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token)
    user_id = current_user_id(request)
    challenge = issue_nonce()
    result = complete_attestation(user_id, challenge["nonce_id"])
    return templates.TemplateResponse(
        "attestation.html",
        base_context(
            request,
            page="attestation",
            challenge=challenge,
            result=result,
            progress=learning_service.get_progress(user_id),
        ),
    )


@router.get("/demo/readiness")
def readiness_page(request: Request):
    from app.services.demo_service import collect_readiness

    return templates.TemplateResponse(
        "readiness.html",
        base_context(request, page="readiness", report=collect_readiness()),
    )


@router.post("/demo/reset")
def reset_page(request: Request, csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token)
    from app.seed import reset_and_seed

    reset_and_seed()
    request.session["user_id"] = DEMO_USER_ID
    return RedirectResponse(url="/demo/readiness", status_code=303)
