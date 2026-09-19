# LINE Messaging API Phase 1

這份文件只涵蓋 Phase 1：真實 LINE Webhook、加入好友 Welcome Message，以及三區塊 Rich Menu。沒有申請對話、案件查詢、帳號綁定、LIFF 或市府後台變更。Phase 2 尚未實作。

竹青安心GO 是可與新竹市既有數位申辦平台整合的 LINE 原生公共服務原型。目前使用團隊測試帳號與合成資料驗證；正式導入仍需市府授權、身分驗證、資安審查、個資影響評估及正式系統串接。

這是競賽／測試頻道能力，**不是**新竹市政府正式官方帳號。

**Phase 1 程式與本機測試完成。** 不可寫「真實 LINE 驗證通過」。真實手機、公開 HTTPS Webhook 與 Rich Menu 實際上傳仍未驗證。

## 範圍

Phase 1 會做：

- `POST /api/line/webhook` 以 `request.stream()` 分段讀取 body；超過 1MB 立即回 `413`，不驗簽、不解析、不排程 Reply。
- 以原始 request body、Channel Secret、HMAC-SHA256 與 Base64 驗證 `X-Line-Signature`。
- LINE 平台的空 `events` 驗證請求回 `200`。
- 錯誤或缺少簽章時拒絕（`401`）。
- 驗簽與最小 JSON schema 通過後快速回 `200`，`queued` 代表已排程背景 Reply，不是已送達。
- `follow` 事件回兩則文字：第一則為指定 Welcome；第二則說明競賽測試版本、合成資料、未連接市府正式系統，以及 Phase 2 尚未啟用。
- Rich Menu 三個完整無縫區塊，皆為 postback：`action=apply`、`action=status`、`action=security`。
- Reply API 對 transport error、timeout、HTTP 429 與 HTTP 5xx 最多重試 3 次（best-effort，不是 exactly-once，也不保證送達）。HTTP 4xx（429 除外）不重試。
- 以 `scripts/setup_line_rich_menu.py` 預設 dry-run；真實修改必須加 `--apply`。

Phase 1 不會做（留給後續階段）：

- 補助說明 Flex Message、資格預檢、申請對話或案件狀態查詢。
- 把 LINE userId 寫進資料庫，或把它當成政府身分驗證。
- 變更申請流程、狀態機、資料庫 schema 或市府後台。
- 透過 LINE 傳送含個資、原始 Prompt、文件內容或補助核准結果的訊息。
- 部署、公開 HTTPS、實際上傳 Rich Menu，或呼叫真實 LINE API。

文字訊息、未知 postback 與 malformed event 會被忽略，Webhook 仍回 `200`。背景 Reply 失敗不會進入 HTTP 回應，也不含 Token。

## Webhook Endpoint

本機：

```text
POST http://127.0.0.1:8000/api/line/webhook
```

公開 HTTPS（尚未設定，需自行準備 tunnel 或主機）：

```text
POST https://<your-host>/api/line/webhook
```

LINE Developers Console 必須填完整 HTTPS URL，不可使用 `http://localhost`。

應用程式會拒絕超過 1MB 的 Webhook body。正式部署仍須在 reverse proxy／hosting platform 設定同等或更小的 request body 上限，否則超大請求可能在到達 FastAPI 前就佔用記憶體。

## 環境變數

複製 `.env.example` 為 `.env` 後填入本機值。不要把真實值提交到 repository。

| 變數 | 用途 |
|---|---|
| `LINE_CHANNEL_SECRET` | Webhook `X-Line-Signature` 驗證。未填則所有 Webhook 回 `401`。 |
| `LINE_CHANNEL_ACCESS_TOKEN` | Reply API 與 Rich Menu API。未填則不呼叫 LINE。 |

LINE API 主機固定為 `https://api.line.me` 與 `https://api-data.line.me`，不能用環境變數改寫。測試以 httpx MockTransport 或 client factory 注入攔截。

`LINE_MESSAGING_ENABLED` 與 `LINE_DRY_RUN` 仍只影響既有站內通知 mock，**不控制** Phase 1 Webhook。`LINE_TO_USER_ID` 為舊版 dry-run 欄位，Phase 1 不使用。

## LINE Developers Console 設定

使用團隊自己的 LINE Developers Provider 與 Messaging API Channel，不要連接或宣稱已連接新竹市政府正式官方帳號。

1. 建立 Messaging API channel（測試用 Official Account）。
2. **Basic settings**：複製 Channel secret 到 `LINE_CHANNEL_SECRET`。
3. **Messaging API**：發行長期 Channel access token，複製到 `LINE_CHANNEL_ACCESS_TOKEN`。
4. Webhook URL 設為 `https://<your-host>/api/line/webhook`。
5. 開啟 **Use webhook**，用 Console 的 Verify 確認空 `events` 可回 `200`。
6. 在 LINE Official Account Manager 關閉內建「加入好友歡迎訊息」與「自動回應訊息」，避免與後端 Welcome／選單回覆重複。
7. 尚未準備公開 HTTPS 前，不要開啟 Webhook；本機測試只跑單元測試與 Rich Menu dry-run。

## Rich Menu 建立方式

圖片為 `assets/line-rich-menu.png`（PNG、2500×843、小於 1MB）。原始稿為 `assets/line-rich-menu.svg`。三個區塊由左到右：

- 申請補助 → `action=apply`
- 查詢進度 → `action=status`
- AI資安專區 → `action=security`

不加參數或加 `--dry-run` 都只驗證規格，**不會**呼叫 LINE API：

```bash
backend/.venv/bin/python scripts/setup_line_rich_menu.py
backend/.venv/bin/python scripts/setup_line_rich_menu.py --dry-run
```

真實建立或重用既有相同選單（需要已填 Token，且會呼叫 LINE API；本次不執行）：

```bash
backend/.venv/bin/python scripts/setup_line_rich_menu.py --apply
```

`--apply` 會先列出既有 Rich Menu，名稱與規格完全相符就重用並設為預設，不會新增相同選單。若本次新建後 upload 或 set-default 失敗，只會 best-effort 刪除本次新建的 menu，不會刪除原有 default 或其他 menu。不可同時使用 `--dry-run` 與 `--apply`。

## 手機實測步驟

只有完成以下操作，才可寫「Phase 1 真實 LINE 驗證通過」。目前尚未完成：

1. 掃描測試帳號 QR Code，加入官方帳號。
2. 收到兩則 Welcome Message。
3. 看見 Rich Menu。
4. 點擊申請補助，收到「已選擇該服務、後續流程尚未啟用」的回覆。
5. 點擊查詢進度，收到對應誠實回覆。
6. 點擊 AI 資安專區，收到對應誠實回覆。

目前尚未取得真實 Channel Secret、Access Token、公開 HTTPS Webhook，也尚未上傳 Rich Menu。因此：

**Phase 1 程式與本機測試完成；真實手機 LINE、公開 Webhook 與 Rich Menu 上傳尚未驗證。**

## 測試

```bash
cd backend
./.venv/bin/python -m pytest tests/test_line_webhook.py -q
./.venv/bin/python -m pytest -q
```

測試覆蓋：無效／缺少簽章、原始 body 簽章、小型合法 payload、超限 413 且不驗簽不排程、驗證請求、兩則 Welcome、三個 postback、多事件排程、忽略未知與 malformed event、背景失敗仍回 200 且不洩漏 Token、Reply 有限重試、官方 HTTPS 網域、Rich Menu 重用與失敗清理、預設 dry-run、`.env.example` 不含真實金鑰或可覆寫 API host。

## 資安與個資限制

- 不把完整 Webhook payload、聊天原文、Channel Secret、Access Token、reply token 或 user ID 寫入程式碼或長期 log。
- Reply／Rich Menu 錯誤只回報 HTTP 狀態或連線失敗，不含 Token 或聊天內容。
- Reply 重試是 best-effort，不是 exactly-once，也不保證在 reply token 有效期內送達。
- LINE User ID 不是政府身分驗證。
- Phase 1 不處理身分證、戶籍地址、存摺、銀行資料或其他高敏感文件。
- 競賽 Demo 只能使用合成資料。

## 已知限制

- 尚未以真實手機 LINE 與公開 HTTPS Webhook 端到端驗證。
- 沒有市政府正式帳號授權。
- Phase 2 以後的對話流程尚未實作；選單回覆會明確這樣說。
- 應用程式 1MB 上限無法取代 hosting／reverse proxy 的 body 限制。
