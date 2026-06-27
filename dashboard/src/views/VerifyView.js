import { escapeHtml } from "../components/StatusPill.js";

function asList(value) {
  return Array.isArray(value) ? value : [];
}

function statusText(ok, fallback = "未提供") {
  if (ok === true) return "通過";
  if (ok === false) return "阻擋";
  return fallback;
}

function renderIssue(issue, index) {
  return `
    <article class="verify-issue-card ${escapeHtml(issue.severity || "unknown")}">
      <span>#${index + 1} ${escapeHtml(issue.type || "issue")}</span>
      <strong>${escapeHtml(issue.severity || "unknown")}</strong>
      <p>${escapeHtml(issue.message || "沒有問題描述。")}</p>
    </article>
  `;
}

function renderAuditCard(title, audit, emptyText) {
  const hasAudit = Boolean(audit);
  const pass = audit?.pass ?? audit?.ok ?? audit?.passed;
  const blocking = asList(audit?.blocking || audit?.errors || audit?.issues).slice(0, 4);
  return `
    <article class="verify-audit-card ${pass === false ? "fail" : pass === true ? "pass" : "empty"}">
      <div>
        <span>${escapeHtml(title)}</span>
        <strong>${escapeHtml(hasAudit ? statusText(pass, "已有資料") : "未載入")}</strong>
      </div>
      <p>${escapeHtml(hasAudit ? (audit.reason || audit.summary || audit.status || emptyText) : emptyText)}</p>
      ${blocking.length ? `<ul>${blocking.map((item) => `<li>${escapeHtml(String(item))}</li>`).join("")}</ul>` : ""}
    </article>
  `;
}

function renderDeliveryGate(artifacts) {
  const gate = artifacts?.delivery_gate;
  const verify = artifacts?.verify_result;
  const blocking = asList(gate?.blocking || verify?.blocking || verify?.errors);
  const pass = gate?.pass ?? verify?.pass ?? verify?.ok;
  return `
    <section class="verify-contract-paper">
      <div>
        <p class="eyebrow">交付判斷</p>
        <h2>${escapeHtml(statusText(pass, "尚未驗證"))}</h2>
        <p>這裡只顯示會影響是否能交付的判斷。沒有 delivery gate 或 verify result 時，不應只憑 final.mp4 宣稱完成。</p>
      </div>
      <div class="verify-kv">
        <span>成品影片</span><strong>${escapeHtml(artifacts?.final_video_url ? "已找到" : "未找到")}</strong>
        <span>Contact Sheet</span><strong>${escapeHtml(artifacts?.contact_sheet_url ? "已找到" : "未找到")}</strong>
        <span>驗證證據包</span><strong>${escapeHtml(artifacts?.verify_evidence_bundle ? "已載入" : "未載入")}</strong>
        <span>阻擋原因</span><strong>${escapeHtml(blocking.length ? blocking.join(" / ") : "目前沒有列出阻擋原因")}</strong>
      </div>
    </section>
  `;
}

export function VerifyView({ artifacts }) {
  const issues = asList(artifacts?.issues);
  const artifactErrors = asList(artifacts?.artifact_errors);
  const totalIssues = issues.length + artifactErrors.length;
  return `
    <section class="view-main full">
      <div class="section-head">
        <div>
          <p class="eyebrow">驗證</p>
          <h2>交付前檢查</h2>
          <p class="view-note">把 verify / delivery gate / audit 報告整理成人能判斷的阻擋點，不直接顯示原始 JSON。</p>
        </div>
        <span class="mode-chip">${escapeHtml(totalIssues)} 個問題</span>
      </div>
      ${renderDeliveryGate(artifacts)}
      <section class="verify-audit-grid">
        ${renderAuditCard("黑畫面 / 空畫面", artifacts?.black_frame_audit, "尚未載入黑畫面檢查。")}
        ${renderAuditCard("B-roll / 素材對題", artifacts?.broll_audit, "尚未載入素材對題檢查。")}
        ${renderAuditCard("字幕可讀性", artifacts?.caption_audit, "尚未載入字幕檢查。")}
        ${renderAuditCard("語意對齊", artifacts?.semantic_alignment, "尚未載入語意對齊檢查。")}
      </section>
      <section class="verify-issue-list">
        <div class="section-head compact">
          <div>
            <p class="eyebrow">阻擋與警訊</p>
            <h3>需要人工處理的項目</h3>
          </div>
        </div>
        ${issues.length || artifactErrors.length
          ? [...issues, ...artifactErrors.map((message) => ({ type: "artifact_error", severity: "error", message }))].map(renderIssue).join("")
          : "<div class='empty-state'>目前沒有載入驗證問題。若此 run 應該已有成片，請確認 verify_result.json / delivery_gate.json 是否存在。</div>"}
      </section>
    </section>
  `;
}
