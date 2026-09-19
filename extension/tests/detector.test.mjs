import { detect, isValidTaiwanId, luhnValid } from "../src/detector/engine.js";
import { containsOriginals, maskText } from "../src/masker/masker.js";
import assert from "node:assert/strict";
import test from "node:test";

test("taiwan id valid A123456789", () => {
  assert.equal(isValidTaiwanId("A123456789"), true);
});

test("taiwan id invalid checksum", () => {
  assert.equal(isValidTaiwanId("A123456780"), false);
});

test("taiwan id invalid format", () => {
  assert.equal(isValidTaiwanId("A323456789"), false);
  assert.equal(isValidTaiwanId("1234567890"), false);
  assert.equal(isValidTaiwanId("A12345678"), false);
});

test("detects valid taiwan id only", () => {
  const hit = detect("合成檢核範例 A123456789");
  const miss = detect("合成檢核範例 A123456780");
  assert.equal(hit.some((item) => item.category === "tw_id"), true);
  assert.equal(miss.some((item) => item.category === "tw_id"), false);
});

test("luhn public test card", () => {
  assert.equal(luhnValid("4111111111111111"), true);
  assert.equal(luhnValid("5555555555554444"), true);
  assert.equal(luhnValid("4111111111111112"), false);
});

test("credit card with dashes and spaces", () => {
  const dashed = detect("卡號 4111-1111-1111-1111");
  const spaced = detect("卡號 4111 1111 1111 1111");
  assert.equal(dashed.some((item) => item.category === "credit_card"), true);
  assert.equal(spaced.some((item) => item.category === "credit_card"), true);
});

test("phone email address and custom term", () => {
  const text = "demo@example.test 打 0912-000-111 到新竹市示意區不存在路 1 號，並提到未公開專案代號";
  const findings = detect(text);
  const categories = new Set(findings.map((item) => item.category));
  assert.equal(categories.has("email"), true);
  assert.equal(categories.has("phone"), true);
  assert.equal(categories.has("address"), true);
  assert.equal(categories.has("custom_sensitive_term"), true);
});

test("does not treat short numbers as phone", () => {
  const findings = detect("會議在 0912 開始，分機 123");
  assert.equal(findings.some((item) => item.category === "phone"), false);
});

test("masker removes original values", () => {
  const text = "A123456789 4111111111111111 0912000111 demo@example.test 新竹市示意路1號 未公開專案代號";
  const findings = detect(text);
  const masked = maskText(text, findings);
  assert.equal(containsOriginals(masked, findings), false);
  assert.equal(masked.includes("A123456789"), false);
  assert.equal(masked.includes("4111111111111111"), false);
  assert.equal(masked.includes("[身分證字號已移除]"), true);
});
