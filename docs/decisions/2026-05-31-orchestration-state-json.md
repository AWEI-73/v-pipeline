# 編排層升級：state.json 作為單一真相（觀測優先遷移）

- 日期：2026-05-31
- 狀態：進行中（三步走第 1 步完成）
- 相關：roadmap.md「🧭 編排層升級」

## 背景

三層邊界已成形：**工具**（`video_tools.py` 子命令，純算無判斷）/ **skill 契約**
（`skills/*.md` 角色說明書，帶品味）/ **編排**（誰先誰後、失敗 route 給誰）。
前兩層成熟，但第三層「編排」目前寫死在 `video_pipeline.py` 的一條直線控制流裡：

- 不可恢復（中斷要從頭跑）、不可單段重跑（改一段重跑全部）。
- router 邏輯（`collect_fix_actions`）與領域知識耦合在主流程內。
- 執行真相散落在 `qa_report / content_qa / decision_log / effects_log /
  precompose_gate / picks` 六份檔案，沒有單一入口。

## 決策

把編排從「程式寫死」升級成「**state 驅動**」，分三步、節點慢慢改，
**每步都保持現有一條龍可跑**：

1. **（本次）定 `state.json` schema + 觀測優先寫出** — pipeline 末尾附帶
   `build_state()` 合成 `state.json`，**只觀測、不改控制流**，先驗證 schema 夠用。
2. `video_pipeline.py` 支援分段執行（`--stage` / `--only-seg` / `--resume`）。
3. 寫薄 route skill（`skills/route.md` + dispatcher）：讀 state → 派工 → 更新 state。

### 為何「觀測優先」

先讓 state.json 與既有控制流並存（純讀既有 artifact + 記憶體狀態合成），
零風險驗證 schema；確認夠用後，第 2/3 步才讓它「接管」決策。避免一次性重平台重工。

## state.json schema v1

```
schema_version, created_at, outdir, style, bgm, final, pass, attempts_used
qa: {score, content_alignment}
stages[]:   {name, status}            # tts→…→content_qa
segments[]: {segment, title, kind, source, layout, status, score,
             fix_target, block_reason?}
            # kind ∈ scored|title|local|collage|montage（與 content_qa 跳過邏輯一致）
            # status ∈ done|low|unfixable|needs_review
blocking[]: {segment, reason}         # 缺口（補拍指引）
next_action: await_material | retry:curator(seg=[…]) | needs_generated(seg=[…]) | review | null
```

關鍵語意：
- `script.json` = 要做什麼（spec）；`state.json` = 做到哪（執行進度，單一真相）。
- **`blocking` 優先於 `pass`**：帶缺口出片（pass=True 但某段仍用後備）時，
  `next_action` 仍給 `await_material`，讓編排層有可選的改進路徑。
- `build_state()` 失敗包在 try/except（non-fatal），不影響出片。
- `needs_generated(seg=[…])` 是 2026-06-01 後保留的 future route state：
  生成素材 provider（優先 Antigravity / assistant_imagegen；ComfyUI 目前 deprecated）
  成熟後，只交付標準 `source=generated`
  素材與 metadata，route 再用 `--only-seg` 接回主流程。當前 runtime 不強制產生此狀態。

## 實作

- `video_pipeline.py`：`STATE_SCHEMA_VERSION` / `_STAGE_NAMES` / `_seg_kind()` /
  `build_state()`；pipeline 末尾呼叫（effects_log 之後）。summary 回傳新增 `state` 路徑。
- 驗證：對既有 `journey_out` artifact 重建 state.json，逐段 status/score/blocking/
  next_action 正確（seg2 unfixable→await_material，montage/collage/title→done 不評分）。
- regression 114 passed。

## Step 2：`--only-seg` 定向重渲（2026-05-31）

`--only-seg N[,M]` 只重渲指定段（吃改過的 effects/layout/montage_n），其餘段用
`_rendered_path()`（鏡像 apply_effects 的 grade→title_card 鏈）沿用上一輪渲染檔，
再重組 concat/merge/QA。需先有完整 run（picks/candidates 快取）；自動關 retry。
假設 timeline（時長/style/轉場）不變——改旁白或重搜素材請跑完整流程。
實測：改 seg3（montage_n 5→4 + grade cool→fire + wipeleft），`--only-seg 3` 跑出
seg1/seg2 mtime 不變、僅 seg3 重渲、QA 100 pass。解掉「改一段要重跑全部」。

## Step 3：route skill（2026-05-31）

`route.py`（dispatcher）+ `skills/route.md`（契約）。router **在 pipeline 外**，
讀 `state.json.next_action` 派工，pipeline 維持單次確定性引擎：

| state | router |
|---|---|
| 無 state | 完整 build |
| `null` | 出片完成 |
| `await_material` | 偵測 `--material-dir/seg{n}_user.*`：到位→`source=local` + `--only-seg n`；未到位→印補拍指引等素材 |
| `needs_generated(seg=[…])` | future：等待外部 generated provider 交付 `materials/generated/seg{n}.*` + metadata，再以 `source=generated` 接回 |
| `retry:curator` / `review` | 交人工（router 不空轉；pipeline 內部 P2-3 已試過）|

端到端實證（學員素材接力）：journey seg2（背包 stock unfixable）→丟 `seg2_user.jpg`
→route 自動偵測→seg2 轉 local→`--only-seg 2`（seg1/3-13 全沿用）→round2 `null` 出片。
qa **92.2→97.0**、content_alignment **74→90**（unfixable 段轉可信 local 退出評分）。
這把「三源素材」的學員自有素材腿接進主流程。

## 三步總結

`build_state`(觀測) → `--only-seg`(分段執行) → `route.py`(state 驅動派工)。
編排從「程式寫死的一條龍」升級成「state 驅動、可恢復、可單段重跑、學員素材可接力」，
且每步都保持現有一條龍可跑。後續 `--stage`/`--resume` 跨階段續跑待需求出現再做。
