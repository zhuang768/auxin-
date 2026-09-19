from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import BACKEND_DIR, settings
from app.db import db_session
from app.models import ACTION_LABELS, CATEGORY_LABELS, STATUS_LABELS
from app.security import (
    ADMIN_SESSION_KEY,
    admin_or_redirect,
    ensure_csrf_token,
    require_admin,
    validate_csrf,
)
from app.services import application_service

router = APIRouter()
templates = Jinja2Templates(directory=str(BACKEND_DIR / "templates"))


def admin_context(request: Request, **extra):
    ctx = {
        "request": request,
        "csrf_token": ensure_csrf_token(request),
        "admin_username": settings.admin_username,
        "status_labels": STATUS_LABELS,
        "category_labels": CATEGORY_LABELS,
        "action_labels": ACTION_LABELS,
    }
    ctx.update(extra)
    return ctx


@router.get("/admin/login")
def login_form(request: Request):
    return templates.TemplateResponse(
        "admin/login.html",
        admin_context(request, error=None),
    )


@router.post("/admin/login")
def login_submit(
    request: Request,
    csrf_token: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
):
    validate_csrf(request, csrf_token)
    if username != settings.admin_username or password != settings.admin_password:
        return templates.TemplateResponse(
            "admin/login.html",
            admin_context(request, error="帳號或密碼不正確。"),
            status_code=401,
        )
    request.session[ADMIN_SESSION_KEY] = True
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/admin/logout")
def logout(request: Request, csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token)
    request.session.pop(ADMIN_SESSION_KEY, None)
    return RedirectResponse(url="/admin/login", status_code=303)


@router.get("/admin")
def dashboard(request: Request, status: Optional[str] = None):
    redirect = admin_or_redirect(request)
    if redirect:
        return redirect
    rows = application_service.list_applications(status or None)
    with db_session() as conn:
        stats = {
            "total": conn.execute("SELECT COUNT(*) AS c FROM applications").fetchone()["c"],
            "submitted": conn.execute("SELECT COUNT(*) AS c FROM applications WHERE status = 'submitted'").fetchone()["c"],
            "under_review": conn.execute("SELECT COUNT(*) AS c FROM applications WHERE status = 'under_review'").fetchone()["c"],
        }
        risk_rows = conn.execute(
            """
            SELECT category, action, COUNT(*) AS count
            FROM risk_events
            GROUP BY category, action
            ORDER BY count DESC
            """
        ).fetchall()
    return templates.TemplateResponse(
        "admin/dashboard.html",
        admin_context(
            request,
            rows=rows,
            filter_status=status or "",
            stats=stats,
            risk_rows=[dict(row) for row in risk_rows],
        ),
    )


@router.get("/admin/applications/{application_id}")
def case_page(request: Request, application_id: str):
    redirect = admin_or_redirect(request)
    if redirect:
        return redirect
    application = application_service.get_application(application_id)
    return templates.TemplateResponse(
        "admin/case.html",
        admin_context(request, application=application),
    )


@router.post("/admin/applications/{application_id}/review")
def review_case(
    request: Request,
    application_id: str,
    csrf_token: str = Form(...),
    to_status: str = Form(...),
    revision_reason: str = Form(""),
    note: str = Form(""),
):
    require_admin(request)
    validate_csrf(request, csrf_token)
    application_service.transition_application(
        application_id,
        to_status,
        "admin",
        note=note or None,
        revision_reason=revision_reason or None,
    )
    return RedirectResponse(url=f"/admin/applications/{application_id}", status_code=303)
