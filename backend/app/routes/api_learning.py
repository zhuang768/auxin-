from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas import LearningCompletionIn
from app.security import current_user_id
from app.services import learning_service

router = APIRouter(prefix="/api/learning", tags=["learning"])


@router.get("/progress")
def progress(request: Request):
    return learning_service.get_progress(current_user_id(request))


@router.post("/completions")
def complete(request: Request, payload: LearningCompletionIn):
    return learning_service.record_completion(current_user_id(request), payload.module, payload.version)
