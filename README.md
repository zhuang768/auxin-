# 竹青安心GO

青年準備把內容送進 ChatGPT、Claude、Gemini 時，系統在資料離開裝置前於本機辨識可能的個資，解釋風險並提供安全改寫；市府只看到申請狀態與匿名彙總，看不到原始 Prompt。

這是 2026 新竹 X 梅竹黑客松・創客交流組的競賽 Demo，不是市政府正式申辦系統。

## 架構

```text
瀏覽器擴充功能（Chrome MV3）
  adapter → detector → masker → 風險抽屜
        ↓ 只上傳 category / action / occurred_at / client_version / demo_session_id
FastAPI + SQLite
  青年入口 / 教材 / 案件狀態機 / 市府工作台 / 站內通知 / LINE dry-run / HMAC 憑證
```

- 後端：`backend/`（FastAPI、SQLite、Jinja）
- 擴充功能：`extension/`
- Demo 腳本：`scripts/reset_demo.py`、`scripts/check_demo.py`
- 企劃基準：`docs/竹青安心GO_完整企劃書.md`

## 安裝與啟動

只可使用下列合成資料：林小竹、`demo@example.test`、`0912-000-111`、虛構地址「新竹市示意區不存在路 1 號」、公開測試卡號 `4111-1111-1111-1111`。不要輸入真實個資。

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # 可選，請改掉示範密鑰
python3 -c "from app.seed import reset_and_seed; reset_and_seed()"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

開啟：

- http://127.0.0.1:8000/ 服務首頁
- http://127.0.0.1:8000/demo-chat 可靠展示入口
- http://127.0.0.1:8000/admin/login 市府工作台
- http://127.0.0.1:8000/demo/readiness 就緒檢查

Demo 管理員預設帳密見 `.env.example`，畫面會標示不可用於正式環境。

## 載入 Chrome 擴充功能

1. 開啟 `chrome://extensions`
2. 開啟「開發人員模式」
3. 「載入未封裝項目」，選本專案 `extension/`
4. 回到 http://127.0.0.1:8000/demo-chat

ChatGPT、Claude、Gemini 適配為 best effort；現場請以 Demo Chat 為準。

## 固定 Demo 腳本

1. 按「一鍵重設 Demo 資料」或執行 `python3 scripts/reset_demo.py`
2. 建立或查看林小竹的申請
3. 完成安全教材與三題測驗
4. 開啟 Demo Chat，按「填入合成測試資料」
5. 送出，擴充功能攔截
6. 選擇「安全遮蔽後送出」
7. 開啟事件頁，確認沒有原始 Prompt
8. 管理員登入並把案件改為審查中或核准
9. 青年端看到站內通知
10. 通知頁查看 LINE dry-run，畫面明示未連政府正式帳號

逐步講稿見 `docs/DEMO_SCRIPT.md`。

## 測試命令

```bash
# Python
cd backend
source .venv/bin/activate
python3 -m compileall app tests
python3 -m pytest

# 擴充功能單元測試
node --test extension/tests/detector.test.mjs

# Manifest
python3 -m json.tool extension/manifest.json >/dev/null

# Demo 就緒
python3 scripts/check_demo.py
```

## Demo／正式功能矩陣

完整表見 `docs/FEATURE_MATRIX.md`。摘要：

| 功能 | 狀態 |
|---|---|
| Demo Chat 本機攔截與遮蔽 | 完成 |
| 補助 Demo 入口與狀態機 | 完成 |
| 市府工作台（Demo 登入） | 完成 |
| 安全教材、案例、測驗 | 完成 |
| 站內通知 | 完成 |
| LINE 通知 | PoC／dry-run |
| LINE Webhook／Welcome／Rich Menu | Phase 1 本機完成；真實手機未驗證 |
| HMAC 完成憑證 | PoC |
| ChatGPT／Claude／Gemini 適配 | best effort |
| 正式身分驗證、撥款、政府 LINE | 未完成 |

## 已知限制

- 規則式偵測會漏接自由書寫的敏感內容。
- 不保證偵測所有個資。
- LINE 未連接新竹市政府正式帳號；沒有授權時不會真的外送。
- 完成憑證只證明 Demo 流程完整性，不是政府身分驗證。
- 第三方 AI 網站 DOM 改版可能使適配失效；備援是 Demo Chat。
- Chrome 擴充功能需人工載入；本環境若無 Chrome 即標示為未驗證。

## LINE Messaging API Phase 1

青年端主要入口改為團隊測試用 LINE Official Account，不是偽 LINE 網頁。Phase 1 程式與本機測試完成：Webhook 簽章、快速 200 與背景 Reply、兩則 Welcome Message，以及三區塊 Rich Menu postback。設定、限制與測試說明見 `docs/LINE_PHASE1.md`。

申請對話（Phase 2）尚未實作。真實手機 LINE、公開 HTTPS Webhook 與 Rich Menu 實際上傳尚未驗證。真實修改 Rich Menu 必須使用 `scripts/setup_line_rich_menu.py --apply`。這不是新竹市政府正式官方帳號。
