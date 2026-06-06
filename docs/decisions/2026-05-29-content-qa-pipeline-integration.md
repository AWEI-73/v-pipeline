# Decision: Integrate content_qa.py into pipeline() as mandatory step

Date: 2026-05-29
Status: verified
Scope: video_pipeline.py / video_pipeline_core.content_qa
Superpowers phase: execute

## 2026-06-05 Amendment: Package Module Entrypoint

`content_qa.py` no longer lives as a root-level runtime script. The canonical
runtime implementation is:

```text
video_pipeline_core/content_qa.py
```

`video_pipeline.py` must invoke it as a package module:

```text
python3 -m video_pipeline_core.content_qa <outdir> --model <model> --weight <weight>
```

The route/build contract is unchanged: `content_qa.json` and the injected
`content_alignment` dimension remain VERIFY artifacts. This amendment only
aligns the subprocess entrypoint with the package reorganization.

## SPEC

Requirement:
`content_qa.py` 原本是手動跑的獨立腳本。retry loop 需要依賴 content_alignment 分數判斷哪些 segment 要重選，必須在 pipeline 內自動執行。

Why:
P2-3 retry loop 的 `collect_fix_actions()` 讀 `content_qa.json` 取 `score<60` 的段落來決定要 repick 哪些 segment。若 content_qa 不在 pipeline 內，retry loop 無法工作。

Direction:
- 步驟順序從 `merge-final → verify → thumbnails` 改為 `merge-final → thumbnails → verify → content_qa`
- thumbnails（`final_frame_*.jpg`）必須在 content_qa 之前產生（content_qa 讀 frames）
- 新增 `run_content_qa(outdir, model, weight, verbose)` 以 subprocess 呼叫 content_qa.py
- 權威 pass/fail 改從 content_qa 更新後的 `qa_report.json` 讀取（content_alignment 注入 + 重算加權分）

Non-goals:
- 不修改 content_qa.py 本身（保持獨立可手動跑）
- 不做 content_alignment 評分準則修訂（deferred D3）

## DO

Files / modules:
- `video_pipeline.py`: 新增 `CONTENT_QA` 常數、`run_content_qa()` 函式；`compose_and_qa()` 內步驟重排並加 step [11] content_qa

Function-level plan:
- `run_content_qa(outdir, model, weight, verbose)`: subprocess.run content_qa.py，解析 stdout 最後一行 JSON 回傳 summary
- `compose_and_qa()`: thumbnails 移至 verify 之前（step [9]），content_qa 在 verify 之後（step [11]），最後重讀 qa_report.json 作為權威回傳

Data / interface changes:
- `qa_report.json` 新增 `content_alignment` 維度（由 content_qa.py 注入），其他 5 維度權重重算為 0.70 總和
- 新增 CLI 參數 `--content-qa-weight`（default 0.30）

Migration / compatibility:
- 舊跑法：`verify` 回傳直接用。新跑法：verify 後再跑 content_qa，最終 pass/fail 以 content_qa 更新後的 qa_report 為準
- `--no-retry` 仍可關閉 retry，但 content_qa 永遠執行（是 pipeline 的一部分，不是 retry 的一部分）

## VERIFY

Pre-checks:
- `python3 -c "import ast; ast.parse(open('video_pipeline.py').read())"` → OK

Tests:
- `python3 -c "import video_pipeline as vp; assert hasattr(vp, 'run_content_qa')"` → OK

Manual checks:
- 跑 nightmarket e2e：`qa_report.json` 含 `content_alignment` 維度 weight=0.30 ✅
- `decision_log.json` 的 `attempt0.content_alignment.avg` 正確填入 ✅
- 分數對照 `qa_run_4b.log`（手動跑 4b avg=88.2）→ pipeline 整合後 avg=84.5（同 4b 模型，分數略降因 seg 組成不同）✅

Regression risks:
- thumbnails 編號從 `final_frame_1.jpg` 改為用 `segment` id 命名（`final_frame_{n}.jpg`）—— content_qa.py 讀 `final_frame_{n}.jpg`，需確認一致

## Decision Notes

Accepted because:
content_qa 是整個 QA 系統的關鍵維度（weight 0.30），整合進 pipeline 是必要前提。subprocess 呼叫讓 content_qa.py 保持獨立可測。

Tradeoffs:
- 每次跑 pipeline 都跑 content_qa（11 段 × 3 VLM prompts = 33 次 VLM 呼叫），約增加 3-5 分鐘
- 但這是唯一能讓 retry loop 自動決策的方式

Open questions:
- D3：評分準則（primary=100/related=60/somewhat=40/no=10）是否需要修訂？（留後）
- D1：單段 gate 取代平均稀釋？（留後）

## Git / Retrieval

Related files:
- `video_pipeline.py`: `run_content_qa()`, `compose_and_qa()`, `CONTENT_QA`
- `content_qa.py`: 不改，以 subprocess 呼叫

Related commits:
- `add33d1` (init commit, 含此實作)

Graphify anchors:
- Community 1 "Content QA & Retry Decisions"
- Node: `content_alignment QA dimension`
- Node: `run_content_qa()` (god node 連結 compose_and_qa)

Search tags: decision-log, content-qa, pipeline-integration, video-pipeline-v2, p2-3-prerequisite
