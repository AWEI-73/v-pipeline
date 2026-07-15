---
name: video-pipeline
description: 影片製作／剪輯的唯一入口與強制驅動點。當使用者要求製作、剪輯、產生任何影片時——「幫我做／剪一支影片」「make a video / edit video / produce a video」「產生影片」「結訓影片 / MV / 宣傳片 / 活動回顧 / 教學片 / 旁白影片」——必須先呼叫本技能,再開始任何工作。它驅動 runtime.py 走完 SPEC→BUILD→VERIFY 節點鏈(每個 node 都有 verify gate),讀 state.json 的 next_action 派工,並分流到 director / writer / curator / editor / audio-director / effects-director / verify / dashboard 等角色技能。不要繞過本技能直接手動跑 ffmpeg 或自行拼接素材。
---
Shared hard boundary: read `skills/pipeline-boundary.md`. Stage 0 entry lock
applies before runtime, BUILD, Workbench, Brownfield, effects, or render. Do not direct-cut from a fuzzy request.


# Video Pipeline — 影片製作的強制入口與編排驅動

這是「做／剪一支影片」的**唯一入口**。被要求製作或剪輯任何影片時,**先進這裡**,
不要直接手動跑 ffmpeg、也不要從隨機素材拼貼開始。本技能不自己剪片——它**驅動**
確定性引擎(`runtime.py`)走完節點鏈,並在每一步把工作派給對的角色技能。

> 三條鐵則:
> 1. **架構優先**:先收斂 SPEC,再 BUILD,最後 VERIFY。不要跳步。
> 2. **state 驅動**:`state.json` 是單一真相,`runtime.py` 讀它的 `next_action` 決定下一棒。
> 3. **每個 node 都有 verify gate**:不要靠感覺判斷「做完了」,看 gate 狀態。

---

## 開工前:一句話分流

| 使用者說的 | 你要做的第一件事 |
|---|---|
| 模糊需求(「幫我做個結訓影片」) | 進 `video-workflow` 技能做**互動式模糊消除**,收齊 brief 欄位 |
| 已有 `segment_contract.json` | 直接 `runtime.py run`,進 BUILD |
| 「為什麼卡住 / 現在到哪」 | `runtime.py status`,讀 next_action |
| 「改一下某段字幕／某段重剪」 | 走 Node 14 局部修正:`runtime.py rerun <node>`,別重跑整條 |
| 「先驗一下鏈接對不對(不要真 render)」 | `video_tools.py contract-dry-build`(離線,秒級) |

> **新專案第一步永遠是 `python video_tools.py project-init <name>`**(建立專案目錄+
> 修正 `.project/active.json` 指標)。跳過它直接 `runtime.py run` 會吃到舊的 active
> 指標(可能被測試污染指向 Temp)。輸入檔放 `<project>/input/`:segment_contract.json、
> brief.json、**editorial_design.json(靈魂政策,別漏)**、material_categories.json、
> materials_db.json。執行環境:**miniconda python(有 librosa)**,hermes venv 沒有。

---

## 節點鏈(SPEC → BUILD → VERIFY)與角色技能

執行順序定義在 `video_pipeline_core/node_registry.py` 的 `NODE_ORDER`。每個 node 都掛了
`verify_fn`,由 `dashboard_state.load_dashboard_state()` 自動評估 → 寫進 `state.json`。

| Node | 層 | 角色技能 | 產物 | verify gate |
|---|---|---|---|---|
| 0 | SPEC | `video-workflow` | `brief.json` | brief 存在 |
| 3 | SPEC | `spec-contract` / `director` | `segment_contract.json` | segments 已定義 |
| 2 | SPEC | `curator` / `gap-analyzer` | `material_coverage_map.json` | 覆蓋率(stock_first 可免) |
| 4-7 | SPEC facets | `writer` / `audio-director` / `effects-director` / `director` / `curator` | contract 6 facets | facets + reasons 齊全 |
| 5 | SPEC | `audio-director` | `music_structure.json` | 節拍分析完成 |
| 8 | route | `gap-analyzer` / `generative-director` | `build_profile.json` | profile 已定 / 等生成素材 |
| 9 | BUILD | `editor` | `assembly_plan.json` | 組裝計畫存在 |
| 10 | BUILD | `editor` | `timeline_build.json` | 每個 clip 有 trace |
| 11 | REVIEW | `editor` / `dashboard` | `editor_review.json` + 多項 audit | 決策 = approve |
| 13 | DELIVERY | `editor` | `final.mp4`(或 capcut draft) | 已 render |
| 12 | VERIFY | `verify` | `verify_result.json` + P1 audit pack | 技術 QA pass |
| 14 | ITER | `editor` / `verify` / `dashboard` | `revision_plan.json` | 只在 verify 失敗時 |

> 領域品味留在各角色技能;本技能只負責「現在該回哪一層、跑哪幾段、叫誰做」。

---

## 驅動方式:runtime.py(唯一 driver)

`runtime.py`(resume / status / rerun)是統一的 state 驅動執行器。
(舊的 `route.py` 已於 2026-06-10 退役,功能全部併入 runtime。)

```bash
# 首輪:建立 run 並從現有 artifact 接著跑
python runtime.py run --project <name> [--contract segment_contract.json] \
    [--brief brief.json] [--music bgm.mp3] [--material-db materials_db.json]

# 自動續跑:讀 state.json.next_action 派工,直到 next_action 為 null / 完成
python runtime.py resume --project <name>

# 觀測:逐 node 狀態 + next_action(看不懂 JSON 也能知道下一步)
python runtime.py status --project <name>

# 局部修正:清掉該 node 及其下游 artifact 後重跑(Node 14 小改不重啟)
python runtime.py rerun <node> --project <name>
```

**BUILD 前 SPEC 總體檢(spec_review gate,roadmap C0)** —— contract-run / dry-build
會自動先跑;也可單獨驗:

```bash
python video_tools.py spec-review <segment_contract.json> --brief brief.json
```

產出 `spec_review.json`:`ready_for_build` + `blocking[]`(SPEC 自相矛盾/會靜默掉內容,
route `revise:director`,**不進 BUILD**)+ `warnings[]`(能跑但品質會降級)。
規則全部來自真實事故(pacing 矛盾/must_include×stock/subtitle:auto 無人聲/
CG-bait query/缺 target_length/mode 推斷陷阱)——blocking 出現時**回 SPEC 改合約,
不要去修工具**。

**離線鏈接驗證(不 render、不下載、不碰網路)** —— 收斂期或交付前快速確認接線:

```bash
python video_tools.py contract-dry-build <segment_contract.json> --out-dir <run_dir>
```

它從 contract 直接物化 Node 8/9/10/11 的 BUILD artifact(build_profile / assembly_plan /
timeline_build / editor_review),`status` 會看到這幾個 node 變 `done`;Node 12/13 仍維持
`missing`(只有真 render 才能產生可驗證影片)——這是預期,不是錯誤。

---

## 視覺判讀:主責 agent 親眼看(agent-as-judge,2026-06-12 決策)

內容判讀(素材對不對題、選哪個窗)的正式裁判是**駕駛中的主責 agent**,不是內嵌
小模型:引擎在判讀點產出「場景中點+時間戳烙印」蒙太奇與 `visual_review_request.json`
後以 `await_visual_review` 暫停;你(或你派的 subagent)**親眼讀圖**、寫
`visual_review_verdict.json`、再 resume。這是正式 node 10.5(Visual Judge,
registry 內,`status` 看得到)。設計見
`docs/archive/decisions/2026-06-12-agent-as-visual-judge.md` 與 s4a/s4b 決策文件。

**verdict 格式(每個 clip 一筆,2026-06-12 S4b 起)**:

```json
{"segment": 2,
 "action": "accept | reject | needs_patch",
 "picked_windows": [{"start": 3.0, "end": 8.5}],
 "patch": {"type": "window | crop | treatment", "hint": {}},
 "reject_reason": null, "notes": "引用格上時間戳寫依據"}
```

- `accept` / `needs_patch` **必須給 picked_windows**(window patch 可只給
  `patch.hint.start/end`,引擎會代填);`reject` 給 `reject_reason`。
- `needs_patch` = 素材可用但要一個有界的確定性修正:`window`(換時間窗)、
  `crop`(`hint: {"x": 0..1, "y": 0..1}` 構圖重心)、`treatment`(`hint:
  {"mode": "slow_push"|...}` 照片動態)。它不是任意改圖的入口。
- 舊欄位 `accept: true/false`(boolean)仍相容,新 verdict 一律用 `action`。

已生效的部分:Node 12 的 `keyframe_grid.jpg`(已含時間戳烙印)**必須由主責 agent
親自讀過**才算完成複核——引用格上時間戳寫結論,不要只看 JSON 分數。
`build_profile.visual_judge: ollama` 為無人值守 autopilot 模式(4b gate + 救援機制)。

## 讀 next_action → 下一棒(路由表)

`runtime.py resume` 會自動處理大部分情況;需要人介入時它會清楚停下並印指引。

| next_action | 意義 / 你要做的 |
|---|---|
| `null` / `complete_review_final` | ✅ 收工:`final.mp4` 已 pass |
| `missing_artifact:<x>` | 對應 node 還沒產物 → 補該 node(見上表角色技能) |
| `await_material` | 等補拍素材:把 `seg{n}_user.*` 放進 project 的 `input/materials/` 再 resume |
| `wait_for_generated_provider` | 等外部生成素材交付 `materials/generated/seg{n}.*` 再 resume |
| `await_capcut_export` | 開 CapCut 匯出 `capcut_exported.mp4` 到 run 目錄,再 resume(僅 capcut backend) |
| `await_visual_review` | Node 10.5:親眼讀 run 目錄下的蒙太奇圖,寫 `visual_review_verdict.json`(格式見上節),再 resume |
| `await_material_visual_review` | `caption-meta --visual-review-dir DIR` 已產生長素材蒙太奇;親眼讀圖、寫 `material_visual_review_verdict.json`,再重跑同一指令 |
| `revise:director` | SPEC 層修正:編輯 `segment_contract.json` 的 layout/media_pref 等,再 resume |
| `retry:curator` | 內部重試已耗盡 → 換 search_query/source 或補本地檔,再 resume |
| `verify_failed` / `human_review` / `fix_timeline_or_assembly` | 看 findings,修最小受影響 node 再 resume |

---

## 邊界(本技能不做)

- **不手動跑 ffmpeg、不自行挑素材/調色/混音**:那是 BUILD 角色技能 + 確定性引擎的事;
  本技能只**叫** runtime 跑。
- **不重解釋創作意圖**:canonical SPEC = `segment_contract.json`;legacy flat script 只是
  生成的 runtime payload,不可當 SPEC。
- **不跳過 verify**:render candidate(Node 13)之後一定走 VERIFY(Node 12);沒 pass 不交付。
- **render backend**:ffmpeg 為 canonical 預設;CapCut 為可選收尾(GUI 匯出是人/CU 閘)。
- **特效**:`build_profile.render_profile` = no_effects / light_effects / motion_graphics;
  特效進階(Remotion/AE 級)屬 roadmap 後段,別在基本鏈未通前展開。

---

## 完成判準(交付前自我檢查)

```text
1. runtime.py status 顯示所有必要 node = done
2. final.mp4 存在,verify_result.json = pass
3. artifact_manifest.json 完整(含 backend 與 final 檔名)
4. next_action = null / complete_review_final
```

---

## ISF1 Interactive Skill Flow（流程固化，不是樣板固化）
> ISF1 UTF-8 anchor: 流程固化，不是樣板固化。
> 入口仍是 `video-pipeline`，模糊需求先交 `video-workflow` 釐清；
> 故事厚度交 `story-soul-blueprint`，素材真實性與缺口交 `material-map`，
> 缺素材才交 `generated-material-producer`。Workbench 只產 draft patch；
> 正式狀態仍以 `state.json` / backend route 為準。

這裡固化的是 agent 操作流程，不是固定故事模板、CI/CD、或單一範例。每次影片仍由互動式 skill 取得必要參數，再交給確定性工具驗證與 BUILD。

| Phase | Owner skill / tool | 必要產物 | 停止條件 | 下一步條件 |
|---|---|---|---|---|
| 0 Intake | `video-workflow` | `project_brief.json` 或等價 brief | 目的、受眾、片長、素材來源、fallback 還不清楚 | brief 欄位足以判斷 script-first / material-first / hybrid |
| 1 Story soul | `story-soul-blueprint` | `story_world.json`, `creative_concept.json`, `screenplay_beats.json`, `director_shot_plan.json` | 沒有核心命題、敘事裝置、情緒弧線 | 每個 beat 有 story function、畫面需求、素材數量估計 |
| 2 Material truth | `material-map` / M6 lifecycle | `material_needs.json`, `project_material_map.json`, `material_delta.json` | `await_material`, `await_map_review`, `revise:material(material_delta)` | delta 可解釋 covered/thin/missing 且可進 BUILD 或 revision |
| 3 Generated fallback | `material-generation-fallback`, `generated-material-producer` | `material_generation_fallback.json`, `generated_provider_packet.json`, reviewed generated map | `wait_for_generated_provider`, `await_material_visual_review` | provider 輸出已 import/review，fresh delta 重算 |
| 4 Contract / BUILD | `director`, `editor`, `audio-director`, `runtime.py` | `segment_contract.json`, `timeline_build.json`, render candidate | BUILD gate / material gate fail | candidate 影片可進 verify |
| 5 Human review / Workbench | Workbench + dashboard | `timeline_patch.json`, `patched_draft_timeline.json`, `workbench_contract_patch.json` | 人工 patch 還沒被 agent 判讀或同步 | patch 經 agent review 後回 contract/revision 或接受為 draft |
| 6 Verify / delivery | `verify`, dashboard | `verify_result.json`, `artifact_manifest.json`, `state.json` | `verify_failed`, `fix_timeline_or_assembly`, `human_review` | `state.json.next_action` 為 `null` 或 `complete_review_final` |

互動原則：

- 模糊需求先進 `video-workflow`，不要直接塞進 runtime。
- 有故事感需求先進 `story-soul-blueprint`，不要只列課程項目。
- 有素材/缺素材問題交給 `material-map`，不要讓 BUILD 偷拿不符合 need 的素材。
- 沒素材但允許生成時，走 generated provider packet；模型產物仍要回 material-map review。
- Workbench 只產 draft patch；正式片仍由 backend ffmpeg / `contract-run` 產生。
- 漫畫、照片故事、繪本、口白 panel 片要帶 `storyboard_panel_locked=true`；拉長 panel 或生成更多 panel，不用同 need 的其他圖自動補滿旁白。
