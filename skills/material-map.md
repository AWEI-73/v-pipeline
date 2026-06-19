---
name: material-map
description: 素材地圖生命週期 Skill。把討論/現有素材/補拍需求收斂成 material_needs → 盤點 → delta → 人工決策 → revised contract → BUILD handoff。M6d orchestration 層,只定義方法與決策責任;確定性的 validate/join/gate/revision 一律交給 Python 工具。
---

# Material Map Lifecycle Skill

把「需求(劇本要什麼)」與「實際素材(手上有什麼)」對齊,並決定下一步:
盤點、補拍、縮短、改寫、刪段、等待,或交付 BUILD。

**核心心法**:這不是兩條互斥流程。`existing-material-first`、`script-first`、
`partial/hybrid` 只是不同入口;**目前 stage 由現存 artifact 決定**,不由你宣稱。
素材量決定劇本——缺素材就誠實輸出 delta / 補拍需求 / revision route,
**絕不默默用不符合 need 的素材**,也不為了宣稱成功而硬 BUILD。

## 唯一入口:lifecycle runner(不要手動拼工具)

```
python video_tools.py material-map-lifecycle --out-dir DIR \
  [--needs material_needs.json] \
  [--maps-dir DIR | --project-map project_material_map.json | --material-db materials_db.json] \
  [--contract segment_contract.json] \
  [--decisions revision_decisions.json] \
  [--categories material_categories.json]
```

它**只**做:嚴格解析當前 artifact → 呼叫 canonical 工具 → 判定 stage → 輸出
`material_map_lifecycle.json`(refs + 摘要的 projection,**不是第二套真相**)→
`build_ready` 時才產 BUILD handoff。它**從不** render、**從不**自己實作第二套
delta/gate/revision 規則、**從不**繞過 `run_contract` 的 M6b/M6c gate。

底層 canonical 真相來源(不可繞過、不可複製):
- required → `material_needs.json`(`validate-needs`)
- actual → per-asset `*.map.json` / `project_material_map.json`(`project-material-map`)
- diff → `material_delta.json`(`material-delta`)
- revision → `material_revision.json` + `revised_segment_contract.json`(`material-revision`)

## Stage 是怎麼判定的(每次 fresh 計算,不信任舊報告)

| stage | 意義 | 你該做什麼 |
|---|---|---|
| `await_requirements_discussion` | 有素材、無 needs | 對著盤點和使用者討論劇本,產 `material_needs.json` |
| `await_map_review` | 有 needs、有素材但尚未 review/連結(無 satisfies),或素材夠但缺 contract | 做 caption/agent review 把 scene 連到 need;或補上 contract |
| `await_material` | must_have 缺料且無合法 fallback | 產/交付 shooting brief,等補拍或既有素材交回 |
| `await_revision_decision` | delta 有缺口、需人工決定如何處理(或已有 decisions 但尚未 accepted) | 由導演/人工選 route 並 **accept** |
| `revision_blocked` | 已套用 accepted decisions 但仍有未解 tier-1 缺口 | 補 explicit waiver、補料,或改決策 |
| `build_ready` | 全部 covered 或 tier-1 缺口已被 canonical waiver 解除 | 交付 BUILD handoff |
| `invalid` | 輸入損壞 / dangling need / 重複 asset / 矛盾 | 修素材地圖或需求契約,**不得 BUILD** |

## 怎麼產 material_needs.json(從討論)

對話出每個「需求」的八件事(見 `shooting-brief` skill):拍什麼、幾個人、什麼動作、
場景、鏡位、時長、補哪一段、為什麼。每個 need 至少:`category / type / purpose /
count / must_have / fallback_tier`(可選 `fallback_options`)。寫好後一律先:

```
python video_tools.py validate-needs needs.json --migrate --out material_needs.json
```

`--migrate` 配發穩定 `need_id`(內容雜湊**初值**,一旦配發即永久;改用途不換 id)。
**不要**自己編 need_id,**不要**手改 join key。

## 三個入口的標準動作

- **只有素材**:`--maps-dir`/`--material-db` → runner 聚合 `project_material_map.json`、
  回報影片/照片/場景數與 caption 覆蓋率。**不要發明 requirements、不要跑 delta**。
  stage=`await_requirements_discussion`,然後你和使用者討論劇本。
- **只有劇本需求**:`--needs` → runner 產 `shooting_brief.json`;must_have 缺料時
  stage=`await_material`、`can_build=false`。把 brief 交給拍攝者,**不要硬 BUILD**。
- **partial/hybrid**:`--needs` + 部分 maps → runner 算 fresh delta。covered 可留;
  thin/missing/excess 留 evidence。有阻擋缺口 → `await_material`/`await_revision_decision`;
  全滿足或有 canonical waiver → `build_ready`。

## 人工決策(accepted decisions)怎麼用

`revision_decisions.json` 是**人/導演**明確接受的處理方式,M6c 只執行 `accepted`:

- `collect_material` / `reshoot`:不改劇本,維持阻擋,輸出 `await_material`。
- `dashboard_review`:不改劇本,輸出 `await_review`。
- `shorten_or_merge`:只縮短**指定 target_segment**(保留 need_refs)。
- `script_rewrite`:只套用決策內**明確提供**的 patch(**不得**由 agent 生成內容,
  不得改 segment identity / need_refs / need_id)。
- `drop_segment`:只刪指定 segment;**must_have / tier-1 需逐一帶 explicit waiver**
  (`reviewer + reason`),否則 fail。

每筆 decision:`decision_id`(唯一)、`need_id`(須在當前 delta)、`route`(須與該
delta outcome 相容)、`status: accepted|rejected`、視 route 帶 `target_segment` /
`patch` / `waiver`、`lineage{reviewer,reason,at}`(呼叫者提供,無隱藏時鐘)。

runner 套用後**重跑 `gate_from_delta`(帶 canonical waivers)**:通過才
`build_ready`。`rejected`/未 accept 的決策**不會**被套用。

## 何時可以交 BUILD,何時必須停

`build_ready` 是**有牙齒的**:只有以下全部成立才會出現,否則維持 await/invalid:

- **actual-side source 只能有一個**(`--project-map` / `--maps-dir` / `--material-db`
  三選一;同時給多個 → `invalid`,不靜默挑優先序)。
- **`--material-db` 是唯一可 BUILD 的來源**;`--maps-dir` / `--project-map` 只能盤點,
  即使算出 covered 也**不會** build_ready(避免「用 A 算 covered 卻交 B 給 BUILD」)。
- contract 通過 `spec_contract.validate_segment_contract`。
- contract 必須宣告 `material_needs_ref`,且 strict resolve(相對 contract 目錄)到
  **與 lifecycle 同一個** needs 檔;未宣告 / 指向不同 needs → `invalid`。
- 有 revision 時,contract 還必須宣告 `revision_decisions_ref` 綁定到同一份 decisions,
  讓 `run_contract` **重跑 M6c**、重新推導 waivers。
- handoff `{contract_ref, material_db_ref, material_needs_ref, revision_waivers,
  ready_for_build}` 的每個 ref 都必須是**真實存在**的檔案。

handoff `contract_ref` 一律指向**原 contract**(它綁定了 needs 與 decisions);
`run_contract` 收到後**重跑 fresh M6b/M6c gate**——無 revision 時直接過 gate;
有 revision 時重套 accepted decisions、重推 waivers、再過 gate,並 BUILD revised 結果。
`revised_segment_contract.json` 仍寫出,記在 `refs.revised_contract` 作為證據/預覽。
M6d **不繞過、不取代** runtime gate。(把 standalone revised contract + 外部 waiver
注入直接交 BUILD 的捷徑,留待 M6e。)
- **可以只完成一個階段就停**:只盤點、只產 brief、停在等料/等決策/等 revision 都算成功。
  **不得**為了宣稱成功而 BUILD/render 或硬湊 `final.mp4`。

## 何時必須回 `invalid`(fail-closed,交回 Python 工具判定)

needs 損壞 / dangling need_id / 重複 asset identity / 損壞的 map 或 DB /
stale/unknown decision need_id / revision 與 gate 矛盾 / revised contract 無效 /
handoff ref 不存在。這些都由 runner 確定性判定——**你不要自己 override 或猜測**。

## 與其他 Skill 的銜接
- 上游:`gap-analyzer`(產 needs 草稿)、`shooting-brief`(把 need 翻成拍攝任務)。
- 下游:`video-pipeline`(吃 build handoff,跑 SPEC→BUILD→VERIFY)。
- 真實案例端到端驗收(真渲 + 學員素材回放)= **M6e**,尚未完成。

---

## ISF1 Material-Map Handoff

Material-map 在 ISF1 裡只負責素材真相與 BUILD handoff，不負責寫故事、產圖、或接受 Workbench draft。

| 來源 | material-map 怎麼接 | 邊界 |
|---|---|---|
| `story-soul-blueprint` | 接 `material_needs.json` / director shot plan，驗證需求與素材覆蓋 | 不替故事補靈魂、不發明 need |
| 既有素材 | 接 per-asset map / `project_material_map.json` / `material_db.json` | 不移動 source file；folder 只是 projection |
| `generated-material-producer` | generated asset 回來後只成為 `candidate satisfies` evidence | 未 review 前不得當 covered |
| `storyboard_panel_locked=true` | comic/photo/storybook narration 要一個 panel 對一個 beat | 拉長 panel 或生成更多；不要用同 need 其他 panel 自動補滿 |
| Workbench | 讀 draft patch / contract patch 作 review 線索 | Workbench must not overwrite canonical needs/maps/delta/handoff |

回傳規則：

- 缺素材且允許生成 → `material-generation-fallback` / `generated-material-producer`。
- 缺素材但不能生成 → `await_material` 或 `revision_decisions.json`。
- 人工修剪 timeline → Workbench draft 交 agent review；若影響需求或素材身份，回 material-map / revision，不直接改 canonical。
- 可以 BUILD 只代表 material truth 通過；正式輸出仍必須由 `video-pipeline` / `contract-run` 重新 gate。
