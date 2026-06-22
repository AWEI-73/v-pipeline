import { VerticalRouteTimeline } from "../components/VerticalRouteTimeline.js";
import { escapeHtml } from "../components/StatusPill.js";

function renderAsset(asset, selectedEvidence) {
  const selected = selectedEvidence?.type === "asset" && selectedEvidence.id === asset.asset_id;
  return `
    <article class="asset-card ${selected ? "selected" : ""}" data-asset-id="${escapeHtml(asset.asset_id)}" tabindex="0">
      <div class="asset-top">
        <strong>${escapeHtml(asset.asset_id)}</strong>
        <span>${escapeHtml(asset.asset_type)} / ${escapeHtml(asset.scene_count)} 個場景</span>
      </div>
      <div class="mono source-line">${escapeHtml(asset.source)}</div>
      ${(asset.scenes || []).map((scene) => `
        <div class="scene-row">
          <p>${escapeHtml(scene.caption || "未命名場景")}</p>
          <div class="tag-row">
            ${(scene.need_ids || []).map((id) => `<span>${escapeHtml(id)}</span>`).join("")}
            ${(scene.statuses || []).map((status) => `<span>${escapeHtml(status)}</span>`).join("")}
            ${scene.visual_family ? `<span>${escapeHtml(scene.visual_family)}</span>` : ""}
            ${scene.angle_scale ? `<span>${escapeHtml(scene.angle_scale)}</span>` : ""}
          </div>
        </div>
      `).join("")}
    </article>
  `;
}

function renderNeed(need, selectedEvidence) {
  const selected = selectedEvidence?.type === "need" && selectedEvidence.id === need.need_id;
  return `
    <article class="need-card ${escapeHtml(need.outcome || "unknown")} ${selected ? "selected" : ""}" data-need-id="${escapeHtml(need.need_id)}" tabindex="0">
      <div class="asset-top">
        <strong>${escapeHtml(need.need_id)}</strong>
        <span>${escapeHtml(need.outcome || "unknown")}</span>
      </div>
      <p>${escapeHtml(need.purpose)}</p>
      <small>需求 ${escapeHtml(need.count)} / 已接受 ${escapeHtml(need.accepted)} / 候選 ${escapeHtml(need.candidate)}</small>
    </article>
  `;
}

function resolveEvidence(materialMap, selectedEvidence) {
  const assets = materialMap?.assets || [];
  const needs = materialMap?.needs || [];
  if (selectedEvidence?.type === "need") {
    const need = needs.find((item) => item.need_id === selectedEvidence.id);
    if (need) return { type: "need", item: need };
  }
  if (selectedEvidence?.type === "asset") {
    const asset = assets.find((item) => item.asset_id === selectedEvidence.id);
    if (asset) return { type: "asset", item: asset };
  }
  if (assets[0]) return { type: "asset", item: assets[0] };
  if (needs[0]) return { type: "need", item: needs[0] };
  return null;
}

function buildDecisionPacket(materialMap, evidence) {
  const stages = materialMap?.stages || [];
  const sourceArtifacts = stages.map((stage) => stage.artifact).filter(Boolean);
  const decision = materialMap?.ready_for_build ? "continue_pipeline" : "pause_for_review";
  return {
    artifact_role: "dashboard_review_decision_packet_preview",
    version: 1,
    mode: "read_only_preview",
    route: materialMap?.route || "unknown",
    entry_path: materialMap?.entry_path || "unknown",
    selected_evidence: evidence
      ? { type: evidence.type, id: evidence.item.asset_id || evidence.item.need_id }
      : null,
    decision,
    handoff_to: materialMap?.ready_for_build ? "timeline_or_workbench" : "material_map_review",
    next_action: materialMap?.ready_for_build
      ? "continue to structure/contract/timeline build"
      : "review coverage gaps before build",
    source_artifacts: sourceArtifacts,
  };
}

function renderEvidenceDrawer(evidence) {
  if (!evidence) {
    return `
      <aside class="evidence-drawer">
        <p class="eyebrow">證據抽屜</p>
        <h3>尚未選取證據</h3>
        <p class="view-note">選擇一個素材或需求，即可檢視素材地圖中的判斷證據。</p>
      </aside>
    `;
  }
  const item = evidence.item;
  const title = evidence.type === "asset" ? item.asset_id : item.need_id;
  return `
    <aside class="evidence-drawer" data-evidence-type="${escapeHtml(evidence.type)}">
      <p class="eyebrow">證據抽屜</p>
      <h3>${escapeHtml(title)}</h3>
      <div class="evidence-kv">
        <span>類型</span><strong>${escapeHtml(evidence.type)}</strong>
        <span>狀態</span><strong>${escapeHtml(item.outcome || item.asset_type || "unknown")}</strong>
        <span>來源</span><strong>${escapeHtml(item.source || item.purpose || "-")}</strong>
      </div>
      ${evidence.type === "asset" ? `
        <div class="evidence-scenes">
          ${(item.scenes || []).map((scene) => `
            <article>
              <p>${escapeHtml(scene.caption || "未命名場景")}</p>
              <div class="tag-row">
                ${(scene.need_ids || []).map((id) => `<span>${escapeHtml(id)}</span>`).join("")}
                ${(scene.statuses || []).map((status) => `<span>${escapeHtml(status)}</span>`).join("")}
              </div>
            </article>
          `).join("") || "<p class='view-note'>沒有場景證據。</p>"}
        </div>
      ` : `
        <p class="view-note">需求 ${escapeHtml(item.count ?? "-")} / 已接受 ${escapeHtml(item.accepted ?? "-")} / 候選 ${escapeHtml(item.candidate ?? "-")}。</p>
      `}
    </aside>
  `;
}

function renderDecisionPanel(materialMap, evidence) {
  const packet = buildDecisionPacket(materialMap, evidence);
  return `
    <section class="decision-panel">
      <div>
        <p class="eyebrow">審核暫停</p>
        <h3>${escapeHtml(packet.decision)}</h3>
        <p class="view-note">這是唯讀的 route task packet 預覽，使用者審核後可交給 agent 接手。</p>
      </div>
      <pre class="decision-packet-preview">${escapeHtml(JSON.stringify(packet, null, 2))}</pre>
    </section>
  `;
}

export function MaterialMapView({ materialMap, selectedEvidence }) {
  const assets = materialMap?.assets || [];
  const needs = materialMap?.needs || [];
  const evidence = resolveEvidence(materialMap, selectedEvidence);
  return `
    <section class="view-grid">
      ${VerticalRouteTimeline(materialMap?.stages || [])}
      <section class="view-main">
        <div class="section-head">
          <div>
            <p class="eyebrow">素材真實狀態</p>
            <h2>素材地圖</h2>
          </div>
          <span class="mode-chip">${materialMap?.ready_for_build ? "可進入 BUILD" : "需要審核"}</span>
        </div>
        ${renderDecisionPanel(materialMap, evidence)}
        <div class="material-map-review-grid">
          <section>
            <h3>素材</h3>
            <div class="stack">${assets.length ? assets.map((asset) => renderAsset(asset, evidence && { type: evidence.type, id: evidence.item.asset_id || evidence.item.need_id })).join("") : "<div class='empty-state'>沒有找到素材。</div>"}</div>
          </section>
          <section>
            <h3>需求</h3>
            <div class="stack">${needs.length ? needs.map((need) => renderNeed(need, evidence && { type: evidence.type, id: evidence.item.asset_id || evidence.item.need_id })).join("") : "<div class='empty-state'>沒有找到需求。</div>"}</div>
          </section>
          ${renderEvidenceDrawer(evidence)}
        </div>
      </section>
    </section>
  `;
}
