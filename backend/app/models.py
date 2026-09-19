from __future__ import annotations

APPLICATION_STATUSES = (
    "draft",
    "submitted",
    "under_review",
    "needs_revision",
    "rejected",
    "approved",
    "completed",
)

STATUS_LABELS = {
    "draft": "草稿",
    "submitted": "已送出",
    "under_review": "審查中",
    "needs_revision": "需補件",
    "rejected": "未通過",
    "approved": "已核准",
    "completed": "已完成",
}

ALLOWED_TRANSITIONS = {
    "draft": {"submitted"},
    "submitted": {"under_review"},
    "under_review": {"needs_revision", "rejected", "approved"},
    "needs_revision": {"submitted"},
    "approved": {"completed"},
    "rejected": set(),
    "completed": set(),
}

USER_TRANSITIONS = {
    "draft": {"submitted"},
    "needs_revision": {"submitted"},
}

ADMIN_TRANSITIONS = {
    "submitted": {"under_review"},
    "under_review": {"needs_revision", "rejected", "approved"},
    "approved": {"completed"},
}

RISK_CATEGORIES = (
    "tw_id",
    "credit_card",
    "phone",
    "email",
    "address",
    "custom_sensitive_term",
)

RISK_ACTIONS = ("cancelled", "masked", "overridden")

CATEGORY_LABELS = {
    "tw_id": "台灣身分證字號",
    "credit_card": "信用卡號",
    "phone": "手機號碼",
    "email": "電子郵件",
    "address": "地址或敏感詞",
    "custom_sensitive_term": "自訂敏感詞",
}

ACTION_LABELS = {
    "cancelled": "返回修改",
    "masked": "安全遮蔽後送出",
    "overridden": "了解風險後仍送出",
}

LEARNING_MODULES = ("guide", "quiz", "protection_demo")

MODULE_LABELS = {
    "guide": "安全檢查懶人包",
    "quiz": "三題情境測驗",
    "protection_demo": "安全改寫示範",
}

DEMO_USER_ID = "user_demo_lin"
DEMO_APPLICATION_ID = "app_demo_001"
DEMO_SESSION_ID = "demo-session-linxiaozhu"
