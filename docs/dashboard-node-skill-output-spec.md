---
title: Dashboard Node-Skill-Output Design Spec
type: implementation-spec
status: ready-for-build
updated: 2026-06-05
tags: [dashboard, node, skill, build-artifacts, review-surface]
---

# Dashboard Node-Skill-Output Design Spec

> 給施工 agent 用。本文件定義 dashboard V1 的資訊架構、資料來源、畫面區塊、
> 狀態規則與驗收條件。施工時以唯讀 dashboard 為主，不先做互動覆寫。

## 1. 設計目標

Dashboard 要從「跑完後看 QA」升級成「整條 video workflow 的 node review surface」。

核心呈現順序固定為：

```text
Node -> Skill -> Output -> Status -> Next Action
```

目的：

- 讓 Hermes / Codex / 其他 agent 看 dashboard 就知道目前跑到哪個 node。
- 讓使用者知道每個 node 由哪個 skill 負責、產出了什麼 artifact、是否可施工。
- 讓 BUILD layer 的工具選擇透明化，尤其是 `build_profile.json`、`generated_asset_requests.json`。
- 讓 review 集中到缺口、風險段、低分段、需要 generated/reshoot/human review 的 node。

## 2. 非目標

V1 不做這些：

- 不做段落素材互動覆寫。
- 不做拖拉 timeline。
- 不直接觸發 external provider。
- 不直接修改 `segment_contract.json`。
- 不把 dashboard 變成 source of truth。

Dashboard 只讀 artifacts。真相仍是：

```text
segment_contract.json
artifact_manifest.json
state.json
```

## 3. 資料來源

Dashboard V1 應優先讀 `artifact_manifest.json`。若不存在，再 fallback 到現有 `state.json` 掃描模式。

主要 artifacts：

| Artifact | 角色 | 來源 |
|---|---|---|
| `artifact_manifest.json` | run artifact index | `contract_adapter.py run` |
| `state.json` | route/verify truth | `mv_cut` / `video_pipeline` / `route.py` |
| `build_profile.json` | BUILD provider/tool profile | `build_profile.py` |
| `generated_asset_requests.json` | generated fallback requests | `generated_assets.py` |
| `generated_asset_manifest.json` | generated provider outputs | external provider / `generated_assets.py` |
| `model_routes.json` | model/tool model routing | `model_routing.py` |
| `music_structure.json` | beat/section/music structure | `music_structure.py` |
| `assembly_plan.json` | Node 9 editing intent | `edit_artifacts.py` |
| `timeline_build.json` | Node 10 concrete EDL | `edit_artifacts.py` |
| `editor_review.json` | Node 11 deterministic editor review | `editor_review.py` |
| `motion_graphics_render_plan.json` | optional motion graphics render plan surfaced under Node 14 Revision | `motion_graphics.py` |
| `qa_report.json` / `verify_result.json` | VERIFY result | `verify` / runtime |
| `final.mp4` | final render | `mv_cut` / `video_pipeline` |

## 4. Node Map

Dashboard V1 must render this node map even when some artifacts are missing.

| Node | Label | Skill | Required Output | Optional Output | Status Rule |
|---|---|---|---|---|---|
| 0 | Brief | `video-workflow` | `brief.json` | none | done if file exists or manifest references brief |
| 2 | Material Coverage | `curator` / `gap-analyzer` | `material_coverage_map.json` | `material_needs.json`, source inventory | done if demand categories are mapped to available/needed supply |
| 3 | Contract | `spec-contract` | `segment_contract.json` | contract hash | done if manifest has canonical contract |
| 4-7 | Contract Facets | `writer` / `audio-director` / `effects-director` / `director` / `curator` | populated segment contract facets | facet review notes | done if required facet reasons are present; audio here is intent/role only |
| 5 | Audio Build | `audio-director` | `music_structure.json` | `music` path | done if artifact exists; this is BUILD timing/beat artifact, not the contract audio facet |
| 8 | Fallback/Profile | `gap-analyzer` / `generative-director` | `build_profile.json` | `fallback_route.json`, `generated_asset_requests.json` | warn if generated requests exist but no generated manifest |
| 9 | Assembly | `editor` | `assembly_plan.json` | unresolved requirements | done if artifact exists |
| 10 | Timeline | `editor` | `timeline_build.json` | source clips, tracks | done if artifact exists |
| 11 | Editor Review | `editor_review` | `editor_review.json` | review findings | pass/warn/block from artifact |
| 12 | Verify | `verify` | `state.json` | `qa_report.json`, `verify_result.json` | pass/warn/fail/block from state/qa |
| 13 | Render | `editor` | `final.mp4` | thumbnails/contact sheet | done if final exists |
| 14 | Revision | `route` / `editor` / `verify` / `dashboard` | `revision_plan.json` | `motion_graphics_render_plan.json`, `motion_graphics_manifest.json` | optional unless a revision/effects profile requires it |

## 5. Layout

### 5.1 Header

Show high-level run facts:

- Project name or output directory.
- Final video path/link.
- `next_action`.
- Pass/fail/warn badge.
- Build profile summary:
  - `render_profile`
  - `fallback_visual_provider`
  - `fallback_visual_mode`
  - `motion_graphics_backend`
  - `effects_enabled`
- Updated time.

### 5.2 Node Rail

Render horizontal or vertical rail:

```text
Brief -> Material Coverage -> Contract -> Build Profile -> Assembly -> Timeline -> Editor Review -> Verify -> Render -> Revision
```

Each node card shows:

- Node number.
- Skill name.
- Output artifact.
- Status badge.
- One-line reason.

Status colors:

| Status | Meaning |
|---|---|
| `done` | required artifact exists and no blocking finding |
| `warn` | artifact exists but has warnings or follow-up |
| `blocked` | node cannot proceed without material/spec/provider/human action |
| `missing` | artifact expected but not found |
| `optional` | artifact absent but not required by current profile |

### 5.3 Node Detail Panel

When a node is selected, show:

```text
Node
Skill
Input artifacts
Output artifacts
Summary
Findings
Next action
Copy-paste command if applicable
```

V1 can render all details expanded instead of implementing click behavior, if simpler.

### 5.4 Segment Timeline

Keep the existing segment timeline, but make it explicitly three-layer:

```text
SPEC   story_purpose / visual_desc / audio / text / must_include
BUILD  provider / selected source / timeline in-out / generated request
VERIFY score / status / finding / next action
```

For each segment, show:

- `segment`
- `story_purpose`
- `visual_desc`
- `source`
- provider if known
- `must_include`
- `audio.role`
- text layer summary
- selected clip/source path
- timeline in/out/duration if present
- generated request if present
- verify score/status
- fix target / next action

## 6. Artifact Parsing Rules

### 6.1 `artifact_manifest.json`

Use it as the artifact index. Expected fields after current BUILD changes:

```json
{
  "canonical_contract": "...",
  "contract_hash": "sha256:...",
  "generated_payload": "...",
  "material_db": "...",
  "music": "...",
  "music_structure": "...",
  "model_routes": "...",
  "build_profile": "...",
  "stock_first_route": "...",
  "generated_asset_requests": "...",
  "assembly_plan": "...",
  "timeline_build": "...",
  "editor_review": "...",
  "final": "...",
  "state": "...",
  "verify_result": "..."
}
```

Missing optional fields should not crash dashboard.

### 6.2 `build_profile.json`

Render these fields:

```text
render_profile
fallback_visual_provider
provider_priority
fallback_visual_mode
effects_enabled
motion_graphics_backend
model_routes
quality_baseline
```

If provider is `comfyui`, dashboard must show `blocked/deprecated provider`.

### 6.3 `generated_asset_requests.json`

Show:

- item count
- provider priority
- segment id
- provider
- prompt
- reason
- `forbidden_as_truth`

If requests exist but `generated_asset_manifest.json` is absent:

```text
status = warn
next_action = wait_for_generated_provider
```

### 6.4 `assembly_plan.json`

Show per segment:

- contract segment
- story purpose
- candidate policy
- must include
- unresolved requirements if present
- selection reason if present

### 6.5 `timeline_build.json`

Show per clip:

- segment
- source path
- original start/end
- adjusted start/end
- timeline in/out
- duration
- audio policy
- transition
- text overlay
- trace

If a timeline clip lacks trace:

```text
status = warn or fail
finding = timeline item has no trace
```

### 6.6 `editor_review.json`

Show:

- decision
- findings
- next node if present
- rerender/block/human review reason

Map decision:

| Decision | Dashboard Status |
|---|---|
| `approve` | done |
| `auto_fix` | warn |
| `route_change` | warn |
| `human_review` | warn |
| `rerender` | blocked |
| `block` | blocked |

## 7. Next Action Rules

Dashboard should derive next action in this priority:

1. `state.next_action` if present.
2. `editor_review.decision` if block/rerender/human_review.
3. generated requests exist but no generated manifest.
4. missing required artifact for current node.
5. final exists and verify pass.

Common output:

| Condition | Dashboard Next Action |
|---|---|
| missing local/proof material | `await_material` |
| generated requests pending | `wait_for_generated_provider` |
| editor review block | `fix_timeline_or_assembly` |
| verify fail | `route_by_verify_findings` |
| final pass | `complete_review_final` |

## 8. V1 Build Scope

Implement only:

1. Read `artifact_manifest.json` from workdir.
2. Load referenced JSON artifacts safely.
3. Build a normalized dashboard state object:

```json
{
  "run": {},
  "nodes": [],
  "segments": [],
  "artifacts": {},
  "next_action": "...",
  "findings": []
}
```

4. Render:
   - Header
   - Node rail/cards
   - Node detail cards
   - Segment timeline
   - Blocking/findings panel
5. Preserve existing `state.json` fallback mode.

## 9. V2 Scope

Do later:

- Click node to focus detail.
- Human override per segment.
- Choose replacement material.
- Mark generated output accepted/rejected.
- Trigger copy-paste rerun commands.
- Contact sheet and thumbnails.
- Side-by-side final preview.

## 10. Build Notes

Frontend constraints:

- Keep dashboard self-contained HTML if possible.
- No heavy framework required for V1.
- Must work with `file://` self-contained dashboard output.
- Must also work through `video_tools.py serve`.
- Do not introduce a build step unless necessary.
- Keep text readable on 1366px desktop and mobile.

Implementation target:

```text
dashboard.html
video_tools.py dashboard/state helpers if needed
tests for state normalization
```

Suggested helper:

```text
dashboard_state.py
  load_dashboard_state(workdir) -> normalized dashboard state
```

If creating this helper, tests should target it rather than browser rendering.

## 11. Tests

Required tests:

1. Manifest-based dashboard state includes nodes:
   - build_profile
   - generated_asset_requests
   - assembly_plan
   - timeline_build
   - editor_review
2. Missing optional effects artifact does not fail when `effects_enabled=false`.
3. Generated requests without generated manifest produce warn status.
4. ComfyUI provider in build profile produces blocked/deprecated finding.
5. Existing route `state.json` dashboard mode still works.

Suggested command:

```bash
python3 -m unittest tests.test_dashboard_state tests.test_video_tools_state -v
```

Full regression before handoff:

```bash
python3 -m unittest discover -s tests -v
```

## 12. Acceptance Criteria

Dashboard V1 is accepted when:

- A canonical run directory with `artifact_manifest.json` shows Node -> Skill -> Output for all known nodes.
- `build_profile.json` provider decisions are visible.
- `generated_asset_requests.json` pending segments are visible.
- Segment timeline clearly separates SPEC / BUILD / VERIFY.
- Missing artifacts show as missing/warn/block instead of crashing.
- Existing self-contained dashboard still opens by file.
- Full test suite passes.

## 13. Review Checklist For Codex

When reviewing implementation, check:

- Does dashboard treat `segment_contract.json` as SPEC truth and not legacy script?
- Does dashboard distinguish provider decision from SPEC?
- Does dashboard avoid making generated image look like real event footage?
- Does dashboard show Node -> Skill -> Output without requiring terminal knowledge?
- Does dashboard keep V1 read-only?
- Are status rules deterministic and test-covered?
- Does file mode still work?
