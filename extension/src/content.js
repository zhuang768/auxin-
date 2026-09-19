import { detect } from "./detector/engine.js";
import { maskText } from "./masker/masker.js";
import { resolveAdapter } from "./adapters/index.js";
import { createRiskDrawer } from "./ui/risk-drawer.js";

const CLIENT_VERSION = "1.0.0";
const DEMO_SESSION_ID = "demo-session-linxiaozhu";
let intercepting = false;
let hintEl = null;

function uniqueCategories(findings) {
  return [...new Set(findings.map((item) => item.category))];
}

function showHint(findings) {
  if (!hintEl) {
    hintEl = document.createElement("div");
    hintEl.id = "zqax-inline-hint";
    hintEl.style.cssText = "position:fixed;left:16px;bottom:16px;z-index:2147483645;background:#f7ead4;color:#5c3b0b;padding:8px 12px;border-radius:8px;font:13px/1.4 sans-serif;max-width:280px;";
    document.body.appendChild(hintEl);
  }
  hintEl.textContent = "發現可能的個資，送出前會再請你確認。建議先移除後再送出。";
  hintEl.hidden = findings.length === 0;
}

function report(category, action) {
  chrome.runtime.sendMessage({
    type: "RISK_EVENT",
    category,
    action,
    occurred_at: new Date().toISOString(),
    client_version: CLIENT_VERSION,
    demo_session_id: DEMO_SESSION_ID,
  });
}

function completeProtectionDemo() {
  chrome.runtime.sendMessage({ type: "LEARNING_COMPLETE", module: "protection_demo" });
}

function boot() {
  const adapter = resolveAdapter(window.location);
  const drawer = createRiskDrawer();

  document.addEventListener("input", (event) => {
    const input = adapter.getInput();
    if (!input || event.target !== input) return;
    const findings = detect(adapter.getText(input));
    showHint(findings);
  });

  function intercept(event) {
    if (intercepting) return;
    const input = adapter.getInput();
    if (!input) return;
    const original = adapter.getText(input);
    const findings = detect(original);
    if (!findings.length) return;
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
    intercepting = true;
    drawer.show(findings, {
      onMask() {
        const masked = maskText(original, findings);
        adapter.setText(input, masked);
        uniqueCategories(findings).forEach((category) => report(category, "masked"));
        completeProtectionDemo();
        intercepting = false;
        adapter.approveSend();
      },
      onCancel() {
        uniqueCategories(findings).forEach((category) => report(category, "cancelled"));
        intercepting = false;
        input.focus();
      },
      onOverride() {
        uniqueCategories(findings).forEach((category) => report(category, "overridden"));
        intercepting = false;
        adapter.approveSend();
      },
    });
  }

  document.addEventListener(
    "keydown",
    (event) => {
      if (event.key === "Enter" && !event.shiftKey) intercept(event);
    },
    true
  );
  document.addEventListener(
    "click",
    (event) => {
      const send = adapter.getSendButton();
      if (send && (event.target === send || send.contains(event.target))) intercept(event);
    },
    true
  );

  window.addEventListener("pagehide", () => {
    intercepting = false;
    drawer.hide();
  });
}

boot();
