from __future__ import annotations

import hmac
import logging
import secrets
from hashlib import sha256
from typing import Any, Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse, Response

from app.config import settings

logger = logging.getLogger("zhuqing")

CSRF_SESSION_KEY = "csrf_token"
ADMIN_SESSION_KEY = "admin_authenticated"
USER_SESSION_KEY = "user_id"


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def ensure_csrf_token(request: Request) -> str:
    token = request.session.get(CSRF_SESSION_KEY)
    if not token:
        token = new_csrf_token()
        request.session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf(request: Request, token: Optional[str]) -> None:
    session_token = request.session.get(CSRF_SESSION_KEY)
    if not session_token or not token or not hmac.compare_digest(session_token, token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF 驗證失敗，請重新整理頁面後再試。")


async def csrf_from_request(request: Request) -> Optional[str]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        return body.get("csrf_token")
    form = await request.form()
    value = form.get("csrf_token")
    return str(value) if value is not None else None


def require_admin(request: Request) -> None:
    if not request.session.get(ADMIN_SESSION_KEY):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="需要管理員登入。")


def admin_or_redirect(request: Request) -> Optional[RedirectResponse]:
    if request.session.get(ADMIN_SESSION_KEY):
        return None
    return RedirectResponse(url="/admin/login", status_code=303)


def current_user_id(request: Request) -> str:
    from app.models import DEMO_USER_ID

    return request.session.get(USER_SESSION_KEY) or DEMO_USER_ID


def sign_payload(payload: str) -> str:
    return hmac.new(
        settings.hmac_secret.encode("utf-8"),
        payload.encode("utf-8"),
        sha256,
    ).hexdigest()


def verify_mac(payload: str, mac: str) -> bool:
    expected = sign_payload(payload)
    return hmac.compare_digest(expected, mac)


def security_headers_middleware(response: Response) -> Response:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    return response


def safe_error_response(detail: str, status_code: int = 500) -> JSONResponse:
    logger.exception("request failed")
    return JSONResponse({"detail": detail}, status_code=status_code)


def looks_like_sensitive_log(text: str) -> bool:
    lowered = text.lower()
    forbidden = ("raw_prompt", "prompt=", "matched_text", "clipboard", "keystrokes")
    return any(item in lowered for item in forbidden)
