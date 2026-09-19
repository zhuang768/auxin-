from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import importlib.util
import json
import struct
import sys
from pathlib import Path

import httpx
import pytest

from app.config import settings
from app.db import db_session
from app.routes import line_webhook as webhook_route
from app.services import line_service

ROOT = Path(__file__).resolve().parents[2]
PNG_PATH = ROOT / "assets" / "line-rich-menu.png"
OFFICIAL_HOSTS = {"api.line.me", "api-data.line.me"}
WELCOME_FIRST_MESSAGE = (
    "歡迎使用新竹市青年 AI 數位工具補助服務。\n"
    "透過 LINE，你可以完成補助申請、查詢案件進度，以及學習 AI 安全使用方式。\n"
    "請從下方選單選擇服務。"
)


def signature(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def signed_post(client, payload, monkeypatch, secret="test-secret"):
    monkeypatch.setattr(settings, "line_channel_secret", secret)
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return client.post(
        "/api/line/webhook",
        content=body,
        headers={"X-Line-Signature": signature(body, secret), "Content-Type": "application/json"},
    )


def assert_official_request(request: httpx.Request) -> None:
    assert request.url.scheme == "https"
    assert request.url.host in OFFICIAL_HOSTS
    if "authorization" in request.headers:
        assert request.url.host in OFFICIAL_HOSTS


def install_transport(monkeypatch, handler):
    transport = httpx.MockTransport(handler)

    def factory(**kwargs):
        kwargs["transport"] = transport
        return httpx.AsyncClient(**kwargs)

    monkeypatch.setattr(line_service, "build_async_client", factory)


def load_setup_script():
    path = ROOT / "scripts" / "setup_line_rich_menu.py"
    spec = importlib.util.spec_from_file_location("setup_line_rich_menu", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def no_retry_sleep(monkeypatch):
    async def instant(_seconds=0.0):
        return None

    monkeypatch.setattr(line_service, "retry_sleep", instant)


def test_webhook_rejects_invalid_signature(client, monkeypatch):
    monkeypatch.setattr(settings, "line_channel_secret", "test-secret")
    response = client.post(
        "/api/line/webhook",
        content=b'{"events":[]}',
        headers={"X-Line-Signature": "wrong", "Content-Type": "application/json"},
    )
    assert response.status_code == 401


def test_webhook_rejects_missing_signature(client, monkeypatch):
    monkeypatch.setattr(settings, "line_channel_secret", "test-secret")
    response = client.post(
        "/api/line/webhook",
        content=b'{"events":[]}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 401
    assert "test-secret" not in response.text


def test_webhook_rejects_missing_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "line_channel_secret", "")
    body = b'{"events":[]}'
    response = client.post(
        "/api/line/webhook",
        content=body,
        headers={"X-Line-Signature": signature(body, "test-secret"), "Content-Type": "application/json"},
    )
    assert response.status_code == 401


def test_webhook_accepts_small_valid_payload(client, monkeypatch):
    response = signed_post(client, {"destination": "Udemo", "events": []}, monkeypatch)
    assert response.status_code == 200
    assert response.json() == {"ok": True, "queued": 0}


def test_signature_is_validated_against_raw_body(client, monkeypatch):
    monkeypatch.setattr(settings, "line_channel_secret", "test-secret")
    body = b'{"destination":"Udemo","events":[ ]}'
    response = client.post(
        "/api/line/webhook",
        content=body,
        headers={"X-Line-Signature": signature(body, "test-secret"), "Content-Type": "application/json"},
    )
    assert response.status_code == 200
    tampered = client.post(
        "/api/line/webhook",
        content=body,
        headers={"X-Line-Signature": signature(b'{"events":[]}', "test-secret"), "Content-Type": "application/json"},
    )
    assert tampered.status_code == 401


def test_webhook_rejects_invalid_json(client, monkeypatch):
    monkeypatch.setattr(settings, "line_channel_secret", "test-secret")
    body = b"not-json"
    response = client.post(
        "/api/line/webhook",
        content=body,
        headers={"X-Line-Signature": signature(body, "test-secret"), "Content-Type": "application/json"},
    )
    assert response.status_code == 400


def test_webhook_rejects_illegal_utf8_json(client, monkeypatch):
    monkeypatch.setattr(settings, "line_channel_secret", "test-secret")
    body = b"\xff\xfe not-utf8"
    response = client.post(
        "/api/line/webhook",
        content=body,
        headers={"X-Line-Signature": signature(body, "test-secret"), "Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert body.decode("latin1") not in response.text


def test_webhook_rejects_oversized_body_without_verifying_or_replying(client, monkeypatch):
    verified = []
    replies = []

    def spy_verify(body, signature_header, channel_secret=None):
        verified.append(len(body))
        return True

    async def fake_reply(reply_token, messages):
        replies.append((reply_token, messages))

    monkeypatch.setattr(webhook_route, "MAX_WEBHOOK_BYTES", 64)
    monkeypatch.setattr(line_service, "verify_signature", spy_verify)
    monkeypatch.setattr(line_service, "reply_message", fake_reply)
    body = b"x" * 200
    response = client.post(
        "/api/line/webhook",
        content=body,
        headers={"X-Line-Signature": "unused", "Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert verified == []
    assert replies == []
    assert "x" * 200 not in response.text
    assert "unused" not in response.text


def test_follow_event_replies_with_two_welcome_messages(client, monkeypatch):
    replies = []

    async def fake_reply(reply_token, messages):
        replies.append((reply_token, messages))

    monkeypatch.setattr(line_service, "reply_message", fake_reply)
    response = signed_post(client, {"events": [{"type": "follow", "replyToken": "reply-token"}]}, monkeypatch)
    assert response.status_code == 200
    assert response.json()["queued"] == 1
    assert replies[0][0] == "reply-token"
    assert replies[0][1][0]["text"] == WELCOME_FIRST_MESSAGE
    assert replies[0][1][0]["text"] == line_service.WELCOME_MESSAGE
    disclaimer = replies[0][1][1]["text"]
    assert "競賽測試版本" in disclaimer
    assert "合成資料" in disclaimer
    assert "並未連接新竹市政府正式申辦系統" in disclaimer
    assert "Phase 2 尚未啟用" in disclaimer


def test_three_rich_menu_postbacks_have_replies(client, monkeypatch):
    replies = []

    async def fake_reply(reply_token, messages):
        replies.append(messages[0]["text"])

    monkeypatch.setattr(line_service, "reply_message", fake_reply)
    for action in ("apply", "status", "security"):
        response = signed_post(
            client,
            {"events": [{"type": "postback", "replyToken": f"token-{action}", "postback": {"data": f"action={action}"}}]},
            monkeypatch,
        )
        assert response.status_code == 200
        assert response.json()["queued"] == 1
    assert replies == [
        line_service.POSTBACK_REPLIES["apply"],
        line_service.POSTBACK_REPLIES["status"],
        line_service.POSTBACK_REPLIES["security"],
    ]
    assert "申請補助" in replies[0]
    assert "查詢進度" in replies[1]
    assert "AI 資安專區" in replies[2]


def test_unknown_events_are_not_queued(client, monkeypatch):
    replies = []

    async def fake_reply(reply_token, messages):
        replies.append(messages)

    monkeypatch.setattr(line_service, "reply_message", fake_reply)
    response = signed_post(
        client,
        {
            "events": [
                {"type": "postback", "replyToken": "t1", "postback": {"data": "action=unknown"}},
                {"type": "message", "replyToken": "t2", "message": {"type": "text", "text": "hello"}},
            ]
        },
        monkeypatch,
    )
    assert response.status_code == 200
    assert response.json()["queued"] == 0
    assert replies == []


def test_multiple_replyable_events_are_queued(client, monkeypatch):
    replies = []

    async def fake_reply(reply_token, messages):
        replies.append(reply_token)

    monkeypatch.setattr(line_service, "reply_message", fake_reply)
    response = signed_post(
        client,
        {
            "events": [
                {"type": "follow", "replyToken": "follow-token"},
                {"type": "postback", "replyToken": "apply-token", "postback": {"data": "action=apply"}},
                {"type": "message", "replyToken": "ignored", "message": {"type": "text", "text": "hi"}},
            ]
        },
        monkeypatch,
    )
    assert response.status_code == 200
    assert response.json()["queued"] == 2
    assert replies == ["follow-token", "apply-token"]


def test_background_reply_failure_does_not_leak_secrets(client, monkeypatch):
    async def fake_reply(reply_token, messages):
        raise line_service.LineMessagingError("LINE reply API 回應 500。")

    monkeypatch.setattr(line_service, "reply_message", fake_reply)
    monkeypatch.setattr(settings, "line_channel_access_token", "super-secret-token")
    response = signed_post(client, {"events": [{"type": "follow", "replyToken": "reply-token"}]}, monkeypatch)
    assert response.status_code == 200
    assert response.json()["queued"] == 1
    assert "super-secret-token" not in response.text
    assert "Bearer" not in response.text
    assert "reply-token" not in response.text


def test_malformed_postback_events_are_ignored(client, monkeypatch):
    replies = []

    async def fake_reply(reply_token, messages):
        replies.append(messages)

    monkeypatch.setattr(line_service, "reply_message", fake_reply)
    response = signed_post(
        client,
        {
            "events": [
                {"type": "postback", "replyToken": "t-null", "postback": None},
                {"type": "postback", "replyToken": "t-str", "postback": "action=apply"},
                {"type": "postback", "replyToken": "t-list", "postback": ["action=apply"]},
                {"type": "postback", "replyToken": "t-data", "postback": {"data": 123}},
                "not-an-object",
                {"type": "follow", "replyToken": ""},
            ]
        },
        monkeypatch,
    )
    assert response.status_code == 200
    assert response.json()["queued"] == 0
    assert replies == []


def test_webhook_does_not_write_application_rows(client, monkeypatch):
    async def fake_reply(reply_token, messages):
        return None

    monkeypatch.setattr(line_service, "reply_message", fake_reply)
    with db_session() as conn:
        before = conn.execute("SELECT COUNT(*) AS n FROM applications").fetchone()["n"]
    signed_post(client, {"events": [{"type": "follow", "replyToken": "reply-token"}]}, monkeypatch)
    with db_session() as conn:
        after = conn.execute("SELECT COUNT(*) AS n FROM applications").fetchone()["n"]
    assert after == before


def test_rich_menu_uses_three_postback_areas():
    spec = line_service.rich_menu_spec()
    assert spec["size"] == {"width": 2500, "height": 843}
    assert len(spec["areas"]) == 3
    assert [area["action"]["type"] for area in spec["areas"]] == ["postback", "postback", "postback"]
    assert [area["action"]["data"] for area in spec["areas"]] == [
        "action=apply",
        "action=status",
        "action=security",
    ]
    cursor = 0
    for area in spec["areas"]:
        bounds = area["bounds"]
        assert bounds["x"] == cursor
        assert bounds["y"] == 0
        assert bounds["height"] == 843
        assert bounds["width"] > 0
        cursor += bounds["width"]
    assert cursor == 2500


def test_line_api_hosts_are_locked_official_https(monkeypatch):
    monkeypatch.setenv("LINE_API_BASE_URL", "https://evil.example")
    monkeypatch.setenv("LINE_API_DATA_BASE_URL", "http://evil.example")
    assert line_service.LINE_API_BASE_URL == "https://api.line.me"
    assert line_service.LINE_API_DATA_BASE_URL == "https://api-data.line.me"


def test_reply_message_posts_to_official_line_api(monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert_official_request(request)
        seen.append(str(request.url))
        assert request.headers["Authorization"] == "Bearer test-token"
        payload = json.loads(request.content)
        assert payload["replyToken"] == "reply-token"
        return httpx.Response(200, json={})

    monkeypatch.setattr(settings, "line_channel_access_token", "test-token")
    install_transport(monkeypatch, handler)
    asyncio.run(line_service.reply_message("reply-token", [{"type": "text", "text": "hi"}]))
    assert seen == ["https://api.line.me/v2/bot/message/reply"]


def test_reply_message_requires_env_token(monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json={})

    monkeypatch.setattr(settings, "line_channel_access_token", "")
    install_transport(monkeypatch, handler)
    with pytest.raises(line_service.LineMessagingError) as exc:
        asyncio.run(line_service.reply_message("reply-token", [{"type": "text", "text": "hi"}]))
    assert "尚未設定" in str(exc.value)
    assert "Bearer" not in str(exc.value)
    assert seen == []


def test_reply_retries_http_500_then_succeeds(monkeypatch):
    attempts = []
    slept = []

    async def record_sleep(seconds):
        slept.append(seconds)

    def handler(request: httpx.Request) -> httpx.Response:
        assert_official_request(request)
        attempts.append(request.url.path)
        if len(attempts) == 1:
            return httpx.Response(500, json={"message": "nope"})
        return httpx.Response(200, json={})

    monkeypatch.setattr(settings, "line_channel_access_token", "test-token")
    monkeypatch.setattr(line_service, "retry_sleep", record_sleep)
    install_transport(monkeypatch, handler)
    asyncio.run(line_service.reply_message("reply-token", [{"type": "text", "text": "hi"}]))
    assert attempts == ["/v2/bot/message/reply", "/v2/bot/message/reply"]
    assert slept == [pytest.approx(0.05)]


def test_reply_retries_http_429_then_succeeds(monkeypatch):
    attempts = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert_official_request(request)
        attempts.append(request.headers["Authorization"])
        if len(attempts) == 1:
            return httpx.Response(429)
        return httpx.Response(200, json={})

    monkeypatch.setattr(settings, "line_channel_access_token", "test-token")
    install_transport(monkeypatch, handler)
    asyncio.run(line_service.reply_message("reply-token", [{"type": "text", "text": "hi"}]))
    assert attempts == ["Bearer test-token", "Bearer test-token"]


def test_reply_retries_transport_error_then_succeeds(monkeypatch):
    attempts = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert_official_request(request)
        attempts.append(1)
        if len(attempts) == 1:
            raise httpx.ConnectError("boom", request=request)
        return httpx.Response(200, json={})

    monkeypatch.setattr(settings, "line_channel_access_token", "test-token")
    install_transport(monkeypatch, handler)
    asyncio.run(line_service.reply_message("reply-token", [{"type": "text", "text": "hi"}]))
    assert attempts == [1, 1]


def test_reply_does_not_retry_http_400(monkeypatch):
    attempts = []
    slept = []

    async def record_sleep(seconds):
        slept.append(seconds)

    def handler(request: httpx.Request) -> httpx.Response:
        assert_official_request(request)
        attempts.append(1)
        return httpx.Response(400, json={"message": "bad"})

    monkeypatch.setattr(settings, "line_channel_access_token", "super-secret-token")
    monkeypatch.setattr(line_service, "retry_sleep", record_sleep)
    install_transport(monkeypatch, handler)
    with pytest.raises(line_service.LineMessagingError) as exc:
        asyncio.run(line_service.reply_message("reply-token", [{"type": "text", "text": "secret-chat"}]))
    assert str(exc.value) == "LINE reply API 回應 400。"
    assert "super-secret-token" not in str(exc.value)
    assert "reply-token" not in str(exc.value)
    assert "secret-chat" not in str(exc.value)
    assert attempts == [1]
    assert slept == []


def test_reply_gives_up_after_three_safe_failures(monkeypatch):
    attempts = []
    slept = []

    async def record_sleep(seconds):
        slept.append(seconds)

    def handler(request: httpx.Request) -> httpx.Response:
        assert_official_request(request)
        attempts.append(500)
        return httpx.Response(500, text="internal")

    monkeypatch.setattr(settings, "line_channel_access_token", "super-secret-token")
    monkeypatch.setattr(line_service, "retry_sleep", record_sleep)
    install_transport(monkeypatch, handler)
    with pytest.raises(line_service.LineMessagingError) as exc:
        asyncio.run(line_service.reply_message("reply-token", [{"type": "text", "text": "hi"}]))
    assert str(exc.value) == "LINE reply API 回應 500。"
    assert "super-secret-token" not in str(exc.value)
    assert "internal" not in str(exc.value)
    assert attempts == [500, 500, 500]
    assert slept == [pytest.approx(0.05), pytest.approx(0.15)]
    assert sum(slept) < 30


def test_authorization_is_not_sent_to_non_official_host(monkeypatch):
    seen_hosts = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_hosts.append(request.url.host)
        if "authorization" in request.headers:
            assert request.url.host in OFFICIAL_HOSTS
            assert request.url.scheme == "https"
        return httpx.Response(200, json={})

    monkeypatch.setattr(settings, "line_channel_access_token", "super-secret-token")
    install_transport(monkeypatch, handler)
    asyncio.run(line_service.reply_message("reply-token", [{"type": "text", "text": "hi"}]))
    assert seen_hosts == ["api.line.me"]


def _existing_menu(menu_id="richmenu-existing", **overrides):
    menu = dict(line_service.rich_menu_spec())
    menu["richMenuId"] = menu_id
    menu.update(overrides)
    return menu


def test_create_rich_menu_reuses_matching_menu(monkeypatch, tmp_path):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert_official_request(request)
        calls.append((request.method, request.url.path))
        if request.method == "GET" and request.url.path == "/v2/bot/richmenu/list":
            return httpx.Response(200, json={"richmenus": [_existing_menu(), _existing_menu("richmenu-other", name="其他")]})
        if request.method == "POST" and request.url.path == "/v2/bot/user/all/richmenu/richmenu-existing":
            return httpx.Response(200, json={})
        raise AssertionError(f"unexpected {request.method} {request.url}")

    monkeypatch.setattr(settings, "line_channel_access_token", "test-token")
    install_transport(monkeypatch, handler)
    image = tmp_path / "menu.png"
    image.write_bytes(PNG_PATH.read_bytes())
    first = asyncio.run(line_service.create_and_set_default_rich_menu(image))
    second = asyncio.run(line_service.create_and_set_default_rich_menu(image))
    assert first == second == "richmenu-existing"
    assert ("POST", "/v2/bot/richmenu") not in calls
    assert ("DELETE", "/v2/bot/richmenu/richmenu-existing") not in calls
    assert ("DELETE", "/v2/bot/richmenu/richmenu-other") not in calls


def test_create_rich_menu_creates_when_missing(monkeypatch, tmp_path):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert_official_request(request)
        calls.append((request.method, str(request.url)))
        if request.method == "GET" and request.url.path == "/v2/bot/richmenu/list":
            return httpx.Response(200, json={"richmenus": [_existing_menu("richmenu-other", name="其他")]})
        if request.method == "POST" and request.url.path == "/v2/bot/richmenu":
            return httpx.Response(200, json={"richMenuId": "richmenu-new"})
        if request.method == "POST" and request.url.path.endswith("/content"):
            assert request.url.host == "api-data.line.me"
            return httpx.Response(200, json={})
        if request.method == "POST" and request.url.path == "/v2/bot/user/all/richmenu/richmenu-new":
            return httpx.Response(200, json={})
        if request.method == "DELETE":
            raise AssertionError("must not delete existing menus")
        raise AssertionError(f"unexpected {request.method} {request.url}")

    monkeypatch.setattr(settings, "line_channel_access_token", "test-token")
    install_transport(monkeypatch, handler)
    image = tmp_path / "menu.png"
    image.write_bytes(PNG_PATH.read_bytes())
    rich_menu_id = asyncio.run(line_service.create_and_set_default_rich_menu(image))
    assert rich_menu_id == "richmenu-new"
    assert calls == [
        ("GET", "https://api.line.me/v2/bot/richmenu/list"),
        ("POST", "https://api.line.me/v2/bot/richmenu"),
        ("POST", "https://api-data.line.me/v2/bot/richmenu/richmenu-new/content"),
        ("POST", "https://api.line.me/v2/bot/user/all/richmenu/richmenu-new"),
    ]


def test_upload_failure_deletes_only_new_menu(monkeypatch, tmp_path):
    deleted = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert_official_request(request)
        if request.method == "GET" and request.url.path == "/v2/bot/richmenu/list":
            return httpx.Response(200, json={"richmenus": [_existing_menu("richmenu-old", name="舊選單")]})
        if request.method == "POST" and request.url.path == "/v2/bot/richmenu":
            return httpx.Response(200, json={"richMenuId": "richmenu-new"})
        if request.method == "POST" and request.url.path.endswith("/content"):
            return httpx.Response(500)
        if request.method == "DELETE":
            deleted.append(request.url.path)
            return httpx.Response(200)
        raise AssertionError(f"unexpected {request.method} {request.url}")

    monkeypatch.setattr(settings, "line_channel_access_token", "test-token")
    install_transport(monkeypatch, handler)
    image = tmp_path / "menu.png"
    image.write_bytes(PNG_PATH.read_bytes())
    with pytest.raises(line_service.LineMessagingError) as exc:
        asyncio.run(line_service.create_and_set_default_rich_menu(image))
    assert "圖片上傳失敗" in str(exc.value)
    assert deleted == ["/v2/bot/richmenu/richmenu-new"]


def test_set_default_failure_deletes_only_new_menu(monkeypatch, tmp_path):
    deleted = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert_official_request(request)
        if request.method == "GET" and request.url.path == "/v2/bot/richmenu/list":
            return httpx.Response(200, json={"richmenus": []})
        if request.method == "POST" and request.url.path == "/v2/bot/richmenu":
            return httpx.Response(200, json={"richMenuId": "richmenu-new"})
        if request.method == "POST" and request.url.path.endswith("/content"):
            return httpx.Response(200)
        if request.method == "POST" and request.url.path == "/v2/bot/user/all/richmenu/richmenu-new":
            return httpx.Response(500)
        if request.method == "DELETE":
            deleted.append(request.url.path)
            return httpx.Response(200)
        raise AssertionError(f"unexpected {request.method} {request.url}")

    monkeypatch.setattr(settings, "line_channel_access_token", "test-token")
    install_transport(monkeypatch, handler)
    image = tmp_path / "menu.png"
    image.write_bytes(PNG_PATH.read_bytes())
    with pytest.raises(line_service.LineMessagingError):
        asyncio.run(line_service.create_and_set_default_rich_menu(image))
    assert deleted == ["/v2/bot/richmenu/richmenu-new"]


def test_reuse_set_default_failure_does_not_delete_existing(monkeypatch, tmp_path):
    deleted = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert_official_request(request)
        if request.method == "GET" and request.url.path == "/v2/bot/richmenu/list":
            return httpx.Response(200, json={"richmenus": [_existing_menu()]})
        if request.method == "POST" and request.url.path == "/v2/bot/user/all/richmenu/richmenu-existing":
            return httpx.Response(500)
        if request.method == "DELETE":
            deleted.append(request.url.path)
            return httpx.Response(200)
        raise AssertionError(f"unexpected {request.method} {request.url}")

    monkeypatch.setattr(settings, "line_channel_access_token", "test-token")
    install_transport(monkeypatch, handler)
    image = tmp_path / "menu.png"
    image.write_bytes(PNG_PATH.read_bytes())
    with pytest.raises(line_service.LineMessagingError):
        asyncio.run(line_service.create_and_set_default_rich_menu(image))
    assert deleted == []


def test_rich_menu_png_matches_spec():
    data = PNG_PATH.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert data[12:16] == b"IHDR"
    width, height = struct.unpack(">II", data[16:24])
    assert (width, height) == (2500, 843)
    assert PNG_PATH.stat().st_size < 1024 * 1024


def test_setup_script_default_is_dry_run(monkeypatch, capsys):
    mod = load_setup_script()

    async def boom(_path):
        raise AssertionError("dry-run must not call LINE API")

    monkeypatch.setattr(mod, "create_and_set_default_rich_menu", boom)
    monkeypatch.setattr(sys, "argv", ["setup_line_rich_menu.py"])
    assert mod.main() == 0
    output = capsys.readouterr().out
    assert "mode=dry-run" in output
    assert "action=apply" in output
    assert "2500x843" in output
    assert "Bearer" not in output
    assert "LINE_CHANNEL_ACCESS_TOKEN" not in output


def test_setup_script_dry_run_flag(monkeypatch, capsys):
    mod = load_setup_script()

    async def boom(_path):
        raise AssertionError("dry-run must not call LINE API")

    monkeypatch.setattr(mod, "create_and_set_default_rich_menu", boom)
    monkeypatch.setattr(sys, "argv", ["setup_line_rich_menu.py", "--dry-run"])
    assert mod.main() == 0
    assert "mode=dry-run" in capsys.readouterr().out


def test_setup_script_apply_calls_api(monkeypatch, capsys):
    mod = load_setup_script()
    called = []

    async def fake_create(path):
        called.append(Path(path).name)
        return "richmenu-demo"

    monkeypatch.setattr(mod, "create_and_set_default_rich_menu", fake_create)
    monkeypatch.setattr(sys, "argv", ["setup_line_rich_menu.py", "--apply"])
    assert mod.main() == 0
    assert called == ["line-rich-menu.png"]
    assert "richmenu-demo" in capsys.readouterr().out


def test_setup_script_rejects_apply_with_dry_run(monkeypatch, capsys):
    mod = load_setup_script()

    async def boom(_path):
        raise AssertionError("must not call LINE API")

    monkeypatch.setattr(mod, "create_and_set_default_rich_menu", boom)
    monkeypatch.setattr(sys, "argv", ["setup_line_rich_menu.py", "--apply", "--dry-run"])
    assert mod.main() == 2
    assert "不可同時使用" in capsys.readouterr().err


def test_env_example_has_placeholder_line_keys():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assignments = {}
    for line in text.splitlines():
        if line.startswith("LINE_CHANNEL_ACCESS_TOKEN=") or line.startswith("LINE_CHANNEL_SECRET="):
            key, _, value = line.partition("=")
            assignments[key] = value
    assert assignments.get("LINE_CHANNEL_ACCESS_TOKEN") == ""
    assert assignments.get("LINE_CHANNEL_SECRET") == ""
    assert "LINE_API_BASE_URL" not in text
    assert "LINE_API_DATA_BASE_URL" not in text
