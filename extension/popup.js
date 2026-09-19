chrome.runtime.sendMessage({ type: "GET_STATUS" }, (response) => {
  const node = document.getElementById("status");
  if (response && response.ok) {
    node.textContent = "擴充功能已啟用，版本 " + response.version + "。";
  } else {
    node.textContent = "擴充功能已載入。請到 localhost:8000/demo-chat 操作。";
  }
});
