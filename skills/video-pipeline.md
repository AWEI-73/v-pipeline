---
name: video-pipeline
description: 影片製作／剪輯的唯一入口與強制驅動點。當使用者要求製作、剪輯、產生任何影片時——「幫我做／剪一支影片」「make a video / edit video / produce a video」「產生影片」「結訓影片 / MV / 宣傳片 / 活動回顧 / 教學片 / 旁白影片」——必須先呼叫本技能,再開始任何工作。它驅動 runtime.py 走完 SPEC→BUILD→VERIFY 節點鏈(每個 node 都有 verify gate),讀 state.json 的 next_action 派工,並分流到 director / writer / curator / editor / audio-director / effects-director / verify / dashboard 等角色技能。不要繞過本技能直接手動跑 ffmpeg 或自行拼接素材。
---

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

## 讀 next_action → 下一棒(路由表)

`runtime.py resume` 會自動處理大部分情況;需要人介入時它會清楚停下並印指引。

| next_action | 意義 / 你要做的 |
|---|---|
| `null` / `complete_review_final` | ✅ 收工:`final.mp4` 已 pass |
| `missing_artifact:<x>` | 對應 node 還沒產物 → 補該 node(見上表角色技能) |
| `await_material` | 等補拍素材:把 `seg{n}_user.*` 放進 project 的 `input/materials/` 再 resume |
| `wait_for_generated_provider` | 等外部生成素材交付 `materials/generated/seg{n}.*` 再 resume |
| `await_capcut_export` | 開 CapCut 匯出 `capcut_exported.mp4` 到 run 目錄,再 resume(僅 capcut backend) |
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
