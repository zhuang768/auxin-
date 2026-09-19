from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status

from app.services import line_service

router = APIRouter(prefix="/api/line", tags=["line"])

MAX_WEBHOOK_BYTES = 1024 * 1024


async def read_limited_body(request: Request, max_bytes: int = MAX_WEBHOOK_BYTES) -> bytes:
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Webhook 內容過大。")
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/webhook")
async def line_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_line_signature: Optional[str] = Header(default=None, alias="X-Line-Signature"),
):
    body = await read_limited_body(request, MAX_WEBHOOK_BYTES)
    if not line_service.verify_signature(body, x_line_signature or ""):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="LINE Webhook 簽章無效。")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook JSON 格式錯誤。") from None
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook JSON 格式錯誤。")

    events = payload.get("events", [])
    if not isinstance(events, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook events 格式錯誤。")

    queued = 0
    for event in events:
        job = line_service.queued_reply(event)
        if not job:
            continue
        event_type, reply_token, messages = job
        background_tasks.add_task(line_service.deliver_reply, event_type, reply_token, messages)
        queued += 1
    return {"ok": True, "queued": queued}
