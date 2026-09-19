from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas import ApplicationCreate, ApplicationReview
from app.security import current_user_id, require_admin
from app.services import application_service

router = APIRouter(prefix="/api/applications", tags=["applications"])


@router.post("")
def create_application(request: Request, payload: ApplicationCreate):
    created = application_service.create_application(current_user_id(request), payload)
    return application_service.transition_application(created["id"], "submitted", "user", "API 送出 Demo 申請")


@router.get("/{application_id}")
def get_application(application_id: str):
    return application_service.get_application(application_id)


@router.post("/{application_id}/submit")
def submit_application(application_id: str):
    return application_service.transition_application(application_id, "submitted", "user", "再次送出")


@router.post("/{application_id}/review")
def review_application(request: Request, application_id: str, payload: ApplicationReview):
    require_admin(request)
    return application_service.transition_application(
        application_id,
        payload.to_status,
        "admin",
        note=payload.note,
        revision_reason=payload.revision_reason,
    )
