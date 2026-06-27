import assert from "node:assert/strict";

import { AppHeader } from "../dashboard/src/components/AppHeader.js";
import { MaterialMapView } from "../dashboard/src/views/MaterialMapView.js";
import { RouteOverviewView } from "../dashboard/src/views/RouteOverviewView.js";
import { WorkbenchView } from "../dashboard/src/views/WorkbenchView.js";

const materialMap = {
  artifact_role: "material_map_dashboard_view",
  artifact_root: "C:/runs/story",
  entry_path: "material_first",
  route: "existing_material_first",
  ready_for_build: false,
  video_type: "training_recap",
  audience: "internal_training_stakeholders",
  intent: {
    video_type: "training_recap",
    audience: "internal_training_stakeholders",
    goal: "Turn existing training footage into a concise recap.",
    material_availability: "existing_material_available",
    text_availability: "brief_available",
    input_state: "brownfield_existing_material",
    entry_path: "material_first",
    route: "existing_material_first",
    gap_strategy: "material_delta_then_collect_or_generate_if_needed",
    required_followup_questions: [],
    assumptions: ["Source media are available."],
    handoff_to: "material_map_lifecycle",
    expected_outputs: ["project_material_map.json", "material_delta.json"],
  },
  stats: { assets: 1, needs: 1, accepted_edges: 1 },
  delta_summary: { covered: 0, thin: 1, missing: 0 },
  stages: [
    { label: "Intent", artifact: "video_intent.json", status: "present" },
    { label: "Material Ingest", artifact: "media", status: "present" },
    { label: "Material Map", artifact: "reviewed_project_material_map.json", status: "present" },
    { label: "Coverage Delta", artifact: "material_delta.json", status: "present" },
    { label: "Contract", artifact: "segment_contract.json", status: "present" },
    { label: "Timeline", artifact: "timeline.json", status: "present" },
  ],
  assets: [
    {
      asset_id: "asset_001",
      asset_type: "video",
      source: "materials/clip.mp4",
      scene_count: 1,
      scenes: [
        {
          caption: "students entering the classroom",
          need_ids: ["need_001"],
          statuses: ["accepted"],
          usable_range: { start: 1.5, end: 8.5 },
          start_sec: 2,
          duration_sec: 5,
          thumbnail_url: "/static/thumbs/clip.jpg?root=C%3A%2Fruns%2Fstory",
          visual_family: "classroom",
          angle_scale: "wide",
        },
      ],
    },
    {
      asset_id: "asset_002",
      asset_type: "video",
      source: "materials/rejected.mp4",
      scene_count: 1,
      scenes: [
        {
          caption: "wrong ceremony angle",
          satisfies: [{ need_id: "need_001", status: "rejected" }],
          visual_family: "ceremony",
          angle_scale: "medium",
        },
      ],
    },
    {
      asset_id: "asset_003",
      asset_type: "video",
      source: "materials/rejected-only.mp4",
      scene_count: 1,
      scenes: [
        {
          caption: "irrelevant hallway",
          satisfies: [{ need_id: "need_002", status: "rejected" }],
          visual_family: "hallway",
          angle_scale: "wide",
        },
      ],
    },
  ],
  needs: [
    {
      need_id: "need_001",
      purpose: "establish learning context",
      count: 1,
      accepted: 1,
      candidate: 0,
      outcome: "thin",
    },
    {
      need_id: "need_002",
      purpose: "show closing promise",
      count: 1,
      accepted: 0,
      candidate: 0,
      outcome: "missing",
    },
  ],
};

const control = {
  artifact_root: "C:/runs/story",
  recommended_next_action: "review_workbench_drafts",
};

const materialHtml = MaterialMapView({
  materialMap,
  selectedEvidence: { type: "need", id: "need_001" },
});
assert.match(materialHtml, /class="material-map-workspace"/);
assert.match(materialHtml, /以劇本需求看素材/);
assert.match(materialHtml, /class="mm-contract-paper"/);
assert.match(materialHtml, /素材判斷契約紙/);
assert.match(materialHtml, /data-asset-id="asset_001"/);
assert.match(materialHtml, /data-asset-id="asset_002"/);
assert.match(materialHtml, /<img class="mm-thumb"/);
assert.match(materialHtml, /src="\/static\/thumbs\/clip\.jpg\?root=C%3A%2Fruns%2Fstory"/);
assert.match(materialHtml, /data-need-id="need_001"/);
assert.match(materialHtml, /mm-scene-card active/);
assert.match(materialHtml, /wrong ceremony angle/);
assert.match(materialHtml, /排除/);
assert.match(materialHtml, /可用區間/);
assert.match(materialHtml, /1\.5s - 8\.5s/);
assert.match(materialHtml, /粗剪切點/);
assert.match(materialHtml, /從 2s 開始，使用 5s/);
assert.match(materialHtml, /可送 Workbench/);

const rejectedOnlyHtml = MaterialMapView({
  materialMap,
  selectedEvidence: { type: "need", id: "need_002" },
});
assert.match(rejectedOnlyHtml, /data-asset-id="asset_003"/);
assert.match(rejectedOnlyHtml, /排除/);
assert.match(rejectedOnlyHtml, /暫停/);
assert.match(rejectedOnlyHtml, /沒有可用素材/);
assert.doesNotMatch(rejectedOnlyHtml, /可送 Workbench/);

const routeHtml = RouteOverviewView({
  control,
  materialMap,
  activeStage: "Material Map",
});
assert.match(routeHtml, /class="stage-detail-panel" data-active-stage="Material Map"/);
assert.match(routeHtml, /路線總覽/);
assert.match(routeHtml, /影片流程審核/);
assert.match(routeHtml, /中文契約紙/);
assert.match(routeHtml, /目前判斷/);
assert.match(routeHtml, /class="stage-file-list"/);
assert.match(routeHtml, /project_material_map\.json/);
assert.match(routeHtml, /reviewed_project_material_map\.json/);
assert.match(routeHtml, /class="stage-file-status"/);

const intentHtml = RouteOverviewView({
  control,
  materialMap,
  activeStage: "Intent",
});
assert.match(intentHtml, /開案摘要/);
assert.match(intentHtml, /養成班 \/ 訓練回顧/);
assert.match(intentHtml, /主要觀眾/);
assert.match(intentHtml, /素材狀態/);
assert.match(intentHtml, /已有素材/);
assert.match(intentHtml, /需要追問/);
assert.match(intentHtml, /目前資訊足夠，不需要追問。/);
assert.match(intentHtml, /預期產物/);
assert.doesNotMatch(intentHtml, /<pre/);

const headerHtml = AppHeader({
  control,
  materialMap,
  activeView: "material-map",
  root: "C:/runs/story",
  projects: [{ name: "Story Run", path: "C:/runs/story" }],
});
assert.match(headerHtml, /影片製作管線工作台/);
assert.match(headerHtml, /白盒 Dashboard/);
assert.match(headerHtml, /選擇 Run/);
assert.match(headerHtml, /id="spa-project-select"/);
assert.match(headerHtml, /id="spa-root-input"/);
assert.match(headerHtml, /list="spa-project-paths"/);
assert.match(headerHtml, /id="spa-project-paths"/);
assert.match(headerHtml, /value="C:\/runs\/story"/);
assert.match(headerHtml, /打開資料夾/);
assert.match(headerHtml, />開啟</);
assert.match(headerHtml, /data-root="C:\/runs\/story"/);
assert.match(headerHtml, /class="pause-banner"/);
assert.match(headerHtml, /目前路線/);

const workbenchHeaderHtml = AppHeader({
  control,
  materialMap,
  activeView: "workbench",
  root: "C:/runs/story",
  projects: [{ name: "Story Run", path: "C:/runs/story" }],
});
assert.match(workbenchHeaderHtml, /黑盒 Workbench/);
assert.doesNotMatch(workbenchHeaderHtml, /class="pause-banner"/);
assert.doesNotMatch(workbenchHeaderHtml, /目前路線/);

const workbenchHtml = WorkbenchView({
  root: "C:/runs/story",
  workbenchHealth: {
    status: "ok",
    can_preview: true,
    artifact_root: "C:/runs/story",
  },
  artifacts: {
    workbench: {
      draft_summary: {
        present_count: 4,
        timeline_edits: 2,
        subtitle_edits: 1,
        audio_cues: 1,
        effect_intents: 0,
        has_handoff: true,
        has_review_report: false,
        agent_ready: false,
        handoff_validation: {
          ok: true,
          error_count: 0,
          warning_count: 1,
        },
      },
    },
  },
});
assert.match(workbenchHtml, /workbench-view/);
assert.match(workbenchHtml, /workbench-run-strip/);
assert.ok(workbenchHtml.includes("影片剪輯工作台"));
assert.ok(workbenchHtml.includes("保留舊版 Workbench 的互動畫面、播放控制與四條時間軸"));
assert.ok(workbenchHtml.includes("Workbench 草稿摘要"));
assert.ok(workbenchHtml.includes("時間軸草稿 2"));
assert.ok(workbenchHtml.includes("字幕草稿 1"));
assert.ok(workbenchHtml.includes("音訊提示草稿 1"));
assert.ok(workbenchHtml.includes("特效意圖草稿 0"));
assert.ok(workbenchHtml.includes("交接驗證 通過"));
assert.match(workbenchHtml, /<iframe title="Hermes Workbench 黑盒剪輯工作檯"/);
assert.match(workbenchHtml, /src="\/workbench\/index.html\?root=C%3A%2Fruns%2Fstory"/);
assert.doesNotMatch(workbenchHtml, /monitor-box/);
assert.doesNotMatch(workbenchHtml, /timeline-wrap/);
assert.doesNotMatch(workbenchHtml, /clip-video/);
assert.doesNotMatch(workbenchHtml, /workbench-status-grid/);
assert.doesNotMatch(workbenchHtml, /workbench-review-summary/);

console.log("dashboard_spa_render_smoke: checks passed");
