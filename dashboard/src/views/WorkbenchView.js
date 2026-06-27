import { escapeHtml } from "../components/StatusPill.js";
import { workbenchLabelsZh } from "../i18n/zh.js";

function renderSummaryChips(summary = {}) {
  const validation = summary.handoff_validation || {};
  const validationText = validation.ok === true ? "通過" : validation.ok === false ? "未通過" : "未檢查";
  return `
    <div class="workbench-layer-chips" aria-label="Workbench 草稿摘要">
      <span>草稿 ${escapeHtml(summary.present_count ?? 0)}</span>
      <span>${escapeHtml(workbenchLabelsZh.timelineDraft)} ${escapeHtml(summary.timeline_edits ?? 0)}</span>
      <span>${escapeHtml(workbenchLabelsZh.subtitleDraft)} ${escapeHtml(summary.subtitle_edits ?? 0)}</span>
      <span>${escapeHtml(workbenchLabelsZh.audioCueDraft)} ${escapeHtml(summary.audio_cues ?? 0)}</span>
      <span>${escapeHtml(workbenchLabelsZh.effectDraft)} ${escapeHtml(summary.effect_intents ?? 0)}</span>
      <span>交接驗證 ${escapeHtml(validationText)}</span>
    </div>
  `;
}

export function WorkbenchView({ workbenchHealth, root, artifacts }) {
  const query = root ? `?root=${encodeURIComponent(root)}` : "";
  const summary = artifacts?.workbench?.draft_summary || {};
  const status = workbenchHealth?.status || "未連線";
  const canPreview = workbenchHealth?.can_preview ? "可預覽" : "尚不可預覽";
  const rootText = workbenchHealth?.artifact_root || root || "尚未選擇 run folder";

  return `
    <section class="view-main full workbench-view">
      <div class="workbench-studio-head">
        <div>
          <p class="eyebrow">Workbench 黑盒</p>
          <h2>影片剪輯工作台</h2>
          <p class="view-note">保留舊版 Workbench 的互動畫面、播放控制與四條時間軸；外層只做 run 狀態與草稿摘要。</p>
        </div>
        <div class="workbench-head-actions">
          <span class="mode-chip">${escapeHtml(status)} / ${escapeHtml(canPreview)}</span>
          <span class="mode-chip soft">素材優先模式</span>
        </div>
      </div>

      <div class="workbench-run-strip">
        <span>Run folder</span>
        <strong class="mono" title="${escapeHtml(rootText)}">${escapeHtml(rootText)}</strong>
        ${renderSummaryChips(summary)}
      </div>

      <div class="workbench-shell">
        <iframe title="Hermes Workbench 黑盒剪輯工作檯" loading="eager" onload="this.dataset.loaded='true'" src="/workbench/index.html${query}"></iframe>
      </div>
    </section>
  `;
}
