import { escapeHtml } from "../components/StatusPill.js";

function asList(value) {
  return Array.isArray(value) ? value : [];
}

function numberOr(value, fallback = 0) {
  const next = Number(value);
  return Number.isFinite(next) ? next : fallback;
}

function fmtSec(value) {
  const sec = numberOr(value, 0);
  return `${sec.toFixed(sec >= 10 ? 1 : 2)}s`;
}

function slotTitle(slot, index) {
  return slot.title || slot.label || slot.segment_title || slot.segment_id || slot.segment || `片段 ${index + 1}`;
}

function slotStatus(slot) {
  return slot.status || (slot.window_quality_fallback ? "fallback" : "matched");
}

function subtitleForSlot(slot, subtitles) {
  const start = numberOr(slot.start_sec, 0);
  const end = numberOr(slot.end_sec, start + numberOr(slot.duration_sec, 0));
  return subtitles.find((sub) => numberOr(sub.start_sec, -1) < end && numberOr(sub.end_sec, -1) > start);
}

function renderSlot(slot, index, totalDuration, subtitles) {
  const start = numberOr(slot.start_sec, 0);
  const duration = numberOr(slot.duration_sec, Math.max(0, numberOr(slot.end_sec, start) - start));
  const width = totalDuration > 0 ? Math.max(7, (duration / totalDuration) * 100) : 100;
  const status = slotStatus(slot);
  const subtitle = subtitleForSlot(slot, subtitles);
  return `
    <article class="timeline-slot-card ${escapeHtml(status)}">
      <div class="timeline-slot-bar" style="width:${width.toFixed(3)}%"></div>
      <div class="timeline-slot-main">
        <span>${escapeHtml(fmtSec(start))} - ${escapeHtml(fmtSec(start + duration))}</span>
        <strong>${escapeHtml(slotTitle(slot, index))}</strong>
        <p>${escapeHtml(slot.need_id || slot.material_need || slot.asset_id || slot.source || "尚未標記素材來源")}</p>
      </div>
      <div class="timeline-slot-side">
        <b>${escapeHtml(status)}</b>
        <small>${escapeHtml(subtitle?.text || "無字幕")}</small>
      </div>
    </article>
  `;
}

function renderSubtitleList(subtitles) {
  if (!subtitles.length) {
    return `<div class="empty-state">目前沒有讀到字幕檔。若影片應有字幕，請確認 review_subtitles.srt / subtitles.srt 是否存在。</div>`;
  }
  return subtitles.slice(0, 10).map((sub) => `
    <article class="timeline-subtitle-card">
      <span>${escapeHtml(fmtSec(sub.start_sec))} - ${escapeHtml(fmtSec(sub.end_sec))}</span>
      <p>${escapeHtml(sub.text || "")}</p>
    </article>
  `).join("");
}

export function TimelineView({ artifacts }) {
  const slots = asList(artifacts?.timeline_slots);
  const subtitles = asList(artifacts?.subtitles);
  const totalDuration = Math.max(
    0,
    ...slots.map((slot) => numberOr(slot.end_sec, numberOr(slot.start_sec, 0) + numberOr(slot.duration_sec, 0)))
  );
  const issueSlots = slots.filter((slot) => ["drift", "wrong_need", "gap", "render_failed"].includes(slotStatus(slot)));
  return `
    <section class="view-main full">
      <div class="section-head">
        <div>
          <p class="eyebrow">時間軸</p>
          <h2>白盒時間軸檢視</h2>
          <p class="view-note">這裡只檢查 timeline 與字幕是否合理；真正拖曳、trim、播放仍回到 Workbench 原生工作檯。</p>
        </div>
        <span class="mode-chip">${escapeHtml(slots.length)} 個片段 / ${escapeHtml(fmtSec(totalDuration))}</span>
      </div>
      <section class="timeline-contract-panel">
        <article>
          <span>時間軸來源</span>
          <strong>${escapeHtml(artifacts?.raw_paths?.timeline || "未找到 timeline.json / timeline_build.json")}</strong>
        </article>
        <article>
          <span>成品影片</span>
          <strong>${escapeHtml(artifacts?.final_video_url ? "已找到，可預覽" : "未找到 final.mp4")}</strong>
        </article>
        <article>
          <span>字幕數</span>
          <strong>${escapeHtml(subtitles.length)}</strong>
        </article>
        <article>
          <span>需注意片段</span>
          <strong>${escapeHtml(issueSlots.length)}</strong>
        </article>
      </section>
      <section class="timeline-whitebox-grid">
        <div class="timeline-slot-list">
          <div class="section-head compact">
            <div>
              <p class="eyebrow">片段順序</p>
              <h3>Timeline slots</h3>
            </div>
          </div>
          ${slots.length ? slots.map((slot, index) => renderSlot(slot, index, totalDuration, subtitles)).join("") : "<div class='empty-state'>目前沒有 timeline slots。若已完成粗剪，請確認 timeline.json / timeline_build.json 是否存在。</div>"}
        </div>
        <aside class="timeline-subtitle-list">
          <div class="section-head compact">
            <div>
              <p class="eyebrow">字幕</p>
              <h3>Subtitle cues</h3>
            </div>
          </div>
          ${renderSubtitleList(subtitles)}
        </aside>
      </section>
    </section>
  `;
}
