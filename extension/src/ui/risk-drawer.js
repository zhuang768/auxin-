export function createRiskDrawer() {
  let host = document.getElementById("zqax-drawer-host");
  if (host) return host._api;

  host = document.createElement("div");
  host.id = "zqax-drawer-host";
  const shadow = host.attachShadow({ mode: "open" });
  shadow.innerHTML = `
    <style>
      :host { all: initial; }
      .wrap { font-family: "PingFang TC","Noto Sans TC","Segoe UI",sans-serif; }
      .overlay { position: fixed; inset: 0; background: rgba(28,42,47,.35); z-index: 2147483646; }
      .drawer {
        position: fixed; right: 16px; bottom: 16px; width: min(420px, calc(100vw - 32px));
        background: #fffdf8; color: #1c2a2f; z-index: 2147483647; border: 1px solid #d7d0c4;
        border-radius: 12px; box-shadow: 0 8px 24px rgba(28,42,47,.18); padding: 16px;
      }
      h2 { font-size: 18px; margin: 0 0 8px; }
      p { margin: 0 0 10px; line-height: 1.5; font-size: 14px; }
      ul { margin: 0 0 12px; padding-left: 18px; }
      .actions { display: flex; flex-wrap: wrap; gap: 8px; }
      button {
        font: inherit; border-radius: 8px; padding: 8px 12px; cursor: pointer;
        border: 1px solid #0f4c5c; background: #0f4c5c; color: #fff;
      }
      button.secondary { background: transparent; color: #0f4c5c; }
      button.ghost { background: transparent; border-color: #d7d0c4; color: #1c2a2f; }
      .banner { background: #f7ead4; color: #5c3b0b; padding: 8px; border-radius: 8px; margin-bottom: 10px; font-size: 13px; }
      [hidden] { display: none !important; }
    </style>
    <div class="wrap" hidden>
      <div class="overlay" part="overlay"></div>
      <div class="drawer" role="dialog" aria-modal="true" aria-labelledby="zqax-title">
        <div class="banner">發現可能的個資，建議先移除。原始內容只在你的裝置上檢查，不會傳到竹青安心GO伺服器。</div>
        <h2 id="zqax-title">送出前先保護這段資料</h2>
        <p class="lede">系統能降低風險，但無法保證偵測所有敏感資訊。</p>
        <ul class="findings"></ul>
        <div class="confirm" hidden>
          <p>若仍要送出原文，請再次確認。我們只會記錄「了解風險後仍送出」，不會保存原文。</p>
        </div>
        <div class="actions">
          <button class="mask" type="button">安全遮蔽後送出</button>
          <button class="secondary edit" type="button">返回修改</button>
          <button class="ghost override" type="button">我了解風險，仍要送出</button>
        </div>
      </div>
    </div>
  `;
  document.documentElement.appendChild(host);

  const root = shadow.querySelector(".wrap");
  const list = shadow.querySelector(".findings");
  const confirmBox = shadow.querySelector(".confirm");
  const maskBtn = shadow.querySelector(".mask");
  const editBtn = shadow.querySelector(".edit");
  const overrideBtn = shadow.querySelector(".override");
  let pending = null;
  let overrideArmed = false;

  function hide() {
    root.hidden = true;
    confirmBox.hidden = true;
    overrideArmed = false;
    pending = null;
  }

  function show(findings, handlers) {
    pending = handlers;
    overrideArmed = false;
    confirmBox.hidden = true;
    list.innerHTML = "";
    findings.forEach((item) => {
      const li = document.createElement("li");
      li.innerHTML = `<strong>${item.label}</strong>：${item.reason}`;
      list.appendChild(li);
    });
    root.hidden = false;
    maskBtn.focus();
  }

  maskBtn.addEventListener("click", () => {
    if (pending) pending.onMask();
    hide();
  });
  editBtn.addEventListener("click", () => {
    if (pending) pending.onCancel();
    hide();
  });
  overrideBtn.addEventListener("click", () => {
    if (!overrideArmed) {
      overrideArmed = true;
      confirmBox.hidden = false;
      overrideBtn.textContent = "確認仍要送出原文";
      overrideBtn.focus();
      return;
    }
    if (pending) pending.onOverride();
    overrideBtn.textContent = "我了解風險，仍要送出";
    hide();
  });
  shadow.querySelector(".overlay").addEventListener("click", () => {
    if (pending) pending.onCancel();
    hide();
  });

  const api = { show, hide };
  host._api = api;
  return api;
}
