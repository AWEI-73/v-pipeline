import { ArtifactCard } from "../components/ArtifactCard.js";
import { VerticalRouteTimeline, expandedRouteStages, stageLabelsZh } from "../components/VerticalRouteTimeline.js";
import { escapeHtml } from "../components/StatusPill.js";

const valueLabels = {
  training_recap: "養成班 / 訓練回顧",
  children_story: "兒童故事",
  graduation_recap: "結訓 / 畢業回顧",
  existing_material_available: "已有素材",
  no_existing_visual_material: "沒有現成影像素材",
  brief_available: "已有簡報或文字簡述",
  story_outline_available: "已有故事大綱",
  brownfield_existing_material: "棕地：已有素材，先消除模糊",
  greenfield_story_first: "綠地：先定故事與素材需求",
  material_first: "素材優先",
  story_first: "故事優先",
  existing_material_first: "既有素材優先",
  story_first_generated_material: "故事優先，缺素材時生成",
  material_delta_then_collect_or_generate_if_needed: "先看素材缺口，再決定補拍、補素材或生成",
  generated_material_fallback: "缺素材時走生成素材 fallback",
  material_map_lifecycle: "素材地圖生命週期",
  story_blueprint_then_material_generation_fallback: "故事藍圖，再生成缺口素材",
};

function readable(value) {
  if (value === undefined || value === null || value === "") return "-";
  return valueLabels[value] || String(value).replaceAll("_", " ");
}

function stageDescription(stage, materialMap) {
  const stats = materialMap?.stats || {};
  const summary = materialMap?.delta_summary || {};
  const descriptions = {
    Intent: "先固定影片目的、觀眾、素材狀態、入口路線與下一站，讓後面流程不用猜。",
    "Material Ingest": "既有素材、生成素材或候選素材進入 run folder，準備被素材地圖辨識。",
    "Material Map": `${stats.assets ?? 0} 個素材、${stats.needs ?? 0} 個需求、${stats.accepted_edges ?? 0} 條已接受對應。`,
    "Coverage Delta": `已覆蓋 ${summary.covered ?? 0}、偏薄 ${summary.thin ?? 0}、缺口 ${summary.missing ?? 0}。`,
    Structure: "故事、教學、活動或特定路線的結構在這裡固定，再交給可建置的契約。",
    Contract: "段落契約把意圖與素材證據轉成可建置的時間與內容槽位。",
    Timeline: "時間軸組裝會產出可編輯的 build timeline，也是 Workbench preview 的基礎。",
    "Review Gates": "審核產物會決定要繼續、修正、生成、補拍，或交給 Workbench。",
    Verify: "交付前做最後的技術與內容檢查，留下驗證證據。",
  };
  return descriptions[stage?.label] || "目前沒有這個階段的細節。";
}

const stageFileManifest = {
  Intent: [
    { path: "video_intent.json", role: "標準意圖檔" },
    { path: "project_brief.json", role: "專案簡述" },
  ],
  "Material Ingest": [
    { path: "media/", role: "既有素材資料夾" },
    { path: "generated_real_imagegen/", role: "生成素材資料夾" },
    { path: "generated_material_review.json", role: "生成素材審核" },
  ],
  "Material Map": [
    { path: "project_material_map.json", role: "原始素材地圖" },
    { path: "reviewed_project_material_map.json", role: "已審核素材地圖" },
  ],
  "Coverage Delta": [
    { path: "material_delta.json", role: "覆蓋差異" },
    { path: "fresh_material_delta.json", role: "最新覆蓋差異" },
  ],
  Structure: [
    { path: "story_blueprint/", role: "故事或路線結構" },
    { path: "material_needs.json", role: "必要畫面需求" },
    { path: "assembly_plan.json", role: "組裝規劃" },
  ],
  Contract: [
    { path: "segment_contract.json", role: "建置契約" },
    { path: "revised_segment_contract.json", role: "修正版契約" },
  ],
  Timeline: [
    { path: "timeline_build.json", role: "時間軸建置來源" },
    { path: "timeline.json", role: "標準時間軸" },
    { path: "preview_timeline.json", role: "Workbench 預覽" },
  ],
  "Review Gates": [
    { path: "reviewer_aggregation.json", role: "多角色審核彙整" },
    { path: "review_report.json", role: "標準審核報告" },
    { path: "workbench_review_report.json", role: "Workbench 審核報告" },
  ],
  Verify: [
    { path: "verify_evidence_bundle.json", role: "驗證證據包" },
    { path: "delivery_gate.json", role: "交付決策" },
    { path: "verify_result.json", role: "驗證結果" },
    { path: "contact_sheet.jpg", role: "畫面證明表" },
  ],
};

function stageStatusByArtifact(materialMap) {
  const status = new Map();
  (materialMap?.stages || []).forEach((stage) => {
    if (stage.artifact) status.set(stage.artifact, stage.status || "present");
  });
  return status;
}

function renderStageFiles(selected, materialMap) {
  const statusByArtifact = stageStatusByArtifact(materialMap);
  const declared = stageFileManifest[selected?.label] || [];
  const currentArtifact = selected?.artifact && !declared.some((item) => item.path === selected.artifact)
    ? [{ path: selected.artifact, role: "目前主要產物" }]
    : [];
  const files = [...currentArtifact, ...declared];
  return `
    <div class="stage-file-list">
      ${files.map((file) => {
        const status = statusByArtifact.get(file.path) || (file.path === selected?.artifact ? selected?.status : "declared");
        return `
          <article class="stage-file-card">
            <span>${escapeHtml(file.role)}</span>
            <strong>${escapeHtml(file.path)}</strong>
            <small class="stage-file-status">${escapeHtml(status || "declared")}</small>
          </article>
        `;
      }).join("")}
    </div>
  `;
}

function metric(label, value) {
  return `
    <article class="intent-metric">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(readable(value))}</strong>
    </article>
  `;
}

function chipList(items, emptyText) {
  const values = Array.isArray(items) ? items : [];
  if (!values.length) return `<p class="intent-empty">${escapeHtml(emptyText)}</p>`;
  return `
    <div class="intent-chip-list">
      ${values.map((item) => `<span>${escapeHtml(readable(item))}</span>`).join("")}
    </div>
  `;
}

function renderIntentSummary(materialMap) {
  const intent = materialMap?.intent || {};
  return `
    <section class="intent-summary-panel">
      <div class="intent-hero">
        <p class="eyebrow">開案摘要</p>
        <h4>${escapeHtml(readable(intent.video_type))}</h4>
        <p>${escapeHtml(intent.goal || "尚未填寫影片目的。")}</p>
      </div>
      <div class="intent-metric-grid">
        ${metric("主要觀眾", intent.audience)}
        ${metric("素材狀態", intent.material_availability)}
        ${metric("文字輸入", intent.text_availability)}
        ${metric("入口路線", intent.entry_path)}
        ${metric("Pipeline 路線", intent.route)}
        ${metric("缺口策略", intent.gap_strategy)}
        ${metric("輸入情境", intent.input_state)}
        ${metric("下一站", intent.handoff_to)}
      </div>
      <div class="intent-review-grid">
        <article>
          <span>需要追問</span>
          ${chipList(intent.required_followup_questions, "目前資訊足夠，不需要追問。")}
        </article>
        <article>
          <span>判斷假設</span>
          ${chipList(intent.assumptions, "目前沒有記錄假設。")}
        </article>
        <article>
          <span>預期產物</span>
          ${chipList(intent.expected_outputs, "尚未設定預期產物。")}
        </article>
      </div>
    </section>
  `;
}

function renderStageInsight(selected, materialMap) {
  if (selected?.label === "Intent") return renderIntentSummary(materialMap);
  return "";
}

export function RouteOverviewView({ control, materialMap, activeStage }) {
  const stages = materialMap?.stages || [];
  const expanded = expandedRouteStages(stages);
  const selected = expanded.find((stage) => stage.label === activeStage) || expanded[0];
  const stats = materialMap?.stats || {};
  return `
    <section class="view-grid">
      ${VerticalRouteTimeline(stages, selected?.label)}
      <section class="view-main">
        <div class="section-head">
          <div>
            <p class="eyebrow">路線總覽</p>
            <h2>影片流程審核</h2>
            <p class="view-note">用重要節點檢查這個 run 的狀態、核心文件與下一步，不需要直接讀 JSON。</p>
          </div>
          <span class="mode-chip">${escapeHtml(readable(materialMap?.entry_path || "unknown"))}</span>
        </div>
        <div class="summary-grid">
          <article><span>素材</span><strong>${escapeHtml(stats.assets ?? "-")}</strong></article>
          <article><span>需求</span><strong>${escapeHtml(stats.needs ?? "-")}</strong></article>
          <article><span>已接受對應</span><strong>${escapeHtml(stats.accepted_edges ?? "-")}</strong></article>
          <article><span>建議動作</span><strong>${escapeHtml(readable(control?.recommended_next_action || "-"))}</strong></article>
        </div>
        <section class="stage-detail-panel" data-active-stage="${escapeHtml(selected?.label || "")}">
          <div>
            <p class="eyebrow">節點詳情</p>
            <h3>${escapeHtml(stageLabelsZh[selected?.label] || selected?.label || "階段")}</h3>
            <p>${escapeHtml(stageDescription(selected, materialMap))}</p>
            ${renderStageInsight(selected, materialMap)}
          </div>
          ${renderStageFiles(selected, materialMap)}
        </section>
        <div class="artifact-strip">
          ${stages.map((stage) => ArtifactCard(stage)).join("")}
        </div>
      </section>
    </section>
  `;
}
