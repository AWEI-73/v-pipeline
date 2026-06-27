import { escapeHtml } from "../components/StatusPill.js";

function asList(value) {
  return Array.isArray(value) ? value : [];
}

function textOr(value, fallback = "未提供") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function assetSceneCount(asset) {
  return asList(asset?.scenes).length || Number(asset?.scene_count || 0) || 0;
}

function sceneNeedEdges(scene) {
  const satisfies = asList(scene?.satisfies)
    .filter((edge) => edge?.need_id)
    .map((edge) => ({
      need_id: edge.need_id,
      status: edge.status || edge.verdict || edge.decision || "candidate",
    }));
  if (satisfies.length) return satisfies;
  const ids = asList(scene?.need_ids);
  const statuses = asList(scene?.statuses);
  return ids.map((needId, index) => ({
    need_id: needId,
    status: statuses[index] || "candidate",
  }));
}

function assetMatchesNeed(asset, needId) {
  if (!needId) return false;
  return asList(asset?.scenes).some((scene) => sceneNeedEdges(scene).some((edge) => edge.need_id === needId));
}

function assetVerdictForNeed(asset, needId) {
  const edge = asList(asset?.scenes)
    .flatMap((scene) => sceneNeedEdges(scene))
    .find((item) => item.need_id === needId);
  const status = String(edge?.status || "").toLowerCase();
  if (["accepted", "accept", "keep", "kept", "採用", "已採用"].includes(status)) return "採用";
  if (["reject", "rejected", "exclude", "excluded", "排除", "已排除"].includes(status)) return "排除";
  if (["candidate", "maybe", "候選", "待確認"].includes(status)) return "候選";
  return edge?.status || "待判斷";
}

function assetUsableForNeed(asset, needId) {
  if (!needId) return true;
  return assetVerdictForNeed(asset, needId) !== "排除";
}

function sceneTimeRange(scene) {
  const usable = scene?.usable_range || scene?.usableRange || null;
  const start = usable?.start ?? usable?.start_sec ?? scene?.start ?? scene?.start_sec;
  const end = usable?.end ?? usable?.end_sec ?? scene?.end ?? scene?.end_sec;
  if (start !== undefined && end !== undefined) return `${start}s - ${end}s`;
  return "尚未標記";
}

function sceneCutHint(scene) {
  const start = scene?.start_sec ?? scene?.timeline_start_sec ?? scene?.trim_start_sec;
  const duration = scene?.duration_sec ?? scene?.slot_dur ?? scene?.trim_duration_sec;
  if (start !== undefined && duration !== undefined) return `從 ${start}s 開始，使用 ${duration}s`;
  return "尚未形成粗剪切點";
}

function needLabel(need) {
  return textOr(need?.purpose || need?.need_id, "未命名需求");
}

function selectedEvidenceFor(materialMap, selectedEvidence) {
  const assets = asList(materialMap?.assets);
  const needs = asList(materialMap?.needs);
  if (selectedEvidence?.type === "need") {
    const need = needs.find((item) => item.need_id === selectedEvidence.id);
    if (need) return { type: "need", item: need };
  }
  if (selectedEvidence?.type === "asset") {
    const asset = assets.find((item) => item.asset_id === selectedEvidence.id);
    if (asset) return { type: "asset", item: asset };
  }
  if (needs[0]) return { type: "need", item: needs[0] };
  if (assets[0]) return { type: "asset", item: assets[0] };
  return null;
}

function assetsForEvidence(materialMap, evidence) {
  const assets = asList(materialMap?.assets);
  if (!evidence) return [];
  if (evidence.type === "asset") return [evidence.item];
  return assets.filter((asset) => assetMatchesNeed(asset, evidence.item.need_id)).slice(0, 8);
}

function needsForEvidence(materialMap, evidence) {
  const needs = asList(materialMap?.needs);
  if (!evidence) return [];
  if (evidence.type === "need") return [evidence.item];
  const sceneNeedIds = new Set(asList(evidence.item.scenes).flatMap((scene) => sceneNeedEdges(scene).map((edge) => edge.need_id)));
  return needs.filter((need) => sceneNeedIds.has(need.need_id)).slice(0, 6);
}

function renderNeedRail(needs, evidence) {
  if (!needs.length) {
    return `<div class="empty-state">目前沒有讀到素材需求。可以先回到 Video Intent / Segment Contract 補需求，再生成素材地圖。</div>`;
  }
  return needs.map((need, index) => {
    const selected = evidence?.type === "need" && evidence.item.need_id === need.need_id;
    const outcome = textOr(need.outcome, "unknown");
    const accepted = Number(need.accepted || 0);
    const candidate = Number(need.candidate || 0);
    const missing = accepted > 0 ? 0 : 1;
    return `
      <button class="mm-scene-card ${selected ? "active" : ""}" data-need-id="${escapeHtml(need.need_id)}">
        <div class="mm-scene-title">
          <span>第 ${index + 1} 項 ${escapeHtml(need.need_id)}</span>
          <strong>${escapeHtml(outcome)}</strong>
        </div>
        <p>${escapeHtml(needLabel(need))}</p>
        <div class="mm-metrics">
          <span>採用 ${escapeHtml(accepted)}</span>
          <span>候選 ${escapeHtml(candidate)}</span>
          <span>缺口 ${missing}</span>
        </div>
      </button>
    `;
  }).join("");
}

function renderAssetChip(asset, needId, selected) {
  const verdict = needId ? assetVerdictForNeed(asset, needId) : "關聯";
  const tone = verdict === "採用" ? "good" : verdict === "排除" ? "bad" : "maybe";
  const firstScene = asList(asset.scenes)[0] || {};
  const thumb = firstScene.thumbnail_url
    ? `<img class="mm-thumb" src="${escapeHtml(firstScene.thumbnail_url)}" alt="${escapeHtml(firstScene.caption || asset.asset_id || "素材縮圖")}" loading="lazy" />`
    : `<span class="mm-thumb">${escapeHtml(asset.asset_type || "素材")}</span>`;
  return `
    <button class="mm-asset-chip ${tone} ${selected ? "active" : ""}" data-asset-id="${escapeHtml(asset.asset_id)}">
      ${thumb}
      <span>
        <strong>${escapeHtml(asset.asset_id)}</strong>
        <small>${escapeHtml(firstScene.caption || asset.source || "尚無描述")}</small>
      </span>
      <b>${escapeHtml(verdict)}</b>
    </button>
  `;
}

function renderNeedNode(need, selected) {
  const outcome = textOr(need.outcome, "unknown");
  const tone = outcome === "covered" || Number(need.accepted || 0) > 0 ? "good" : Number(need.candidate || 0) > 0 ? "maybe" : "bad";
  return `
    <button class="mm-graph-node ${tone} ${selected ? "active" : ""}" data-need-id="${escapeHtml(need.need_id)}">
      <strong>${escapeHtml(need.need_id)}</strong>
      <span>${escapeHtml(needLabel(need))}</span>
    </button>
  `;
}

function renderGraph(materialMap, evidence) {
  const relatedNeeds = needsForEvidence(materialMap, evidence);
  const relatedAssets = assetsForEvidence(materialMap, evidence);
  const activeNeed = evidence?.type === "need" ? evidence.item : relatedNeeds[0];
  const needId = activeNeed?.need_id || "";
  const usableAssets = relatedAssets.filter((asset) => assetUsableForNeed(asset, needId));
  const canSendToWorkbench = usableAssets.length > 0;
  const sceneTitle = evidence?.type === "asset"
    ? `素材 ${evidence.item.asset_id}`
    : `需求 ${needId || "未選取"}`;
  const sceneDesc = evidence?.type === "asset"
    ? "從素材反查它支撐哪些劇本需求與粗剪位置。"
    : "從劇本需求檢查有哪些素材支撐、哪些只是候選、哪些仍是缺口。";

  return `
    <section class="mm-canvas">
      <div class="mm-canvas-head">
        <div>
          <h2>${escapeHtml(sceneTitle)}</h2>
          <p>${escapeHtml(sceneDesc)}</p>
        </div>
        <div class="mm-tool-row">
          <span>${materialMap?.ready_for_build ? "可進入粗剪" : "等待素材審核"}</span>
          <span>${escapeHtml(materialMap?.route || "material-first")}</span>
        </div>
      </div>
      <div class="mm-graph">
        <div class="mm-col">
          <div class="mm-col-label">段落 / 需求</div>
          <div class="mm-graph-node active">
            <strong>${escapeHtml(sceneTitle)}</strong>
            <span>${escapeHtml(sceneDesc)}</span>
          </div>
        </div>
        <div class="mm-col">
          <div class="mm-col-label">鏡頭需求</div>
          ${relatedNeeds.length ? relatedNeeds.map((need) => renderNeedNode(need, activeNeed?.need_id === need.need_id)).join("") : "<div class='mm-graph-node bad'><strong>缺少需求</strong><span>尚未建立可檢查的 material need。</span></div>"}
        </div>
        <div class="mm-col wide">
          <div class="mm-col-label">素材候選</div>
          <div class="mm-asset-grid">
            ${relatedAssets.length ? relatedAssets.map((asset) => renderAssetChip(asset, needId, evidence?.type === "asset" && evidence.item.asset_id === asset.asset_id)).join("") : "<div class='empty-state'>這個需求目前沒有對應素材。應回到素材審核或標記補拍 / 生成缺口。</div>"}
          </div>
        </div>
        <div class="mm-col">
          <div class="mm-col-label">粗剪決策</div>
          <div class="mm-graph-node ${canSendToWorkbench ? "cut" : "bad"}">
            <strong>${canSendToWorkbench ? "可送 Workbench" : "暫停"}</strong>
            <span>${canSendToWorkbench ? "已有素材支撐，可進一步檢查切點與段落長度。" : "沒有可用素材，不應直接進入粗剪。"}</span>
          </div>
        </div>
      </div>
    </section>
  `;
}

function renderContractPaper(materialMap, evidence) {
  if (!evidence) {
    return `
      <aside class="mm-contract-paper">
        <h2>素材判斷契約紙</h2>
        <p>尚未讀到素材或需求。</p>
      </aside>
    `;
  }
  const isAsset = evidence.type === "asset";
  const item = evidence.item;
  const relatedNeeds = needsForEvidence(materialMap, evidence);
  const relatedAssets = assetsForEvidence(materialMap, evidence);
  const activeNeedId = evidence.type === "need" ? evidence.item.need_id : relatedNeeds[0]?.need_id;
  const usableAssets = relatedAssets.filter((asset) => assetUsableForNeed(asset, activeNeedId));
  const activeAsset = evidence.type === "asset" ? evidence.item : relatedAssets[0];
  const activeScene = activeAsset
    ? asList(activeAsset.scenes).find((scene) => !activeNeedId || sceneNeedEdges(scene).some((edge) => edge.need_id === activeNeedId))
      || asList(activeAsset.scenes)[0]
    : null;
  const title = isAsset ? item.asset_id : item.need_id;
  const summary = isAsset ? textOr(item.source, "素材來源未提供") : needLabel(item);
  const outcome = isAsset ? textOr(item.asset_type, "素材") : textOr(item.outcome, "unknown");
  const accepted = isAsset
    ? relatedNeeds.map((need) => need.need_id).join("、") || "尚未對應需求"
    : `${textOr(item.accepted, 0)} 個採用素材`;
  const candidates = isAsset
    ? `${assetSceneCount(item)} 個 scene 描述`
    : `${textOr(item.candidate, 0)} 個候選素材`;
  const selectedAssetVerdict = isAsset && activeNeedId ? assetVerdictForNeed(item, activeNeedId) : "";
  const selectedAssetUsable = isAsset && selectedAssetVerdict !== "排除";
  const next = selectedAssetVerdict === "排除"
    ? "此素材目前被排除，不應直接送 Workbench；可回素材審核或改為候選。"
    : usableAssets.length || selectedAssetUsable
    ? "可交給 Workbench 檢查切點、長度與替換素材。"
    : "先補素材審核 verdict，或將此項標記為補拍 / 生成缺口。";

  return `
    <aside class="mm-contract-paper">
      <h2>素材判斷契約紙</h2>
      <p>${escapeHtml(summary)}</p>
      <div class="mm-kv">
        <span>目前選取</span><strong>${escapeHtml(title)}</strong>
        <span>類型 / 狀態</span><strong>${escapeHtml(outcome)}</strong>
        <span>已滿足</span><strong>${escapeHtml(accepted)}</strong>
        <span>候選 / 描述</span><strong>${escapeHtml(candidates)}</strong>
        <span>可用區間</span><strong>${escapeHtml(sceneTimeRange(activeScene))}</strong>
        <span>粗剪切點</span><strong>${escapeHtml(sceneCutHint(activeScene))}</strong>
        <span>下一步</span><strong>${escapeHtml(next)}</strong>
      </div>
      <div class="mm-contract-note">
        <strong>設計原則</strong>
        <p>這裡只顯示會影響剪輯決策的素材資訊；完整 JSON 仍保留給開發者模式。</p>
      </div>
    </aside>
  `;
}

export function MaterialMapView({ materialMap, selectedEvidence }) {
  const needs = asList(materialMap?.needs);
  const evidence = selectedEvidenceFor(materialMap, selectedEvidence);
  const assets = asList(materialMap?.assets);
  return `
    <section class="material-map-workspace">
      <aside class="mm-scene-rail">
        <div class="eyebrow">素材地圖</div>
        <h2>以劇本需求看素材</h2>
        <p>不要把素材全部攤開；先選一個段落或需求，再看它的採用、候選、排除與缺口。</p>
        <div class="mm-summary-row">
          <span>素材 ${escapeHtml(assets.length)}</span>
          <span>需求 ${escapeHtml(needs.length)}</span>
          <span>${materialMap?.ready_for_build ? "BUILD ready" : "需審核"}</span>
        </div>
        <div class="mm-scene-list">
          ${renderNeedRail(needs, evidence)}
        </div>
      </aside>
      ${renderGraph(materialMap, evidence)}
      ${renderContractPaper(materialMap, evidence)}
    </section>
  `;
}
