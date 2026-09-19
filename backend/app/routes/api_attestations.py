from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas import AttestationCompleteIn
from app.security import current_user_id
from app.services.attestation_service import complete_attestation, issue_nonce, verify_attestation

router = APIRouter(prefix="/api/attestations", tags=["attestations"])


@router.post("/challenge")
def challenge():
    return issue_nonce()


@router.post("/complete")
def complete(request: Request, payload: AttestationCompleteIn):
    return complete_attestation(current_user_id(request), payload.nonce_id)


@router.post("/{attestation_id}/verify")
def verify(attestation_id: str, payload: dict):
    return verify_attestation(attestation_id, payload.get("payload", ""), payload.get("mac", ""))
