import { getText, setText } from "./dom.js";

export const demoChatAdapter = {
  id: "demo-chat",
  match(location) {
    return /localhost|127\.0\.0\.1/.test(location.hostname) && location.pathname.includes("demo-chat");
  },
  getInput() {
    return document.getElementById("demo-chat-input");
  },
  getSendButton() {
    return document.getElementById("demo-chat-send");
  },
  getText,
  setText,
  approveSend() {
    window.dispatchEvent(new CustomEvent("zqax:approved-send"));
  },
};

export const chatgptAdapter = {
  id: "chatgpt",
  match(location) {
    return /chatgpt\.com|chat\.openai\.com/.test(location.hostname);
  },
  getInput() {
    return document.querySelector("#prompt-textarea, textarea[data-id], div[contenteditable='true']#prompt-textarea");
  },
  getSendButton() {
    return document.querySelector("button[data-testid='send-button'], button[aria-label='Send prompt']");
  },
  getText,
  setText,
  approveSend() {
    const button = this.getSendButton();
    if (button) button.click();
  },
};

export const claudeAdapter = {
  id: "claude",
  match(location) {
    return location.hostname.includes("claude.ai");
  },
  getInput() {
    return document.querySelector("div[contenteditable='true'], textarea");
  },
  getSendButton() {
    return document.querySelector("button[aria-label='Send message'], button[aria-label='Send Message']");
  },
  getText,
  setText,
  approveSend() {
    const button = this.getSendButton();
    if (button) button.click();
  },
};

export const geminiAdapter = {
  id: "gemini",
  match(location) {
    return location.hostname.includes("gemini.google.com");
  },
  getInput() {
    return document.querySelector("rich-textarea, div[contenteditable='true'], textarea");
  },
  getSendButton() {
    return document.querySelector("button[aria-label='Send message'], button[aria-label='送出']");
  },
  getText,
  setText,
  approveSend() {
    const button = this.getSendButton();
    if (button) button.click();
  },
};

export const genericAdapter = {
  id: "generic",
  match() {
    return true;
  },
  getInput() {
    return document.querySelector("textarea, [contenteditable='true']");
  },
  getSendButton() {
    return document.querySelector("button, [role='button']");
  },
  getText,
  setText,
  approveSend() {},
};

const ADAPTERS = [demoChatAdapter, chatgptAdapter, claudeAdapter, geminiAdapter, genericAdapter];

export function resolveAdapter(location) {
  return ADAPTERS.find((adapter) => adapter.match(location)) || genericAdapter;
}
