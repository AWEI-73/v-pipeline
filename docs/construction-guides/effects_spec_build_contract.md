# 特效 SPEC→BUILD 完整規格(施工合約 / for Codex)

> 狀態:本檔是**施工規格**,不是現況文件。Part 1 描述既有實作(**不要重蓋**),
> Part 2 是要做的 5 個 delta(W1–W5),Part 3 是硬邊界(不准做),Part 4 是驗收。
> 文化鐵則:**TDD red 先行**,每個 W 都附失敗測試;green 是唯一驗收證據。
> 不改 render backend 行為、不接 Remotion 進主 BUILD、不把 backend API 餵進 agent。

---

## Part 0 — 治理原則(特效邊界 doctrine)

特效不靠單一邊界,靠**一個組織問句 + 三圈 + 兩條程序線**。所有 W 必須符合。

**組織問句:這個特效改變的是「意義」還是「感覺」?**

| 圈 | 定義 | 規則 | 落點 |
|---|---|---|---|
| **圈 0 禁區** | 讓觀眾以為某事件發生、但素材沒拍到 | 硬 NO | `must_not_satisfy_material_need=true`(已存在,`effect_contract.py`)|
| **圈 1 受閘** | 特效本身就是故事 beat(章節轉場/資訊字卡/記憶框) | `required_for_story=true` → **渲不出 = blocking gap** | W1 / W5 |
| **圈 2 自由** | 只改感覺(grade/simple fade/微 overlay) | 可自由 fallback,不擋交付 | W1(降為 warning)|

**兩條程序線(正交):**
- **高度線**:意圖永不漏 backend。`component/props/fps/durationFrames/springConfig` 出現在意圖層 = raise(已存在,`REMOTION_SPECIFIC_FIELDS`)。
- **權威線**:canonical final renderer 只有 ffmpeg `contract-run`;Workbench / Remotion 一律 draft,未 review 不得進合成。

**核心立場:能被問責的特效才值得做。** 任何新特效能力(backend)必須先有
(a) 中性詞彙 token、(b) conformance 認領、(c) 「required 的渲不出就紅燈」的測試,
**三者齊備才准長出來**。W2 提供 (a)(b),W1/W5 提供 (c)。

---

## Part 1 — 既有實作(AS-IS,不要重蓋)

施工前先讀這些,確認你在「擴充」而不是「重造」。

### FX1 中性合約 — `video_pipeline_core/effect_contract.py`
- `compile_effect_contract(director_shot_plan)` → `{effect_intent_plan, effect_asset_spec}`。
- `ALLOWED_EFFECT_ROLES`(11 種,封閉 enum):title_card / chapter_transition / lower_third /
  color_grade / overlay / particle / light_leak / transition_plate / motion_background /
  panel_frame / speed_line。
- `ALLOWED_INTENSITIES = {none, low, medium, high}`。
- effect 欄位:role / intent / intensity / target{beat_id,segment_id,story_function} /
  `visual_language: list[str]`(**目前自由字串,W2 要收斂**)/ `required_for_story: bool` /
  `must_preserve_proof: bool` / `allowed_backends` / `fallback`。
- `validate_effect_intent_plan()` / `validate_effect_asset_spec()`:已強制
  `must_not_satisfy_material_need=true`、`_ensure_no_backend_specific_fields`。
- CLI:`python video_tools.py effect-intent-plan <director_shot_plan.json> --out-plan effect_intent_plan.json --out-spec effect_asset_spec.json`。

### FX2 確定性渲染 + baseline review — `video_pipeline_core/light_effects.py`
- `build_light_effects_plan(contract, build_profile=None, *, effect_intent_plan=None)`:
  **已 join 兩種表徵** —— 同時吃 flat `contract.segments` 的 `_segment_operations(seg)`
  與中性 `_effect_intent_operations(effect_intent_plan)`,合成 `light_effects_plan.items`。
- `SAFE_OPERATIONS` 白名單;非法 op → raise。
- `write_light_effects_artifacts(...)` → `light_effects_manifest`。
- `record_motion_graphics_outputs` / `record_mv_render_outputs`。
- `build_light_effects_baseline_review(plan, manifest, *, final_video, audit_paths)` →
  `light_effects_baseline_review`,含 `gaps`(每 gap 帶 `effect_id` + `next_action`)。
- `motion_graphics.py`:render 配方 template(title_fade / section_label / lower_third_clean)。

### FX3 Node14 bounded 修正 — `video_pipeline_core/effect_revision.py`
- 吃 `light_effects_baseline_review.gaps` → `effect_revision_request`(bounded)。
- route:`ADAPTER_ROUTE = route_to_node14_or_remotion_adapter` /
  `RECIPE_ROUTE = implement_or_wire_effect_recipe`。
- `write_revised_effect_intent_plan(...)`(draft,不覆寫 canonical)。
- CLI:`effect-revision-request` / `effect-revision-draft` / `effect-revision-apply`。

### Remotion adapter(邊界後,prompt-driven)— `video_pipeline_core/remotion_effects.py`
- `build_remotion_prompt_pack(effect_revision_request, ...)`:按 `_component_family` 產 prompt-pack
  (component_family + prompt + timing + 驗收條件)。**不是 component API 字典。**
- CLI `remotion-prompt-pack`;bridge `tools/remotion_worker_bridge.mjs`。

### Capability / profile — `capability_manifest.py` / `build_profile.py`
- `build_capability_manifest()` → `capability_manifest`(列 capabilities,如
  `arbitrary_effects` / `remotion_backend`、render_profiles、render_backends)。
- `ALLOWED_RENDER_PROFILES = {no_effects, light_effects, motion_graphics, debug}`。
- `ALLOWED_RENDER_BACKENDS = {ffmpeg, capcut_draft, remotion, html_playwright}`。
- `ALLOWED_MOTION_BACKENDS = {ffmpeg_libass, html_playwright, remotion, mlt, blender}`。

### 交付閘(圈 1 問責,已存在)— `video_pipeline_core/delivery_gate.py`
- `evaluate_complete_video_delivery(root)`。
- `_effects_required(root)`:`effect_intent_plan.json` 或 `transition_plan.json` 非空 → 需驗證。
- 消費 `effect_render_verification.json`,規則:`missing_effect_render_verification` /
  `effect_render_verification_not_passed` / `effect_render_verification_has_no_verified_effects` /
  `planned_effect_not_rendered`(`verified_effects[i].rendered != true`)/
  `rendered_effect_has_no_evidence_refs`。
- **限制(W1 要修):** 上述規則對**所有** planned effect 一視同仁(全部 must-render),
  **不分** `required_for_story`。圈 1/圈 2 的差異尚未反映在嚴重度。

### 驗證側 — `presentation_feel_audit.py`
- `audit_presentation_feel(...)` 消費 `effect_overlays`,route 到 `editor/effects-director`。

---

## Part 2 — 施工項目(W1–W5)

每個 W:**目標 → artifact/schema → 函式簽名與整合點 → 規則 → TDD red → 驗收**。
施工順序建議:**W5 → W1 → W2 → W3 → W4**(W5 是 W1 的前置 plumbing)。

---

### W5(前置)— `required_for_story` / `must_preserve_proof` 全鏈傳遞

**目標**:讓 `required_for_story` 與 `must_preserve_proof` 從 `effect_intent_plan`
一路流到 `effect_render_verification.verified_effects[]`,否則 W1 無從分辨圈 1/圈 2。

**整合點**:
1. `light_effects.py::_effect_operation(effect)` / `_effect_intent_operations(...)`:
   產出的 op 必須帶 `effect_id`、`required_for_story`、`must_preserve_proof`、`role`、`intensity`。
2. `write_light_effects_artifacts` → manifest item 保留上述欄位。
3. `build_light_effects_baseline_review` 的 gap 與 rendered item 保留 `required_for_story`。
4. **新增** effect render verification 的產生器(目前 `effect_render_verification.json`
   是外部餵入的;改為由工具產生,見下)。

**新增工具**:`video_pipeline_core/effect_render_verification.py`
```python
def build_effect_render_verification(
    light_effects_manifest: dict,
    baseline_review: dict,
    *,
    visual_audit_ref: str | None = None,
    keyframe_grid_ref: str | None = None,
) -> dict:
    """彙整每個 planned effect 是否 rendered + evidence,輸出 delivery_gate 吃的 artifact。"""
```
輸出 schema(`artifact_role: effect_render_verification`, `version: 1`):
```json
{
  "artifact_role": "effect_render_verification",
  "version": 1,
  "pass": true,
  "visual_audit_ref": "visual_audit.json",
  "keyframe_grid_ref": "keyframe_grid.jpg",
  "verified_effects": [
    {
      "effect_id": "fx_b02_chapter_transition",
      "role": "chapter_transition",
      "required_for_story": true,
      "must_preserve_proof": true,
      "rendered": true,
      "fell_back": false,
      "fallback_used": null,
      "evidence_refs": ["visual_audit.json", "keyframe_grid.jpg"]
    }
  ]
}
```
CLI:`python video_tools.py effect-render-verification --run <dir> --out effect_render_verification.json`。

**TDD red**(`tests/test_effect_render_verification.py`):
- `test_required_for_story_propagates_from_intent_plan_to_verification`
- `test_decorative_effect_marked_fell_back_when_fallback_used`
- `test_must_preserve_proof_carried_through`

**驗收**:`effect_render_verification.verified_effects[]` 每筆都帶 `required_for_story`、
`rendered`、`fell_back`,且值與上游 `effect_intent_plan` 一致。

---

### W1 — 交付閘按圈 1/圈 2 分嚴重度(核心問責)

**目標**:把「全部 must-render」拆成圈 1(required)blocking、圈 2(decorative)warning。

**整合點**:`delivery_gate.py::evaluate_complete_video_delivery`,改 `verified_effects` 迴圈
(現 L947–968)。

**新規則語意**:
| 條件 | 嚴重度 | rule |
|---|---|---|
| `required_for_story=true` 且 `rendered!=true` | **blocking** | `required_effect_not_rendered` |
| `required_for_story=true` rendered 但無 evidence_refs | **blocking** | `required_effect_has_no_evidence_refs` |
| `required_for_story=false` 且 `rendered!=true` 但 `fell_back=true` | **warning** | `decorative_effect_fell_back` |
| `required_for_story=false` 且 `rendered!=true` 且 `fell_back!=true` | **warning** | `decorative_effect_dropped` |
| `must_preserve_proof=true` 但 evidence 顯示遮蔽證據(見 note) | **blocking** | `effect_obscured_proof` |

> note:`effect_obscured_proof` 第一版可只檢查 `effect_render_verification` 是否帶
> `proof_preserved: false` 旗標(由 presentation_feel_audit 或 visual_audit 標注);
> 不要在 delivery_gate 內做影像分析。

保留既有 `missing_effect_render_verification` / `effect_render_verification_not_passed`。
`planned_effect_not_rendered` 退役為 W1 兩條 required 規則(保留向後相容:若 item 無
`required_for_story` 欄位,**預設視為 required**=blocking,以免靜默放水)。

**TDD red**(`tests/test_delivery_gate_effect_severity.py`):
- `test_required_effect_not_rendered_blocks`
- `test_decorative_effect_fallback_is_warning_not_block`
- `test_missing_required_for_story_defaults_to_required_block`(安全預設)
- `test_must_preserve_proof_violation_blocks`

**驗收**:圈 1 渲不出 → `pass=false` 且 `blocking[0].rule=required_effect_not_rendered`;
圈 2 fallback → `pass` 不因此變 false,只進 `warnings`。

---

### W2 — 中性 `visual_language` 受控詞彙 + backend conformance(pre-BUILD 閘)

**目標**:把 `visual_language` 從自由字串收成受控詞彙,並在 **SPEC 階段**(BUILD 前)
就擋掉「沒有任何啟用 backend 能渲」的意圖,而不是渲染後才發現。

**新增 artifact A(意圖面,agent 可讀)**:`examples/effect_capability_vocab.json`
```json
{
  "artifact_role": "effect_capability_vocab",
  "version": 1,
  "roles": ["title_card", "chapter_transition", "...11 種"],
  "visual_language_tokens": {
    "paper_texture":   {"communicates": "report/memory", "pairs_with_roles": ["chapter_transition","panel_frame"]},
    "timestamp_overlay": {"communicates": "info_label",  "pairs_with_roles": ["lower_third","overlay"]},
    "light_leak":      {"communicates": "warmth/nostalgia","pairs_with_roles": ["overlay","light_leak"]},
    "speed_line":      {"communicates": "energy/motion",  "pairs_with_roles": ["speed_line","overlay"]}
  }
}
```
> 初版 token 從現有 code/skill 出現過的抽:paper_texture / timestamp_overlay /
> light_leak / speed_line(可再擴,但每加一個必須有 W2-B 認領 + 測試)。

**新增 artifact B(backend 面,agent 不可讀)**:`examples/effect_backend_conformance.json`
```json
{
  "artifact_role": "effect_backend_conformance",
  "version": 1,
  "backends": {
    "ffmpeg_light_effects": {
      "roles": {"title_card": "ok", "chapter_transition": "degraded", "particle": "none"},
      "tokens": {"timestamp_overlay": "ok", "paper_texture": "degraded", "light_leak": "ok"}
    },
    "motion_graphics": { "...": "..." },
    "remotion":        { "...": "..." }
  }
}
```
fidelity enum:`ok` / `degraded` / `none`。**這裡才是 Remotion / 社群 repo 特效編目的位置**
(挖 remotion-templates 等放進這份,版本化;adapter 更新只動這檔,意圖層不動)。

**新增檢查**:`video_pipeline_core/effect_conformance.py`
```python
def check_effect_conformance(
    effect_intent_plan: dict,
    *,
    vocab: dict,
    conformance: dict,
    enabled_backends: list[str],   # 來自 build_profile 本 run 啟用的 backends
) -> dict:
    """回 {artifact_role: effect_conformance_report, pass, blocking[], warnings[]}。"""
```
規則:
| 條件 | 嚴重度 | rule |
|---|---|---|
| `visual_language` token 不在 vocab | blocking | `unknown_visual_language_token` |
| token 與 role 不在 `pairs_with_roles` | warning | `token_role_mismatch` |
| `required_for_story=true` 的 effect,**所有**啟用 backend 對其 role 或 token 都是 `none` | blocking | `unrenderable_required_intent` |
| 同上但 `required_for_story=false` | warning | `unrenderable_decorative_intent` |
| 最佳可用 fidelity 僅 `degraded` 且 `required` | warning | `required_intent_degraded_only` |

接點:在 `spec-review` / BUILD 前節點呼叫(與既有 `perfunctory_spec` 同層,blocking →
回 SPEC 改意圖,不要修工具)。

**TDD red**(`tests/test_effect_conformance.py`):
- `test_unknown_token_blocks`
- `test_required_intent_no_backend_renders_blocks`
- `test_decorative_unrenderable_is_warning`
- `test_token_role_mismatch_warns`
- `test_every_vocab_token_has_at_least_one_backend`(詞彙↔認領對稱,守 Part 0 立場)

**驗收**:`effect_capability_vocab.json` 每個 token 在 `effect_backend_conformance.json`
至少一個 backend 非 `none`,否則該對稱測試紅燈。

---

### W3 — effect_intent 差異化 / 敷衍閘(對稱 material 的 perfunctory_spec)

**目標**:擋「每個 beat 填一樣的 effect_intent」的模板填充。

**新增檢查**:`video_pipeline_core/effect_perfunctory.py`
```python
def detect_effect_perfunctory(effect_intent_plan: dict) -> dict:
    """回 {signals: [...], level: ok|warn|blocking}。≥3 訊號共現 → blocking。"""
```
訊號(每條一個 signal):
- `identical_role_ratio`:>80% effect 同一 role。
- `identical_intensity`:全部同 intensity。
- `duplicate_visual_language`:≥3 effect 的 visual_language 完全相同集合。
- `placeholder_intent`:`intent` 長度 < 8 或在 {"fx","effect","-","n/a"}。
- `missing_reason_link`:effect 無法連回 `target.story_function`/`segment_id`。

語意比照 spec-contract:單一訊號 warn;**≥3 共現 → blocking(`perfunctory_effect_intent`)**。

**TDD red**(`tests/test_effect_perfunctory.py`):
- `test_all_identical_effect_intent_blocks`
- `test_single_signal_only_warns`
- `test_differentiated_plan_passes`

**驗收**:5 beat 全同 effect_intent → blocking;段段差異化 → pass。

---

### W4 — `section_role → effect_role` 政策表(對稱 style→transition)

**目標**:讓「這段該不該有這種特效」可稽核,而非全靠品味。

**新增 artifact**:`examples/effect_role_policy.json`
```json
{
  "artifact_role": "effect_role_policy",
  "version": 1,
  "by_section_role": {
    "opening":  {"recommended": ["title_card"], "discouraged": ["lower_third"], "forbidden": []},
    "hold":     {"recommended": [], "discouraged": ["particle","speed_line"], "forbidden": []},
    "montage":  {"recommended": ["overlay","light_leak","speed_line"], "discouraged": [], "forbidden": []},
    "closing":  {"recommended": ["title_card","chapter_transition"], "discouraged": [], "forbidden": []},
    "title":    {"recommended": ["title_card","motion_background"], "discouraged": [], "forbidden": []}
  }
}
```
**新增檢查**:`video_pipeline_core/effect_role_policy.py`
```python
def check_effect_role_policy(effect_intent_plan: dict, contract: dict, policy: dict) -> dict:
    """用 effect.target.segment_id 對到 segment.core.section_role,比對政策。"""
```
規則:
| 條件 | 嚴重度 | rule |
|---|---|---|
| role 在該 section 的 `forbidden` | blocking | `effect_role_forbidden_for_section` |
| role 在 `discouraged` 且**無 reason override** | warning | `effect_role_discouraged_for_section` |
| 有 `reason`/`creative_exception` override | 放行(記 note) | — |

> 政策是**預設政策**,不是鐵律——比照 style→transition「段落可覆寫」。override 必須留 reason。

**TDD red**(`tests/test_effect_role_policy.py`):
- `test_forbidden_role_blocks`
- `test_discouraged_without_reason_warns`
- `test_discouraged_with_reason_override_passes`

**驗收**:hold 段塞 forbidden role → blocking;discouraged + reason → pass。

---

## Part 3 — 硬邊界(不准做)

1. **不要把 Remotion API / component 字典餵進 video agent。** Remotion 編目只進
   `effect_backend_conformance.json`(W2-B)與 `remotion_effects.py` adapter,邊界後、版本化。
2. **不要把 backend-specific 欄位**(component/props/fps/durationFrames/springConfig)
   放進 `effect_intent` 或任何意圖層 artifact——`effect_contract.py` 會 raise,別繞過。
3. **不要動 canonical render path**:final renderer 仍是 ffmpeg `contract-run`;
   W1–W5 全是 spec/gate/verification 層,**不得改變 render 輸出**。
4. **不要讓 effect asset 滿足 material need**:`must_not_satisfy_material_need=true` 不可放寬。
5. **不要重蓋 Part 1 既有模組**;W 全部是擴充或新增 sibling 檔。
6. **未 review 的 Remotion / Workbench 產物不得進正式合成**(權威線)。
7. spec 層 blocking → **回 SPEC 改意圖/合約**,不要為了過閘去改檢查工具。

---

## Part 4 — 驗收與測試

- 全測試基準:`python -m unittest discover -s tests`(施工前先記基準數,W 只增不減 green)。
- 新測試模組(全部要從 red→green):
  `tests/test_effect_render_verification.py`(W5)、
  `tests/test_delivery_gate_effect_severity.py`(W1)、
  `tests/test_effect_conformance.py`(W2)、
  `tests/test_effect_perfunctory.py`(W3)、
  `tests/test_effect_role_policy.py`(W4)。
- 端到端煙霧(沿用既有 dry-run,不 render):
  `python video_tools.py effect-intent-plan <director_shot_plan.json> --out-plan effect_intent_plan.json --out-spec effect_asset_spec.json`
  → conformance(W2) → perfunctory(W3) → role-policy(W4) → 都 pass 才 BUILD。
- delivery 驗收:`evaluate_complete_video_delivery(run)` 對「required 渲不出」回 blocking、
  對「decorative fallback」只回 warning。

**完成定義(DoD):** W1–W5 全測試 green;`effect_capability_vocab.json` 每 token 有 backend 認領
(對稱測試 green);圈 1 渲不出真的擋交付、圈 2 fallback 不擋;且 `python -m unittest discover -s tests`
總 green 數不低於施工前基準。

---

## 附:資料流總圖

```
director_shot_plan.json (beat.effect_intent)
  └─ effect-intent-plan ─→ effect_intent_plan.json + effect_asset_spec.json   [FX1 既有]
        ├─ W2 conformance  ─→ effect_conformance_report   (unrenderable_required_intent → blocking, 回 SPEC)
        ├─ W3 perfunctory  ─→ (perfunctory_effect_intent → blocking, 回 SPEC)
        └─ W4 role policy   ─→ (effect_role_forbidden_for_section → blocking, 回 SPEC)
                 │ 全 pass
                 ▼
  build_light_effects_plan(contract, profile, effect_intent_plan)             [FX2 既有, 兩表徵已 join]
        └─ light_effects_manifest + baseline_review(gaps)                     [FX2 既有]
                 │ gaps
                 ▼
  effect-revision-request → remotion-prompt-pack → (draft, 非 canonical)      [FX3 既有]
                 │ rendered (ffmpeg contract-run, canonical)
                 ▼
  W5 build_effect_render_verification → effect_render_verification.json
                 ▼
  W1 evaluate_complete_video_delivery
        圈1 required 渲不出 → blocking ; 圈2 decorative fallback → warning
```
