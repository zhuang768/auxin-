(function () {
  var input = document.getElementById("demo-chat-input");
  var send = document.getElementById("demo-chat-send");
  var messages = document.getElementById("demo-chat-messages");
  var fill = document.getElementById("fill-demo-text");
  var clear = document.getElementById("clear-chat");

  var DEMO_TEXT = [
    "以下為合成測試資料，非正式證件或帳號。",
    "請幫我潤飾這段自我介紹：我是林小竹，聯絡信箱 demo@example.test，手機 0912-000-111。",
    "住址：新竹市示意區不存在路 1 號（虛構地址，僅供偵測示範）。",
    "測試信用卡（支付業公開測試號）：4111-1111-1111-1111。",
    "測試身分證檢核範例：A123456789。",
    "另外請不要提到未公開專案代號。",
  ].join("\n");

  function appendMessage(text, label) {
    var div = document.createElement("div");
    div.className = "chat-msg";
    div.textContent = (label || "已送出") + "\n" + text;
    messages.prepend(div);
  }

  function sendCurrent() {
    var text = input.value;
    if (!text.trim()) return;
    appendMessage(text, "示範回覆（非真實 AI）");
    input.value = "";
    input.dispatchEvent(new Event("input", { bubbles: true }));
  }

  send.addEventListener("click", function () {
    sendCurrent();
  });
  input.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendCurrent();
    }
  });
  window.addEventListener("zqax:approved-send", function () {
    sendCurrent();
  });
  fill.addEventListener("click", function () {
    input.value = DEMO_TEXT;
    input.focus();
  });
  clear.addEventListener("click", function () {
    messages.innerHTML = "";
    input.value = "";
  });
})();
