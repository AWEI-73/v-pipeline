import { escapeHtml } from "../components/StatusPill.js";

function renderReviewSummary(artifacts) {
  const summary = artifacts?.workbench?.draft_summary || {};
  const present = summary.present_count ?? 0;
  const handoff = summary.has_handoff ? "交接包已存在" : "交接包缺少";
  const review = summary.has_review_report ? "審核報告已存在" : "審核報告缺少";
  const agent = summary.agent_ready ? "可交給 Agent" : "尚不可交給 Agent";
  const validation = summary.handoff_validation || {};
  return `
    <section class="workbench-review-summary">
      <div>
        <p class="eyebrow">草稿包</p>
        <h3>${escapeHtml(present)} 個草稿檔</h3>
        <p class="view-note">${escapeHtml(handoff)} / ${escapeHtml(review)} / ${escapeHtml(agent)}</p>
      </div>
      <div class="workbench-layer-chips">
        <span>timeline ${escapeHtml(summary.timeline_edits ?? 0)}</span>
        <span>字幕 ${escapeHtml(summary.subtitle_edits ?? 0)}</span>
        <span>音訊 ${escapeHtml(summary.audio_cues ?? 0)}</span>
        <span>效果 ${escapeHtml(summary.effect_intents ?? 0)}</span>
        <span>驗證 ${escapeHtml(validation.ok === true ? "通過" : validation.ok === false ? "失敗" : "未建立")}</span>
      </div>
    </section>
  `;
}

export function WorkbenchView({ workbenchHealth, root, artifacts }) {
  const query = root ? `?root=${encodeURIComponent(root)}` : "";
  const status = workbenchHealth?.status || "載入中";
  const canPreview = workbenchHealth?.can_preview ? "可預覽" : "尚無預覽時間軸";
  const rootText = workbenchHealth?.artifact_root || root || "載入中";
  return `
    <section class="view-main full">
      <div class="section-head">
        <div>
          <p class="eyebrow">互動草稿工作區</p>
          <h2>剪輯工作區</h2>
          <p class="view-note">健康狀態：<code>/api/workbench/health</code></p>
        </div>
        <span class="mode-chip">${escapeHtml(status)} / ${escapeHtml(canPreview)}</span>
      </div>
      <div class="workbench-status-grid">
        <article>
          <span>執行環境</span>
          <strong>已合併的 Dashboard server</strong>
        </article>
        <article>
          <span>產物根目錄</span>
          <strong class="mono">${escapeHtml(rootText)}</strong>
        </article>
        <article>
          <span>寫入規則</span>
          <strong>只寫入草稿</strong>
        </article>
      </div>
      ${renderReviewSummary(artifacts)}
      <div class="workbench-shell">
        <iframe title="Hermes 剪輯工作區" loading="eager" onload="this.dataset.loaded='true'" src="/workbench/index.html${query}"></iframe>
      </div>
    </section>
  `;
}
