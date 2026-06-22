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
          visual_family: "classroom",
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
assert.match(materialHtml, /class="decision-panel"/);
assert.match(materialHtml, /dashboard_review_decision_packet_preview/);
assert.match(materialHtml, /class="decision-packet-preview"/);
assert.match(materialHtml, /class="evidence-drawer" data-evidence-type="need"/);
assert.match(materialHtml, /data-asset-id="asset_001"/);
assert.match(materialHtml, /data-need-id="need_001"/);
assert.match(materialHtml, /need-card thin selected/);
assert.match(materialHtml, /&quot;handoff_to&quot;: &quot;material_map_review&quot;/);

const routeHtml = RouteOverviewView({
  control,
  materialMap,
  activeStage: "Material Map",
});
assert.match(routeHtml, /class="stage-detail-panel" data-active-stage="Material Map"/);
assert.match(routeHtml, /路線總覽/);
assert.match(routeHtml, /影片流程審核/);
assert.match(routeHtml, /節點詳情/);
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
assert.match(headerHtml, /影片管線儀表板/);
assert.match(headerHtml, /選擇 Run/);
assert.match(headerHtml, /id="spa-project-select"/);
assert.match(headerHtml, /data-root="C:\/runs\/story"/);

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
assert.match(workbenchHtml, /workbench-review-summary/);
assert.match(workbenchHtml, /互動草稿工作區/);
assert.match(workbenchHtml, /src="\/workbench\/index.html\?root=C%3A%2Fruns%2Fstory"/);

console.log("dashboard_spa_render_smoke: checks passed");
