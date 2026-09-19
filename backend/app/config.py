from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]

load_dotenv(ROOT_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env")


def _bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    app_name = "竹青安心GO"
    demo_mode = True
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    database_path = Path(os.getenv("DATABASE_PATH", str(BACKEND_DIR / "data" / "app.db")))
    if not database_path.is_absolute():
        database_path = (BACKEND_DIR / database_path).resolve()

    session_secret = os.getenv("SESSION_SECRET", "demo-session-secret-not-for-production")
    hmac_secret = os.getenv("ATTESTATION_HMAC_SECRET", "demo-hmac-secret-not-for-production")
    admin_username = os.getenv("DEMO_ADMIN_USERNAME", "demo-admin")
    admin_password = os.getenv("DEMO_ADMIN_PASSWORD", "demo-admin-not-for-production")
    nonce_ttl_seconds = int(os.getenv("NONCE_TTL_SECONDS", "300"))

    cors_origins = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
    ]

    line_messaging_enabled = _bool("LINE_MESSAGING_ENABLED", "false")
    line_dry_run = _bool("LINE_DRY_RUN", "true")
    line_channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    line_channel_secret = os.getenv("LINE_CHANNEL_SECRET", "")
    line_to_user_id = os.getenv("LINE_TO_USER_ID", "")

    email_enabled = _bool("EMAIL_ENABLED", "false")
    sms_enabled = _bool("SMS_ENABLED", "false")

    client_version = "1.0.0"


settings = Settings()
