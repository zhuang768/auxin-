const DEFAULT_API_BASE = "http://127.0.0.1:8000";

async function apiBase() {
  const stored = await chrome.storage.local.get(["apiBase"]);
  return stored.apiBase || DEFAULT_API_BASE;
}

function whitelistPayload(message) {
  return {
    category: message.category,
    action: message.action,
    occurred_at: message.occurred_at,
    client_version: message.client_version,
    demo_session_id: message.demo_session_id,
  };
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  handle(message).then(sendResponse).catch((error) => {
    sendResponse({ ok: false, error: error.message });
  });
  return true;
});

async function handle(message) {
  const base = await apiBase();
  if (message.type === "RISK_EVENT") {
    const body = whitelistPayload(message);
    try {
      await fetch(`${base}/api/risk-events`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    } catch (_error) {
      // 核心流程不依賴網路；失敗時仍回報本機已處理。
    }
    return { ok: true };
  }
  if (message.type === "LEARNING_COMPLETE") {
    try {
      await fetch(`${base}/api/learning/completions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ module: message.module, version: "demo-1" }),
      });
    } catch (_error) {
      // ignore
    }
    return { ok: true };
  }
  if (message.type === "GET_STATUS") {
    return { ok: true, apiBase: base, version: "1.0.0" };
  }
  return { ok: false, error: "unknown" };
}
