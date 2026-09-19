import { REPLACEMENTS } from "../detector/engine.js";

export function maskText(text, findings) {
  const sorted = [...findings].sort((a, b) => b.start - a.start);
  let result = text;
  for (const finding of sorted) {
    const replacement = REPLACEMENTS[finding.category] || "[敏感資料已移除]";
    result = result.slice(0, finding.start) + replacement + result.slice(finding.end);
  }
  return result;
}

export function containsOriginals(masked, findings) {
  return findings.some((finding) => finding.value && masked.includes(finding.value));
}
