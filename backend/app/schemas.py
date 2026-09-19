from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import RISK_ACTIONS, RISK_CATEGORIES

RiskCategory = Literal[
    "tw_id",
    "credit_card",
    "phone",
    "email",
    "address",
    "custom_sensitive_term",
]
RiskAction = Literal["cancelled", "masked", "overridden"]
NotifyChannel = Literal["in_app", "line", "email", "sms"]
ApplicationStatus = Literal[
    "draft",
    "submitted",
    "under_review",
    "needs_revision",
    "rejected",
    "approved",
    "completed",
]


class ForbiddenMixin(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ApplicationCreate(ForbiddenMixin):
    display_name: str = Field(min_length=1, max_length=40)
    email: str = Field(min_length=3, max_length=120)
    phone: str = Field(min_length=8, max_length=20)
    identity_type: Literal["general", "disadvantaged"]
    tool_category: Literal["conversational_llm", "image_video", "productivity"]
    tool_name: str = Field(min_length=1, max_length=80)
    purpose: str = Field(min_length=1, max_length=400)
    notify_in_app: bool = True
    notify_line: bool = True
    notify_email: bool = False
    notify_sms: bool = False


class ApplicationReview(ForbiddenMixin):
    to_status: ApplicationStatus
    revision_reason: Optional[str] = Field(default=None, max_length=400)
    note: Optional[str] = Field(default=None, max_length=400)


class LearningCompletionIn(ForbiddenMixin):
    module: Literal["guide", "quiz", "protection_demo"]
    version: str = Field(default="demo-1", max_length=32)


class RiskEventIn(ForbiddenMixin):
    category: RiskCategory
    action: RiskAction
    occurred_at: datetime
    client_version: str = Field(min_length=1, max_length=32)
    demo_session_id: str = Field(min_length=4, max_length=64)

    @field_validator("category")
    @classmethod
    def category_allowed(cls, value: str) -> str:
        if value not in RISK_CATEGORIES:
            raise ValueError("不支援的風險類別")
        return value

    @field_validator("action")
    @classmethod
    def action_allowed(cls, value: str) -> str:
        if value not in RISK_ACTIONS:
            raise ValueError("不支援的處理結果")
        return value


class AttestationCompleteIn(ForbiddenMixin):
    nonce_id: str = Field(min_length=8, max_length=80)


class NotificationTestIn(ForbiddenMixin):
    event_type: str = Field(min_length=3, max_length=64)
    channel: NotifyChannel = "line"


class AdminLoginIn(ForbiddenMixin):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
    csrf_token: Optional[str] = None
