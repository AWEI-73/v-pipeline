---
name: route
description: 派工 Skill（編排層 dispatcher）。讀 state.json 的 next_action，決定下一棒叫誰：首輪完整 build、學員素材到位則該段轉 local 重渲、重試耗盡交人工、未來 generated provider 補洞。router 在 pipeline 外，pipeline 維持單次確定性引擎。
---

# Route Skill（派工 / 編排層）

> **Canonical-first runtime(see roadmap.md):公開 SPEC 輸入 = `segment_contract.json`。**
> legacy flat script 只是生成的 runtime payload,不可當 canonical。route 只讀產物狀態派工、
> 不重解釋創作意圖、保留 blockers/review gate、把修正送最小受影響節點(Light Route Contract 見 video-workflow.md)。

> ## Revision Loop / Change Request Contract(Node 14 — 小改不重啟 greenfield)
> 交付後的修改請求,**只動「最小受影響節點」**,不重跑整條規劃。`revision_plan`:
> `spec_delta`(改哪些 segment 合約欄位)+ `build_delta`(重選段/重渲哪些 item)+
> `verify_delta`(只重驗受影響範圍)+ `version`/rerender route(指到最小受影響節點 → 再 verify/render)。
> 例:只改某段字幕 → text_layer delta → 重渲該段(`--only-seg`)→ 局部 verify;不重做 brief/material-map。
> 與既有機制接點:`--only-seg`(局部重渲)+ `state.json` next_action + dashboard 覆寫即此迴圈的執行面。

把「誰先誰後、失敗 route 給誰」從寫死在 `video_pipeline.py` 的控制流，抽成
**讀 state→決定下一棒** 的外層迴圈。對應使用者最初描述的流程：
`route skill → state.json 偵測 → 驅動各 skill`。

這份 skill 是 **Video Route Skill Project** 的核心契約，目標是可被 Hermes、Claude
Code、Codex、或任何能讀 Markdown、跑 shell、讀 JSON 的 agent 平台使用。平台差異只能存在
RUNBOOK/runner shim，不應滲進 route 決策。

## 兩條正交的軸（先分清楚，route 邊界才切得乾淨）

系統有**兩種「分層」**，講的是不同東西，別混為一談：

**軸 A — 實作堆疊（東西怎麼疊起來的）**
- **工具**（`video_tools.py` 子命令）：純算、無判斷。
- **skill 契約**（`skills/*.md`）：帶品味的角色。
- **編排**（本 skill）：不懂剪片，只讀 `state.json` 派工。

**軸 B — 功能分層（每個角色在做哪一種事）** ⟨你問的這條⟩

| 功能層 | 在做什麼 | 哪些 skill / 角色 | 產物 |
|---|---|---|---|
| **SPEC** | 定義「要做什麼」 | 編劇（內容）、導演（製作設計）、video-workflow（高層規劃）、gap-analyzer / shooting-brief（缺口→補拍 brief）| `script.json` |
| **BUILD** | 把 spec「做出來」 | 小編（找素材）、剪輯師（組裝）、特效師（調色/轉場/字卡）、音控師（TTS+混音）、字幕師（SRT）、generative-director（外部生成素材）+ `video_pipeline.py` 確定性引擎 | `final.mp4` + artifacts |
| **VERIFY** | 檢查「做得對不對」 | VERIFY（5 維技術 QA→fix_target）、content_qa（content_alignment）、precompose_gate（規格/時長）| `qa_report.json` / `content_qa.json` |
| **稽核軌（貫穿三層）** | 記「做到哪 / 為何這樣決定」 | —（非 skill，是 artifact）| `state.json`（現況單一真相）+ `decision_log.json`（逐輪歷史）|

> 軸 A 的「編排」== route；它**跨**軸 B 的 SPEC/BUILD/VERIFY 移動工作。
> 軸 B 的稽核軌（state/decision_log）就是你說的 DECISION LOG layer——它是 VERIFY 的結論餵給 route 的**唯一介面**。

## route 在分層裡的位置：控制迴圈，不屬於任何功能層

route **不是** SPEC、不是 BUILD、不是 VERIFY 的一員。它是**架在三層之上的控制迴圈**：

```
SPEC ──► BUILD ──► VERIFY ──► (寫進 state.json / decision_log.json)
 ▲          ▲                          │
 └──────────┴──── route 讀 next_action 決定「回哪一層、跑哪幾段」◄┘
```

- route **只讀** VERIFY 沉澱到 `state.json` 的結論（`next_action`），**自己不做** SPEC/BUILD/VERIFY。
- route 決定的是「**回哪一功能層、對哪幾段、用 full 還是 `--only-seg`**」，然後叫確定性引擎跑。
- 領域知識留在各功能層；route 只認 `next_action` 的路由表（下節）。

## 單一真相：state.json
`script.json` = 要做什麼（spec）；`state.json` = 做到哪（執行進度）。
pipeline 末尾由 `build_state()` 寫出，關鍵欄位：

```
pass / qa{score, content_alignment}
stages[]    : tts…content_qa 各階段 status
segments[]  : {segment, kind, source, layout, status(done/low/blocked/unfixable/needs_review),
               score, fix_class(material|spec|human), fix_target, block_reason}
blocking[]  : {segment, reason}            # 補拍指引（unfixable + material build block）
gate_review : null | precompose gate 整片級失敗原因
next_action : null | await_material | retry:curator(seg=[…]) | revise:director(seg=[…])
              | needs_generated(seg=[…]) | review
```

**`fix_class`（VERIFY/state 已發出，2026-06-02）**：每段標 `material|spec|human`，這是讓 route
「回對的功能層」的依據——`material`→curator/await、`spec`→director、`human`→review。
其中 `blocked` 狀態 = 可恢復的 BUILD 失敗（出 placeholder 不炸片），`gate_review` = 整片級 gate 失敗。

## 派工規則（`route.py`）——每個 next_action = 回哪一功能層

| state | router 動作 | 回到哪一層 |
|---|---|---|
| 無 state | 完整 build（首輪）：`run_with_ollama.sh script --out OUT` | SPEC→BUILD→VERIFY 全跑 |
| `next_action == null` | ✅ 完成，出片 | — 收工 |
| `await_material` | 偵測 `--material-dir` 內 `seg{n}_user.*`：**到位**→該段 `source=local` + `--only-seg n` 重渲；**未到位**→印補拍指引、停下等素材 | 暫停 → 回 BUILD（素材換源後只重渲該段）|
| `retry:curator(seg=[…])` | pipeline 內部重試已用盡仍未達標 → 交人工換源/補拍 | BUILD 已用盡 → 升級人工 |
| `needs_generated(seg=[…])` | 等外部生成素材專案輸出 `materials/generated/seg{n}.*` + metadata，再以 `source=generated` 只重渲該段 | 暫停 → 回 BUILD（外部 provider 供料後）|
| `review` | 交人工 | 升級人工（含潛在 SPEC 改寫，見下）|

關鍵：router **在 pipeline 外**（軸 A 編排層），每輪只讀 state→決定回哪一功能層、跑哪幾段
（full 或 `--only-seg`）；pipeline 內部的自省重試（P2-3）是 **BUILD 層的微迴圈**，route 是**跨層的巨迴圈**——兩個迴圈尺度不同、不打架。

### ⚠️ 目前的缺角：route 只會回 BUILD，不會回 SPEC

現有 `next_action` 全是「回 BUILD（重渲/換源）」或「升級人工」。**沒有一條路徑會自動回 SPEC**
（叫編劇/導演改寫 `script.json`）。例如 content_alignment 一直低分，根因可能是導演選錯 `media_pref`/`layout`、
或編劇 `visual_desc` 寫歪——這類 **SPEC-level 修正目前一律落進 `review` 交人工**。

**進度（2026-06-02）**：VERIFY/`build_state` 現已**發出** `fix_class` 三分類與 `revise:director(seg=[…])`
next_action；缺的只剩 **`route.py` 消費這條**（偵測 `revise:director`→回導演重填製作欄位→`--only-seg` 重渲）。

| fix 類別 | 根因在 | next_action（state 已發）| route.py 消費 |
|---|---|---|---|
| **material** | BUILD 找錯/沒素材 | `retry:curator` / `await_material` / `needs_generated` | ✅ 已有（await_material）|
| **spec** | SPEC 媒材/版面/畫面描述選錯 | `revise:director(seg=[…])` | ⬜ 待補 |
| **human** | 都不是、需判斷 | `review` | ✅ 已有 |

## 用法

```bash
# 首輪 + 自動續跑（學員素材到位就自動接力重渲那段）
python3 route.py journey/script.json --out journey_out \
  --material-dir ~/student_uploads --verbose
```

學員把補拍檔丟進 `--material-dir`（命名 `seg2_user.jpg` / `seg2_user.mp4`），
再跑一次 route.py，它會自動把該段轉 local、只重渲那段、重組出片。

## 與「三源素材」的銜接
這正是「學員自有素材」接進主流程的那條腿：
- stock 找不到的台灣專有實體（胡椒餅/刈包）→ `await_material` + 補拍指引。
- 學員上傳 → router 偵測 → `source=local` 重渲 → 紀實主體歸位。
- 之後接生成式（Antigravity / assistant_imagegen / Codex 圖像等 provider）也走同一個 material source contract；route 只接收 `source=generated` 的成品素材。

### Material Source Contract（路由只認這層）

```json
{
  "segment": 6,
  "source": "stock | local | generated",
  "provider": "pexels | pixabay | user_upload | antigravity | assistant_imagegen | codex_imagegen | gemini_veo | manual",
  "file": "/absolute/path/to/material",
  "status": "candidate | selected | rejected | needs_review",
  "score": 0.0,
  "metadata": {}
}
```

生成 provider 由另一個 agent/project 獨立維護。不要把 provider installer、client、
workflow JSON、模型檔混進 route skill core。生成端只需交付：

```text
materials/generated/seg6.jpg
materials/generated/seg6.json
```

route 再把該段視為 `source=generated`，用 `--only-seg 6` 接回主流程。

### 全候選被 VLM reject 的長期政策

目前 runtime 仍可能在所有候選都被 VLM reject 後使用 top text-score fallback。這是 legacy 容錯，
不是 route skill project 的目標契約。QA hardening 之後應改成：

| 條件 | route 結果 |
|---|---|
| 期待學員/使用者素材 | `await_material` |
| 在地專有、stock ceiling 明顯 | 先 `await_material`，若 generated provider 已配置則 `needs_generated(seg=[…])` |
| generated 素材已交付 | `source=generated` + `--only-seg n` |
| 沒有更好來源 | `review` |

## 邊界（不做）——用分層講

- **不踩 SPEC**：router 不寫/不改 `script.json`（不重寫旁白、不選 media_pref/layout、不定 style）。那是編劇/導演的事；要改 spec 目前走 `review` 交人工。
- **不踩 BUILD**：router 不挑單一素材、不調色、不混音、不渲染。它只**叫**確定性引擎跑（full 或 `--only-seg`），怎麼做是 BUILD 各 skill + pipeline 的事。
- **不踩 VERIFY**：router 不評分、不判對題。它只**讀** VERIFY 沉澱到 `state.json` 的結論。
- **不改 timeline**：時長/段序/style 一變就要完整 build，不是 route 的 `--only-seg` 能處理的。
- **不碰外部 provider 本體**：不安裝/不啟動/不管理 Antigravity / assistant_imagegen / ComfyUI 等外部工具；generated 只是外部輸入源（交付 `materials/generated/segN.*`）。ComfyUI 預設 deprecated/disabled，除非使用者明確要求實驗。
- 自動接力只處理 `await_material`；`retry:curator` 耗盡、`needs_generated` 未供料、`review` 一律停下交人工。

## route 的姊妹：dashboard（同一條稽核軌的兩種出口）

`state.json` 是單一真相，有**兩個讀者**，都不屬於 SPEC/BUILD/VERIFY：
- **route**：機器讀者——讀 `next_action` → 自動派工（能自動的就自動）。
- **dashboard** [dashboard.md](dashboard.md)：人類讀者——把同一份 state 可視化（stage、低分段、素材來源、`next_action`、補素材指令、候選縮圖），給人在迴圈 review。

兩者都**只讀** state、都**不產**內容；差別只是「自動續跑」vs「給人看了再決定」。`decision_log.json` 則是兩者背後的歷史稽核（為什麼每輪這樣決定）。
