export function getText(el) {
  if (!el) return "";
  if (el.isContentEditable) return el.innerText || "";
  return el.value || "";
}

export function setNativeValue(el, value) {
  const proto = el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, "value").set;
  setter.call(el, value);
  el.dispatchEvent(new Event("input", { bubbles: true }));
}

export function setText(el, value) {
  if (!el) return;
  if (el.isContentEditable) {
    el.innerText = value;
  } else {
    setNativeValue(el, value);
  }
}
