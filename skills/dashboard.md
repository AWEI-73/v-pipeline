---
name: dashboard
description: Pipeline 監控 / review Dashboard。讀 route state.json 與 artifacts，瀏覽器即時顯示 stages、VERIFY 分數、低分段、素材來源、next_action 與 route 建議。auto-refresh 5s。
---

# Dashboard Skill

## Tool Contract

<!-- TOOL_CONTRACT_START -->
{
  "version": 1,
  "skill": "dashboard",
  "stage_owner": "dashboard_workbench_review_surface",
  "triggers": [
    "使用者要開 dashboard、檢查前端、查看 Workbench、或驗證 UI 是否讀到 artifacts",
    "需要以瀏覽器檢查 dashboard/workbench 狀態"
  ],
  "canonical_tools": [
    {
      "tool": "tools/dashboard_server.py",
      "when": "啟動 dashboard review surface",
      "inputs": [
        "repo root",
        "optional run root"
      ],
      "outputs": [
        "local dashboard URL"
      ],
      "stop_if": [
        "server fails to bind or dashboard state cannot load"
      ],
      "capability_id": "cap.dashboard.dashboard-server.v1",
      "execution_class": "deterministic",
      "capability_role": "review",
      "loops": [
        "L0",
        "L5"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/workbench_server.py",
      "when": "啟動 Workbench review/edit surface",
      "inputs": [
        "repo root",
        "optional run root"
      ],
      "outputs": [
        "local workbench URL"
      ],
      "stop_if": [
        "server fails to bind or workbench state cannot load"
      ],
      "capability_id": "cap.dashboard.workbench-server.v1",
      "execution_class": "deterministic",
      "capability_role": "review",
      "loops": [
        "L0",
        "L5"
      ],
      "maturity": "experimental"
    }
  ],
  "supporting_tools": [
    {
      "tool": "tools/api_surface_manifest.py",
      "when": "審計與盤點 API Surface Manifest 限制與健康度",
      "inputs": [
        "registry json path"
      ],
      "outputs": [
        "manifest JSON or audit report"
      ],
      "stop_if": [
        "audit fails rules or branch not match"
      ]
    },
    {
      "tool": "tools/workbench_frontend_smoke.py",
      "when": "用瀏覽器或前端 smoke 檢查 Workbench UI",
      "inputs": [
        "workbench URL or local server"
      ],
      "outputs": [
        "frontend smoke report"
      ],
      "stop_if": [
        "browser check fails"
      ]
    },
    {
      "tool": "tools/workbench_proxy.py",
      "when": "代理 Workbench 讀取本機素材或 run artifacts",
      "inputs": [
        "repo root",
        "request path"
      ],
      "outputs": [
        "proxied artifact or media response"
      ],
      "stop_if": [
        "path escapes allowed workspace"
      ]
    }
  ],
  "forbidden_tools": [
    "Dashboard must not silently rewrite canonical artifacts",
    "Workbench UI drafts must return through review before canonical promotion",
    "Do not use UI visibility as proof that delivery gates passed"
  ],
  "capability_namespace": "cap.dashboard.*",
  "capability_lookup_owner": "dashboard"
}
<!-- TOOL_CONTRACT_END -->

> ## AI Editor Review / Override Surface(Node 11 — AI 為主、人為輔)
> **AI editor 是主控,human-in-the-loop 是選配且 targeted。** AI editor 讀 assembly_plan +
> timeline_build + validation findings → 產 `editor_review`:`decision ∈ approve / auto_fix /
> route_change / human_review / block / rerender` + reason + 指向的 next_node(12/10/9/8)。
> dashboard 是這個 review/控制面的呈現 + **人類覆寫接點**(node-timeline 上點選改選段/補開場收尾/
> 補必放;目前唯讀呈現,互動編輯待 schema 定後做)。
> 與 verify 分工:**editor 提案修法/路由;verify 給正式 pass/fail 閘**(Node 12)。canonical = JSON。

不是「全新 Skill」，是把整條 pipeline 視覺化的工具。  
跑長時間 pipeline 時，看 dashboard 比 tail terminal 直觀。

在 Video Route Skill Project 裡，dashboard 的定位是 **human/agent review surface**：
它讀 `state.json` 和既有 artifacts，幫人決定下一步，但不成為真相來源。

---

## 工具位置

```
/home/lio730309/.hermes/profiles/video_director/workspace/video_tools.py
/home/lio730309/.hermes/profiles/video_director/workspace/dashboard.html
```

兩個指令：
```bash
python3 video_tools.py state <workdir> [--project NAME]
python3 video_tools.py serve <workdir> [--port 8765]
```

---

## 對應命令
* `[[cmd_state]]` - 掃描 workdir 並產出 state.json 供監控 Dashboard 使用。
* `[[cmd_serve]]` - 啟動本地 HTTP 伺服器服務 dashboard.html 以及工作區檔案，並自動更新 state.json。

---

---

## 使用流程

```bash
# 1. 跑你的 pipeline（任何 Skill 組合都行）
bash /tmp/skill_test/full_auto_pipeline.sh

# 2. 啟動 dashboard server（會自動複製 dashboard.html + 跑 state）
python3 video_tools.py serve /tmp/skill_test/full_auto --port 8765

# 3. 瀏覽器打開
http://localhost:8765/dashboard.html
```

頁面每 5 秒自動 fetch `state.json` 刷新。Pipeline 還在跑時，新的檔案出現會即時亮綠。

---

## Route State Dashboard ✅ 已實作（2026-06-02）

`dashboard.html`（repo 根目錄）現在直接讀 **route `state.json` schema**：頂部 route banner（`next_action` 色碼 + copy-paste 指令）、stages、QA（加權分 + content_alignment + 巢狀 6 維度）、segments 表（status/score/`fix_class→fix_target`/block_reason 色碼）、blocking 補拍清單、final 連結。auto-refresh 5s。`cmd_state` 已會保留 route state 並把舊檔案掃描資料巢狀在 `state.dashboard` 下（QA 維度從那裡取）。

兩種看法：

```bash
# A) self-contained 快照（推薦給「直接開檔」工作流，免 server）
python3 video_tools.py dashboard <outdir>      # 產 <outdir>/dashboard_view.html（state 內嵌）
#    → 直接用瀏覽器開該檔即可（含 \\wsl.localhost\... file://），無需任何 server

# B) live server（要 auto-refresh 5s 時用）
python3 video_tools.py serve <outdir> --port 8765   # → http://localhost:8765/dashboard.html
```

⚠️ **`dashboard.html` 直接用 file:// 開會「讀不到」**——因為瀏覽器禁止 file:// fetch 同目錄 `state.json`。
所以「直接開檔」一定要用 `dashboard`（內嵌資料）那支；`serve` 那支才是給 http 用的。

Dashboard 顯示的 route review 訊號：

| 區塊 | 內容 |
|---|---|
| Project summary | project/outdir/final video/updated |
| Stages | `stages[]` 的 done/pending/error |
| QA | total score、content_alignment、各 QA dimensions |
| Segments | segment/title/source/layout/status/score/fix_target |
| Material source | `stock | local | generated`、provider、file |
| Route | `next_action`、blocking、建議 command |
| Review assets | final frame、candidate thumbs、low segment frame |

### `next_action` 顯示規則

| `next_action` | Dashboard 顯示 |
|---|---|
| `null` | 完成，可下載/檢查 final |
| `await_material` | 列出 blocking segments、補素材命名規則、`route.py --material-dir ...` |
| `retry:curator(seg=[...])` | 列出低分段，建議人工換 query/source |
| `revise:director(seg=[...])` | SPEC 選錯（layout/media_pref/bgm）→ 建議導演重填 + `--only-seg N` |
| `needs_generated(seg=[...])` | 列出需要 generated provider 的段落與 expected output path |
| `review` | 顯示人工 review checklist |

### 建議 command

Dashboard 可以產生 copy-paste 指令，但不要自動執行：

```bash
python3 route.py <script.json> --out <OUT> --material-dir <DIR> --verbose
bash run_with_ollama.sh <script.json> --out <OUT> --only-seg 6 --verbose
```

---

## state 指令（舊 dashboard 模式）

```bash
python3 video_tools.py state /tmp/skill_test/running_run \
  --project "跑步主題-運動科學" \
  --out /tmp/skill_test/running_run/state.json
```

掃 `workdir` 找以下檔案（fnmatch 模糊比對）：

| 節點 | 找什麼 |
|------|--------|
| writer | `*script*.json` |
| audio | `tts_timing.json` + `final_audio.wav`/`voice.mp3` |
| subtitle | `*.srt` |
| curator | `clip_list.json` |
| editor | `rough_cut.mp4` + `rough_cut_edit_log.json` |
| final | `*final*.mp4`（排除 rough_cut）|
| verify | `qa_report.json` |

存在就 `status: done`，不存在 `status: pending`。  
每節點附 timestamp + 摘要（segment 數 / 時長 / drift 等）。

### 輸出 state.json 結構
```json
{
  "project": "跑步主題-運動科學",
  "workdir": "/tmp/skill_test/running_run",
  "updated": "2026-05-25T21:23:20",
  "nodes": {
    "writer":   { "status": "done", "ts": "21:21:26", "summary": "4 segments" },
    "audio":    { "status": "done", "ts": "20:40:25", "summary": "79.8s, 25 phrases" },
    ...
    "verify":   { "status": "done", "ts": "20:53:35", "summary": "score 100.0 ✅" }
  },
  "files": { "script": "...", "tts_timing": "...", ... },
  "qa": { 完整 qa_report.json 內容 }
}
```

---

## serve 指令

```bash
python3 video_tools.py serve /tmp/skill_test/running_run --port 8765
```

做的事：
1. 把 `dashboard.html` 從 workspace 複製到 workdir（如果還沒有）
2. 跑一次 `state`，產出 `state.json`
3. 啟動 `python -m http.server` 在指定 port 服務 workdir
4. 印出網址，使用者貼到瀏覽器

純本機 HTTP，沒有 CORS、沒有 auth、不對外開放。  
Ctrl+C 關閉。

---

## Dashboard 視覺結構

```
🎬 Video Director Pipeline          [project name] [updated] [auto 5s]
─────────────────────────────────────────────────────────────────────
[編劇] [音控] [字幕] [小編] [剪輯] [成片] [VERIFY]
  ✅     ✅     ✅     ✅     ✅     ✅      ✅
  4seg  80s   25ph  4clip 80s  80s  100.0
─────────────────────────────────────────────────────────────────────
┌─ VERIFY 加權總分 ─────────────────────────────────┐
│  100.0    ✅ PASS (threshold 80)                  │
│                                                   │
│  ┌─ 5 維度 ────────────────────────────────┐      │
│  │ script_coverage  100  duration_fit  100│      │
│  │ subtitle_accuracy 100  audio_levels 100│      │
│  │ technical_quality 100                  │      │
│  └────────────────────────────────────────┘      │
└───────────────────────────────────────────────────┘
─────────────────────────────────────────────────────────────────────
📁 Files Produced
  📜 script.json         workspace/script_running.json
  🎙 tts_timing.json     audio/tts_timing.json
  ...
```

### 節點顏色
- ✅ 綠 = done
- 🔄 橘 (脈動) = running（state 暫未自動偵測 running，可手動標記）
- ❌ 紅 = error
- ⏳ 灰 = pending

### VERIFY 卡片
- pass 綠框 / fail 紅框
- 大字顯示總分
- 5 個維度小卡，分數依高/中/低不同顏色

---

## 已知限制

### state 不偵測 running
單靠檔案存在判斷只有 done / pending。要顯示「currently running」需要 Skill 在執行前後呼叫 state 寫入特殊欄位。  
**目前 workaround**：跑 pipeline 時自己看 terminal log。

### state 不偵測 error
檔案沒生出來只會顯示 pending，不會顯示 error。  
**目前 workaround**：看 terminal stderr。

### 沒有歷史紀錄
每次 state 都覆寫 state.json，過去的 VERIFY 分數比較不下來。  
**未來**：可加 `--archive` 把舊 state 存到 `history/`。

---

## 與其他 Skill 的銜接

不直接呼叫任何 Skill，只讀檔。所有 Skill 都不需要為 dashboard 改動。

---

## 對應的 vault 文件
- `projects/video-agent-pipeline/roadmap.md` Phase 7
- `projects/video-agent-pipeline/skill-interface-contracts.md` — pipeline_state.json 格式
