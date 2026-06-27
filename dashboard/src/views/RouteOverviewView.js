import { ArtifactCard } from "../components/ArtifactCard.js";
import { VerticalRouteTimeline, expandedRouteStages } from "../components/VerticalRouteTimeline.js";
import { escapeHtml } from "../components/StatusPill.js";
import { stageLabelsZh, zhValue } from "../i18n/zh.js";

function readable(value) {
  return zhValue(value);
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

const boundaryStageLabels = {
  stage2_3_material_wall_to_review_apply: "Stage 2/3 素材牆到審核套用",
  stage4_build: "Stage 4 剪輯計畫邊界",
  stage5_final_review: "Stage 5 最終審核邊界",
};

function boundaryStageLabel(stage) {
  return boundaryStageLabels[stage] || String(stage || "-").replaceAll("_", " ");
}

function renderBoundaryAcceptance(artifacts) {
  const report = artifacts?.material_first_boundary_acceptance_report;
  if (!report) return "";

  const stages = Array.isArray(report.stages) ? report.stages : [];
  const statusText = report.ok ? "通過" : "需修復";
  const statusTone = report.ok ? "pass" : "fail";
  const nextAction = report.next_action || (report.ok ? "ready_for_render_or_human_review" : "repair_required");
  const failedStage = report.failed_stage ? boundaryStageLabel(report.failed_stage) : "無";

  return `
    <section class="boundary-acceptance-panel" data-report="material_first_boundary_acceptance_report">
      <div class="boundary-acceptance-head">
        <div>
          <p class="eyebrow">Material-first Acceptance</p>
          <h3>邊界驗收</h3>
          <p>用同一份 <code>material_first_boundary_acceptance_report.json</code> 顯示目前 route 是否已通過素材優先邊界。</p>
        </div>
        <span class="boundary-status ${statusTone}">${escapeHtml(statusText)}</span>
      </div>
      <div class="boundary-metrics">
        <article>
          <span>下一步</span>
          <strong>${escapeHtml(nextAction)}</strong>
        </article>
        <article>
          <span>失敗階段</span>
          <strong>${escapeHtml(failedStage)}</strong>
        </article>
        <article>
          <span>素材來源</span>
          <strong title="${escapeHtml(report.source_dir || "-")}">${escapeHtml(report.source_dir || "-")}</strong>
        </article>
      </div>
      <div class="boundary-stage-list">
        ${stages.map((stage) => {
          const blocking = Array.isArray(stage.blocking) ? stage.blocking : [];
          return `
            <article class="${stage.ok ? "pass" : "fail"}">
              <div>
                <strong>${escapeHtml(boundaryStageLabel(stage.stage))}</strong>
                <span>${escapeHtml(stage.report || "no report file")}</span>
              </div>
              <div class="boundary-stage-result">
                <span>${escapeHtml(stage.ok ? "通過" : "阻塞")}</span>
                ${blocking.length ? `<small>${escapeHtml(blocking.join(" / "))}</small>` : ""}
              </div>
            </article>
          `;
        }).join("")}
      </div>
    </section>
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

function artifactStatus(materialMap, artifact) {
  const found = (materialMap?.stages || []).find((stage) => stage.artifact === artifact);
  return found?.status || "declared";
}

function stageContract(selected, materialMap, control, artifacts) {
  const stats = materialMap?.stats || {};
  const delta = materialMap?.delta_summary || {};
  const boundary = artifacts?.material_first_boundary_acceptance_report;
  const route = [materialMap?.entry_path, materialMap?.route].filter(Boolean).join(" / ") || "尚未判定";
  const contracts = {
    Intent: {
      verdict: materialMap?.intent?.route ? "需求已收斂，可交給後續流程" : "尚未讀到完整 video_intent",
      params: `路線：${route}`,
      result: `影片類型：${readable(materialMap?.intent?.video_type || "unknown")}；觀眾：${readable(materialMap?.intent?.audience || "unknown")}`,
      gap: Array.isArray(materialMap?.intent?.required_followup_questions) && materialMap.intent.required_followup_questions.length
        ? materialMap.intent.required_followup_questions.join(" / ")
        : "目前沒有必要追問。",
      next: materialMap?.intent?.handoff_to || "進入素材或故事路線",
      stages: "Stage 0 / Video Intent Planner",
    },
    "Material Ingest": {
      verdict: stats.assets ? "已有素材進場，可建立素材地圖" : "尚未看到可用素材統計",
      params: `素材數：${stats.assets ?? 0}`,
      result: "素材會被整理成可審核的 asset / scene / need 關係。",
      gap: stats.assets ? "若素材分類錯誤，需在素材地圖審核時修正。" : "需要匯入素材或建立 generated candidates。",
      next: "進入素材地圖與覆蓋檢查",
      stages: "Stage 1 / Material Ingest",
    },
    "Material Map": {
      verdict: materialMap?.ready_for_build ? "素材覆蓋足夠，可往 build 前進" : "素材仍需審核或補缺口",
      params: `素材 ${stats.assets ?? 0} / 需求 ${stats.needs ?? 0} / 已接受對應 ${stats.accepted_edges ?? 0}`,
      result: "已用素材地圖保存素材、需求、採用與候選關係。",
      gap: stats.accepted_edges ? "仍需確認弱語意素材是否真的對題。" : "尚未有足夠 accepted edges，不能直接粗剪。",
      next: materialMap?.ready_for_build ? "送往結構 / 契約 / Workbench" : "先做 material map review apply",
      stages: "Stage 2-3 / Material Map Lifecycle",
    },
    "Coverage Delta": {
      verdict: (delta.missing || 0) > 0 ? "存在素材缺口" : "目前未看到明確缺口",
      params: `覆蓋 ${delta.covered ?? 0} / 偏薄 ${delta.thin ?? 0} / 缺口 ${delta.missing ?? 0}`,
      result: "素材缺口會決定補拍、生成、降級使用或暫停。",
      gap: (delta.missing || 0) > 0 ? "缺口需被標記為補拍 / 生成 / 接受不足。" : "仍需用實際畫面 review 確認不是假陽性。",
      next: "決定是否可進段落契約",
      stages: "Stage 3 / Coverage Delta",
    },
    Structure: {
      verdict: artifactStatus(materialMap, "assembly_plan.json") !== "missing" ? "已有結構規劃線索" : "結構規劃尚未完整落地",
      params: `路線：${route}`,
      result: "把影片拆成可對應素材與時間軸的段落。",
      gap: "若故事線與素材不一致，應先修 structure，不要硬剪。",
      next: "產出或修正 segment_contract.json",
      stages: "Stage 4 / Structure",
    },
    Contract: {
      verdict: artifactStatus(materialMap, "segment_contract.json") !== "missing" ? "段落契約已宣告或存在" : "尚未看到段落契約",
      params: "每段需包含目的、素材、字幕、音訊、特效意圖與時長。",
      result: "契約是後續 timeline / ffmpeg / effect factory 的主要依據。",
      gap: "若 contract 與素材供給不一致，必須回到 reviewer gate 修正。",
      next: "送往 timeline build",
      stages: "Stage 5 / Segment Contract",
    },
    Timeline: {
      verdict: artifactStatus(materialMap, "timeline.json") !== "missing" ? "已有時間軸或預覽時間軸" : "尚未看到可預覽時間軸",
      params: "影片 / 字幕 / 音訊 / 特效四層需要可追蹤。",
      result: "時間軸會提供 Workbench 播放與草稿修改依據。",
      gap: "這裡只看狀態，不直接修改 Workbench 的播放與四軌核心。",
      next: "進入 Workbench 或審核關卡",
      stages: "Stage 6-8 / Timeline Build",
    },
    "Review Gates": {
      verdict: boundary ? (boundary.ok ? "邊界驗收通過" : "邊界驗收仍有阻擋") : "尚未看到邊界驗收報告",
      params: boundary ? `next_action：${boundary.next_action || "-"}` : "material_first_boundary_acceptance_report.json",
      result: boundary ? `failed_stage：${boundary.failed_stage || "無"}` : "沒有報告時，不能宣稱已完成素材優先驗收。",
      gap: boundary?.ok ? "仍需人工看粗剪語意與畫面品質。" : "先補齊 blocking gate，不要直接 render。",
      next: boundary?.ok ? "可進 human review / Workbench" : "修正失敗 stage",
      stages: "Stage 9-11 / Review Gates",
    },
    Verify: {
      verdict: artifacts?.verify_result ? "已有驗證結果" : "尚未看到最終驗證結果",
      params: "delivery_gate / verify_result / evidence bundle",
      result: "驗證要證明字幕、畫面、音訊、素材對題與交付狀態。",
      gap: "沒有 verify evidence 時，不應只憑 final.mp4 宣稱完成。",
      next: "通過後才進最終交付",
      stages: "Stage 12-13 / Verify",
    },
  };
  return contracts[selected?.label] || {
    verdict: "尚未建立這個節點的契約紙",
    params: "-",
    result: "-",
    gap: "-",
    next: "-",
    stages: selected?.label || "-",
  };
}

function contractRow(label, value) {
  return `
    <div>${escapeHtml(label)}</div>
    <div>${escapeHtml(value)}</div>
  `;
}

function renderStageContractPaper(selected, materialMap, control, artifacts) {
  const contract = stageContract(selected, materialMap, control, artifacts);
  return `
    <section class="dashboard-contract-paper" data-active-stage="${escapeHtml(selected?.label || "")}">
      <div>
        <p class="eyebrow">中文契約紙</p>
        <h3>${escapeHtml(stageLabelsZh[selected?.label] || selected?.label || "階段")}</h3>
        <p>${escapeHtml(stageDescription(selected, materialMap))}</p>
      </div>
      <div class="dashboard-contract-grid">
        ${contractRow("目前判斷", contract.verdict)}
        ${contractRow("主要參數", contract.params)}
        ${contractRow("實際結果", contract.result)}
        ${contractRow("問題缺口", contract.gap)}
        ${contractRow("下一步", contract.next)}
        ${contractRow("對應管線", contract.stages)}
      </div>
      ${renderStageInsight(selected, materialMap)}
    </section>
  `;
}

export function RouteOverviewView({ control, materialMap, artifacts, activeStage }) {
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
        ${renderBoundaryAcceptance(artifacts)}
        <section class="stage-detail-panel" data-active-stage="${escapeHtml(selected?.label || "")}">
          ${renderStageContractPaper(selected, materialMap, control, artifacts)}
          ${renderStageFiles(selected, materialMap)}
        </section>
        <div class="artifact-strip">
          ${stages.map((stage) => ArtifactCard(stage)).join("")}
        </div>
      </section>
    </section>
  `;
}
