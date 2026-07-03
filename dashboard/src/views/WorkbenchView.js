import { escapeHtml } from "../components/StatusPill.js";
import { workbenchLabelsZh } from "../i18n/zh.js";

function renderSummaryChips(summary = {}) {
  const validation = summary.handoff_validation || {};
  const validationText = validation.ok === true ? "通過" : validation.ok === false ? "未通過" : "待檢查";
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
    <section class="view-main full workbench-view workbench-retired-shell">
      <div class="workbench-studio-head">
        <div>
          <p class="eyebrow">Workbench 入口</p>
          <h2>影片剪輯工作台</h2>
          <p class="view-note">原生 Workbench 已是主頁面；Dashboard 只保留白盒檢視，不再以 iframe 包住剪輯器。</p>
        </div>
        <div class="workbench-head-actions">
          <span class="mode-chip">${escapeHtml(status)} / ${escapeHtml(canPreview)}</span>
          <a class="mode-chip primary" href="/workbench${query}">開啟原生 Workbench</a>
        </div>
      </div>

      <div class="workbench-run-strip">
        <span>Run folder</span>
        <strong class="mono" title="${escapeHtml(rootText)}">${escapeHtml(rootText)}</strong>
        ${renderSummaryChips(summary)}
      </div>

      <div class="workbench-native-handoff">
        <div>
          <p class="eyebrow">單文件架構</p>
          <h3>剪輯器不在 Dashboard SPA 內重新掛載</h3>
          <p>請在原生 Workbench 中操作影片、字幕、音訊與特效時間軸。Route、素材地圖、Artifacts、Verify 等白盒資訊會在原生頁面的滑出面板中開啟，切換面板不會重置播放位置、片段選取或抽屜狀態。</p>
        </div>
        <a class="primary-link" href="/workbench${query}">前往剪輯工作台</a>
      </div>
    </section>
  `;
}
