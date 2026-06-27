import { escapeHtml } from "./StatusPill.js";
import { stageLabelsZh, zhStatus } from "../i18n/zh.js";

const routeOrder = [
  ["Intent", "釐清目的、觀眾與路線"],
  ["Material Ingest", "素材或生成候選進場"],
  ["Material Map", "建立可審核的素材證據"],
  ["Coverage Delta", "確認缺口與可建置性"],
  ["Structure", "固定故事或影片架構"],
  ["Contract", "轉成段落建置契約"],
  ["Timeline", "組成可預覽時間軸"],
  ["Review Gates", "導演與系統審核停點"],
  ["Verify", "交付前驗證與證據"],
];

function expandStages(stages) {
  const byLabel = new Map((stages || []).map((stage) => [stage.label, stage]));
  return routeOrder.map(([label, summary]) => {
    const found = byLabel.get(label);
    if (found) return { ...found, summary };
    if (label === "Material Map") return byLabel.get("Material Map") || { label, summary, artifact: "project_material_map.json", status: "missing" };
    if (label === "Coverage Delta") return byLabel.get("Coverage Delta") || { label, summary, artifact: "material_delta.json", status: "missing" };
    return { label, summary, artifact: "", status: "pending" };
  });
}

export function expandedRouteStages(stages = []) {
  return expandStages(stages);
}

export function VerticalRouteTimeline(stages = [], activeStage = "Material Map") {
  const expanded = expandStages(stages);
  return `
    <aside class="route-rail">
      <div class="rail-line">
        ${expanded.map((stage) => `
          <button type="button" class="rail-node ${escapeHtml(stage.status || "unknown")} ${stage.label === activeStage ? "active" : ""}" data-stage="${escapeHtml(stage.label)}" title="${escapeHtml(stage.artifact || stage.summary || "")}">
            <span class="rail-node-title">${escapeHtml(stageLabelsZh[stage.label] || stage.label)}</span>
            <span class="rail-node-summary">${escapeHtml(stage.summary || stage.artifact || "")}</span>
            <span class="rail-node-state">${escapeHtml(zhStatus(stage.status || "pending"))}</span>
          </button>
        `).join("")}
      </div>
    </aside>
  `;
}
