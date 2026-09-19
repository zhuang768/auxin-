from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import BACKEND_DIR, settings
from app.db import init_db
from app.models import DEMO_USER_ID
from app.routes import admin, api_applications, api_attestations, api_demo, api_learning, api_risk_events, line_webhook, portal
from app.security import security_headers_middleware
from app.seed import reset_and_seed

logger = logging.getLogger("zhuqing")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")


def create_app() -> FastAPI:
    app = FastAPI(
        title="竹青安心GO",
        description="競賽 Demo：本機個資防護、補助入口與市府審查工作台。非正式生產系統。",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        same_site="lax",
        https_only=False,
        max_age=60 * 60 * 8,
    )

    app.mount("/static", StaticFiles(directory=str(BACKEND_DIR / "static")), name="static")
    app.include_router(portal.router)
    app.include_router(admin.router)
    app.include_router(api_applications.router)
    app.include_router(api_learning.router)
    app.include_router(api_risk_events.router)
    app.include_router(api_attestations.router)
    app.include_router(api_demo.router)
    app.include_router(line_webhook.router)

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        return security_headers_middleware(response)

    @app.on_event("startup")
    def startup():
        init_db()
        from app.db import db_session

        with db_session() as conn:
            user = conn.execute("SELECT id FROM users WHERE id = ?", (DEMO_USER_ID,)).fetchone()
        if user is None:
            reset_and_seed()
        logger.info("demo backend started; database=%s", settings.database_path)

    @app.get("/demo")
    def legacy_demo():
        return RedirectResponse(url="/", status_code=303)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        if isinstance(exc, HTTPException):
            return await http_exception_handler(request, exc)
        if isinstance(exc, RequestValidationError):
            return await request_validation_exception_handler(request, exc)
        logger.exception("unhandled error on %s", request.url.path)
        return JSONResponse({"detail": "伺服器發生錯誤，請稍後再試。"}, status_code=500)

    return app


app = create_app()
