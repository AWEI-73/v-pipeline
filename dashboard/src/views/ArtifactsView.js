import { escapeHtml } from "../components/StatusPill.js";

function existsLabel(value) {
  return value ? "已存在" : "未找到";
}

function artifactCard({ title, filename, status, description, path }) {
  const tone = status === "已存在" || status === "已載入" || status === "可用" ? "present" : "missing";
  return `
    <article class="artifact-decision-card ${tone}">
      <div>
        <span>${escapeHtml(status)}</span>
        <h3>${escapeHtml(title)}</h3>
        <p>${escapeHtml(description)}</p>
      </div>
      <strong>${escapeHtml(filename)}</strong>
      ${path ? `<small title="${escapeHtml(path)}">${escapeHtml(path)}</small>` : ""}
    </article>
  `;
}

function workbenchDraftCards(artifacts) {
  const drafts = artifacts?.workbench?.draft_artifacts || {};
  const labels = {
    timeline_patch: "時間軸修改",
    patched_draft_timeline: "草稿時間軸",
    workbench_contract_patch: "契約修改",
    workbench_handoff: "Agent 交接包",
    subtitle_patch: "字幕修改",
    audio_cue_patch: "音訊提示",
    effect_patch: "特效意圖",
    workbench_review_report: "Workbench 審核",
    workbench_review_report_md: "審核 Markdown",
  };
  return Object.entries(labels).map(([key, title]) => {
    const item = drafts[key] || {};
    return artifactCard({
      title,
      filename: item.filename || `${key}.json`,
      status: existsLabel(item.exists),
      description: item.exists ? "Workbench 已產生草稿，後續可交給 Agent 或 rerender 工具接手。" : "尚未由 Workbench 產生。",
      path: item.path,
    });
  }).join("");
}

export function ArtifactsView({ control, materialMap, artifacts }) {
  const stats = materialMap?.stats || {};
  const raw = artifacts?.raw_paths || {};
  const cards = [
    {
      title: "影片意圖",
      filename: "video_intent.json",
      status: materialMap?.intent ? "已載入" : "未找到",
      description: "Stage 0 的標準意圖檔，決定棕地 / 綠地 / 素材優先路線。",
      path: raw.state,
    },
    {
      title: "素材地圖",
      filename: "project_material_map.json",
      status: stats.assets || stats.needs ? "已載入" : "未找到",
      description: `目前讀到素材 ${stats.assets ?? 0}、需求 ${stats.needs ?? 0}、已接受對應 ${stats.accepted_edges ?? 0}。`,
      path: raw.state,
    },
    {
      title: "素材優先邊界驗收",
      filename: "material_first_boundary_acceptance_report.json",
      status: artifacts?.material_first_boundary_acceptance_report ? "已載入" : "未找到",
      description: "用來證明 material-first route 是否已通過邊界驗收。",
    },
    {
      title: "時間軸",
      filename: "timeline.json / preview_timeline.json",
      status: artifacts?.timeline || artifacts?.timeline_slots?.length ? "已載入" : "未找到",
      description: "Workbench 與後續 ffmpeg 剪輯的主要時間軸來源。",
      path: raw.timeline,
    },
    {
      title: "審核報告",
      filename: "review_report.json / workbench_review_report.json",
      status: artifacts?.review_report || artifacts?.workbench?.draft_summary?.has_review_report ? "已載入" : "未找到",
      description: "保存導演、素材、字幕、交付等審核結論。",
      path: raw.review_report,
    },
    {
      title: "交付驗證",
      filename: "delivery_gate.json / verify_result.json",
      status: artifacts?.delivery_gate || artifacts?.verify_evidence_bundle ? "已載入" : "未找到",
      description: "確認 final video、字幕、畫面與內容是否可交付。",
    },
  ];

  return `
    <section class="view-main full">
      <div class="section-head">
        <div>
          <p class="eyebrow">產物</p>
          <h2>重要文件與交接狀態</h2>
          <p class="view-note">只列會影響決策與交接的產物。完整 JSON 仍由檔案本身保存，不在主畫面大段顯示。</p>
        </div>
        <span class="mode-chip">${escapeHtml(artifacts?.profile || "unknown")}</span>
      </div>
      <section class="artifact-decision-grid">
        ${cards.map(artifactCard).join("")}
      </section>
      <section class="artifact-section">
        <div class="section-head compact">
          <div>
            <p class="eyebrow">Workbench 草稿</p>
            <h3>剪輯工作檯產物</h3>
          </div>
          <span class="mode-chip">${escapeHtml(artifacts?.workbench?.draft_summary?.present_count ?? 0)} 份</span>
        </div>
        <div class="artifact-decision-grid compact-grid">
          ${workbenchDraftCards(artifacts)}
        </div>
      </section>
      <section class="artifact-section">
        <div class="section-head compact">
          <div>
            <p class="eyebrow">目前 Root</p>
            <h3>${escapeHtml(artifacts?.artifact_root || control?.artifact_root || materialMap?.artifact_root || "未指定")}</h3>
          </div>
        </div>
      </section>
    </section>
  `;
}
