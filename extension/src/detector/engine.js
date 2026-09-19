export const CATEGORY_LABELS = {
  tw_id: "台灣身分證字號",
  credit_card: "信用卡號",
  phone: "手機號碼",
  email: "電子郵件",
  address: "地址",
  custom_sensitive_term: "敏感詞",
};

export const CATEGORY_REASONS = {
  tw_id: "符合身分證格式且通過檢核碼，可能被用來冒用身分。",
  credit_card: "通過 Luhn 檢核的卡號，可能被第三方保存或濫用。",
  phone: "台灣手機號碼可直接聯繫本人，不應交給外部 AI。",
  email: "電子郵件可識別與聯絡個人。",
  address: "地址或可定位特徵可能揭露居住或工作地點。",
  custom_sensitive_term: "命中示範敏感詞，可能涉及未公開資訊。",
};

export const REPLACEMENTS = {
  tw_id: "[身分證字號已移除]",
  credit_card: "[信用卡號已移除]",
  phone: "[手機號碼已移除]",
  email: "[電子郵件已移除]",
  address: "[地址已移除]",
  custom_sensitive_term: "[敏感詞已移除]",
};

export const DEFAULT_TERMS = ["未公開專案代號", "客戶名單", "薪資明細"];

const TAIWAN_ID_MAP = {
  A: 10, B: 11, C: 12, D: 13, E: 14, F: 15, G: 16, H: 17, I: 34, J: 18,
  K: 19, L: 20, M: 21, N: 22, O: 35, P: 23, Q: 24, R: 25, S: 26, T: 27,
  U: 28, V: 29, W: 32, X: 30, Y: 31, Z: 33,
};

export function isValidTaiwanId(value) {
  if (!/^[A-Za-z][12]\d{8}$/.test(value)) return false;
  const upper = value.toUpperCase();
  const mapped = TAIWAN_ID_MAP[upper[0]];
  if (!mapped) return false;
  const n1 = Math.floor(mapped / 10);
  const n2 = mapped % 10;
  const digits = upper.slice(1).split("").map(Number);
  const weights = [8, 7, 6, 5, 4, 3, 2, 1, 1];
  let sum = n1 + n2 * 9;
  for (let i = 0; i < 9; i += 1) sum += digits[i] * weights[i];
  return sum % 10 === 0;
}

export function luhnValid(digits) {
  if (!/^\d{13,19}$/.test(digits)) return false;
  let sum = 0;
  let alternate = false;
  for (let i = digits.length - 1; i >= 0; i -= 1) {
    let n = digits.charCodeAt(i) - 48;
    if (alternate) {
      n *= 2;
      if (n > 9) n -= 9;
    }
    sum += n;
    alternate = !alternate;
  }
  return sum % 10 === 0;
}

function pushFinding(findings, category, start, end, value) {
  findings.push({
    category,
    start,
    end,
    value,
    label: CATEGORY_LABELS[category],
    reason: CATEGORY_REASONS[category],
  });
}

function overlaps(findings, start, end) {
  return findings.some((item) => !(end <= item.start || start >= item.end));
}

export function detect(text, extraTerms = DEFAULT_TERMS) {
  const findings = [];
  if (!text) return findings;

  const idRe = /[A-Za-z][12]\d{8}/g;
  let match;
  while ((match = idRe.exec(text)) !== null) {
    if (isValidTaiwanId(match[0])) {
      pushFinding(findings, "tw_id", match.index, match.index + match[0].length, match[0]);
    }
  }

  const cardRe = /\b(?:\d[ \-]*?){13,19}\b/g;
  while ((match = cardRe.exec(text)) !== null) {
    const digits = match[0].replace(/[^\d]/g, "");
    if (luhnValid(digits) && !overlaps(findings, match.index, match.index + match[0].length)) {
      pushFinding(findings, "credit_card", match.index, match.index + match[0].length, match[0]);
    }
  }

  const emailRe = /\b[\w.+-]+@[\w-]+\.[\w.-]+\b/g;
  while ((match = emailRe.exec(text)) !== null) {
    pushFinding(findings, "email", match.index, match.index + match[0].length, match[0]);
  }

  const phoneRe = /\b09\d{2}[- ]?\d{3}[- ]?\d{3}\b/g;
  while ((match = phoneRe.exec(text)) !== null) {
    if (!overlaps(findings, match.index, match.index + match[0].length)) {
      pushFinding(findings, "phone", match.index, match.index + match[0].length, match[0]);
    }
  }

  const addressRe = /(?:台北|臺北|新北|桃園|台中|臺中|台南|臺南|高雄|新竹|苗栗|彰化|南投|雲林|嘉義|屏東|宜蘭|花蓮|台東|臺東|基隆|澎湖|金門|連江)[市縣][^\n]{0,20}(?:路|街|大道|巷)[^\n]{0,12}號/g;
  while ((match = addressRe.exec(text)) !== null) {
    pushFinding(findings, "address", match.index, match.index + match[0].length, match[0]);
  }

  extraTerms.forEach((term) => {
    if (!term) return;
    let from = 0;
    while (from < text.length) {
      const index = text.indexOf(term, from);
      if (index === -1) break;
      pushFinding(findings, "custom_sensitive_term", index, index + term.length, term);
      from = index + term.length;
    }
  });

  return findings.sort((a, b) => a.start - b.start);
}
