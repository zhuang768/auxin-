from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import logging
from pathlib import Path
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger("zhuqing.line")

LINE_API_BASE_URL = "https://api.line.me"
LINE_API_DATA_BASE_URL = "https://api-data.line.me"

WELCOME_MESSAGE = (
    "歡迎使用新竹市青年 AI 數位工具補助服務。\n"
    "透過 LINE，你可以完成補助申請、查詢案件進度，以及學習 AI 安全使用方式。\n"
    "請從下方選單選擇服務。"
)

WELCOME_DISCLAIMER = (
    "本服務目前為競賽測試版本，使用合成資料，並未連接新竹市政府正式申辦系統。Phase 2 尚未啟用。"
)

POSTBACK_REPLIES = {
    "apply": "你已選擇「申請補助」。申請對話流程將在下一階段啟用。",
    "status": "你已選擇「查詢進度」。案件查詢功能將在後續階段啟用。",
    "security": "你已選擇「AI 資安專區」。資安內容將在後續階段啟用。",
}

RICH_MENU_SIZE = {"width": 2500, "height": 843}
RICH_MENU_ACTIONS = ("apply", "status", "security")
REPLY_MAX_ATTEMPTS = 3
REPLY_RETRY_BACKOFF_SECONDS = (0.05, 0.15)


class LineMessagingError(RuntimeError):
    pass


def build_async_client(**kwargs: Any) -> httpx.AsyncClient:
    return httpx.AsyncClient(**kwargs)


async def retry_sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)


def verify_signature(body: bytes, signature: str, channel_secret: Optional[str] = None) -> bool:
    secret = channel_secret if channel_secret is not None else settings.line_channel_secret
    if not secret or not signature:
        return False
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("ascii")
    return hmac.compare_digest(expected, signature)


def text_message(text: str) -> dict[str, str]:
    return {"type": "text", "text": text}


def postback_action(data: str) -> Optional[str]:
    for item in data.split("&"):
        key, separator, value = item.partition("=")
        if separator and key == "action":
            return value
    return None


def safe_event_type(event: dict[str, Any]) -> str:
    event_type = event.get("type")
    if isinstance(event_type, str) and event_type:
        return event_type[:32]
    return "invalid"


def reply_for_event(event: dict[str, Any]) -> Optional[list[dict[str, str]]]:
    if not isinstance(event, dict):
        return None
    event_type = event.get("type")
    if event_type == "follow":
        return [text_message(WELCOME_MESSAGE), text_message(WELCOME_DISCLAIMER)]
    if event_type == "postback":
        postback = event.get("postback")
        if not isinstance(postback, dict):
            return None
        data = postback.get("data")
        if not isinstance(data, str):
            return None
        action = postback_action(data)
        reply = POSTBACK_REPLIES.get(action or "")
        if reply:
            return [text_message(reply)]
    return None


def queued_reply(event: Any) -> Optional[tuple[str, str, list[dict[str, str]]]]:
    if not isinstance(event, dict):
        return None
    reply_token = event.get("replyToken")
    if not isinstance(reply_token, str) or not reply_token:
        return None
    messages = reply_for_event(event)
    if not messages:
        return None
    return safe_event_type(event), reply_token, messages


def _should_retry_status(status_code: int) -> bool:
    return status_code == 429 or status_code >= 500


async def reply_message(reply_token: str, messages: list[dict[str, Any]]) -> None:
    token = settings.line_channel_access_token
    if not token:
        raise LineMessagingError("LINE_CHANNEL_ACCESS_TOKEN 尚未設定。")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"replyToken": reply_token, "messages": messages}
    url = f"{LINE_API_BASE_URL}/v2/bot/message/reply"
    async with build_async_client(timeout=10.0) as client:
        for attempt in range(REPLY_MAX_ATTEMPTS):
            try:
                response = await client.post(url, headers=headers, json=payload)
            except httpx.TransportError:
                if attempt >= REPLY_MAX_ATTEMPTS - 1:
                    raise LineMessagingError("LINE reply API 連線失敗。") from None
                await retry_sleep(REPLY_RETRY_BACKOFF_SECONDS[attempt])
                continue
            if response.status_code < 400:
                return
            if _should_retry_status(response.status_code) and attempt < REPLY_MAX_ATTEMPTS - 1:
                await retry_sleep(REPLY_RETRY_BACKOFF_SECONDS[attempt])
                continue
            raise LineMessagingError(f"LINE reply API 回應 {response.status_code}。")


async def deliver_reply(event_type: str, reply_token: str, messages: list[dict[str, Any]]) -> None:
    try:
        await reply_message(reply_token, messages)
    except Exception:
        logger.exception("LINE event reply failed; type=%s", event_type)


def rich_menu_spec() -> dict[str, Any]:
    width = RICH_MENU_SIZE["width"]
    height = RICH_MENU_SIZE["height"]
    labels = ("申請補助", "查詢進度", "AI資安專區")
    areas = []
    x = 0
    for index, (action, label) in enumerate(zip(RICH_MENU_ACTIONS, labels)):
        remaining = 3 - index
        area_width = (width - x) if remaining == 1 else width // 3
        areas.append(
            {
                "bounds": {"x": x, "y": 0, "width": area_width, "height": height},
                "action": {
                    "type": "postback",
                    "label": label,
                    "data": f"action={action}",
                    "displayText": label,
                },
            }
        )
        x += area_width
    return {
        "size": dict(RICH_MENU_SIZE),
        "selected": True,
        "name": "竹青安心GO 主選單",
        "chatBarText": "服務選單",
        "areas": areas,
    }


def _action_identity(action: Any) -> Optional[dict[str, Any]]:
    if not isinstance(action, dict):
        return None
    return {
        "type": action.get("type"),
        "label": action.get("label"),
        "data": action.get("data"),
        "displayText": action.get("displayText"),
    }


def _menu_identity(menu: dict[str, Any]) -> Optional[dict[str, Any]]:
    areas_in = menu.get("areas")
    if not isinstance(areas_in, list):
        return None
    areas = []
    for area in areas_in:
        if not isinstance(area, dict):
            return None
        action = _action_identity(area.get("action"))
        if action is None:
            return None
        areas.append({"bounds": area.get("bounds"), "action": action})
    return {
        "size": menu.get("size"),
        "selected": menu.get("selected"),
        "name": menu.get("name"),
        "chatBarText": menu.get("chatBarText"),
        "areas": areas,
    }


def matching_rich_menu_id(payload: Any, spec: dict[str, Any]) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    menus = payload.get("richmenus")
    if not isinstance(menus, list):
        return None
    wanted = _menu_identity(spec)
    if wanted is None:
        return None
    for menu in menus:
        if not isinstance(menu, dict):
            continue
        if _menu_identity(menu) != wanted:
            continue
        menu_id = menu.get("richMenuId")
        if isinstance(menu_id, str) and menu_id:
            return menu_id
    return None


def _json_payload(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


async def _best_effort_delete_rich_menu(client: httpx.AsyncClient, headers: dict[str, str], rich_menu_id: str) -> None:
    try:
        await client.delete(f"{LINE_API_BASE_URL}/v2/bot/richmenu/{rich_menu_id}", headers=headers)
    except httpx.HTTPError:
        return


async def create_and_set_default_rich_menu(image_path: Path) -> str:
    token = settings.line_channel_access_token
    if not token:
        raise LineMessagingError("LINE_CHANNEL_ACCESS_TOKEN 尚未設定。")
    if not image_path.is_file():
        raise LineMessagingError(f"找不到 Rich Menu 圖片：{image_path}")

    spec = rich_menu_spec()
    headers = {"Authorization": f"Bearer {token}"}
    created_id: Optional[str] = None
    async with build_async_client(timeout=20.0) as client:
        try:
            list_response = await client.get(f"{LINE_API_BASE_URL}/v2/bot/richmenu/list", headers=headers)
            if list_response.is_error:
                raise LineMessagingError(f"LINE Rich Menu 查詢失敗（{list_response.status_code}）。")
            existing_id = matching_rich_menu_id(_json_payload(list_response), spec)
            if existing_id:
                default_response = await client.post(
                    f"{LINE_API_BASE_URL}/v2/bot/user/all/richmenu/{existing_id}",
                    headers=headers,
                )
                if default_response.is_error:
                    raise LineMessagingError(f"LINE Rich Menu 設為預設失敗（{default_response.status_code}）。")
                return existing_id

            create_response = await client.post(
                f"{LINE_API_BASE_URL}/v2/bot/richmenu",
                headers={**headers, "Content-Type": "application/json"},
                json=spec,
            )
            if create_response.is_error:
                raise LineMessagingError(f"LINE Rich Menu 建立失敗（{create_response.status_code}）。")
            payload = _json_payload(create_response)
            try:
                created_id = str(payload["richMenuId"])
            except (TypeError, KeyError, ValueError):
                raise LineMessagingError("LINE Rich Menu 建立失敗（回應格式錯誤）。") from None

            upload_response = await client.post(
                f"{LINE_API_DATA_BASE_URL}/v2/bot/richmenu/{created_id}/content",
                headers={**headers, "Content-Type": "image/png"},
                content=image_path.read_bytes(),
            )
            if upload_response.is_error:
                raise LineMessagingError(f"LINE Rich Menu 圖片上傳失敗（{upload_response.status_code}）。")

            default_response = await client.post(
                f"{LINE_API_BASE_URL}/v2/bot/user/all/richmenu/{created_id}",
                headers=headers,
            )
            if default_response.is_error:
                raise LineMessagingError(f"LINE Rich Menu 設為預設失敗（{default_response.status_code}）。")
            return created_id
        except httpx.HTTPError:
            if created_id:
                await _best_effort_delete_rich_menu(client, headers, created_id)
            raise LineMessagingError("LINE Rich Menu API 連線失敗。") from None
        except LineMessagingError:
            if created_id:
                await _best_effort_delete_rich_menu(client, headers, created_id)
            raise
