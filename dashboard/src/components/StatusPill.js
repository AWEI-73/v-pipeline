export function statusPill(label, tone = "neutral") {
  return `<span class="status-pill ${tone}">${escapeHtml(label)}</span>`;
}

export function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}
