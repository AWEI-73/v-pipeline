# Decision: Handoff hub co-location + git init

Date: 2026-05-29
Status: verified
Scope: ~/video_pipeline/ (repository structure)
Superpowers phase: execute

## SPEC

Requirement:
任何 agent（不限特定 harness）指向 `~/video_pipeline/` 就能接續這個 workflow，不依賴 session memory 或特定工具鏈。

Why:
原本設計文件散落在：`~/.hermes/profiles/video_director/`（skills/vault/workspace）、`~/video_pipeline/`（程式碼）、`C:\Users\user\vaults\hermes-video-graph\`（舊圖譜）。無統一進入點，跨 session/harness 困難。

Direction:
- `~/video_pipeline/` 作為 canonical handoff hub，co-locate 所有設計工件
- 從各 profile/vault 複製 snapshot（不移除 canonical source，video_tools.py/skills/design 仍以 profile 為主）
- git init，.gitignore 排除所有 run-output 媒體（.mp4/.wav/.jpg）、logs、per-run JSON
- graphify-out/ co-located，graph 從設計檔 staging 建（排除 127 個媒體檔），輸出放回 graphify-out/
- HANDOFF.md 作為進入點（讀取順序 + 跑法 + 刷新圖譜說明）
- roadmap.md 作為狀態錨（v2 完成狀態 + deferred D1/D2/D3）

Non-goals:
- 不推到遠端（local git only，無 GitHub/GitLab）
- 不移除 ~/.hermes/profiles/video_director/ 的 canonical source
- 不追蹤 nightmarket 的媒體/run-output（.gitignore 擋掉）

## DO

Files / modules:
- `~/video_pipeline/` 新增：`HANDOFF.md`, `roadmap.md`, `video_tools.py`（snapshot）, `skills/*.md`（10 個 snapshot）, `design/*.md`（5 個 snapshot）, `docs/decisions/`（本次 3 個決策）, `graphify-out/`（graph.json/html/GRAPH_REPORT.md）
- `~/video_pipeline/.gitignore`：排除 *.mp4/wav/jpg/jpeg/png/heic/mp3、*.log、nightmarket/ 的 per-run JSON、coffee_v2/、__pycache__/

Graphify corpus（22 設計檔，不含媒體）staging → 輸出到 graphify-out/：
- 189 nodes, 369 edges, 14 communities
- 從 Windows miniconda graphify（WSL 無安裝）跑，輸出複製回 WSL

## VERIFY

Pre-checks:
- `git status` → 28 files staged, 0 media/logs ✅

Tests:
- `git log --oneline` → 1 commit `add33d1` ✅
- `ls ~/video_pipeline/skills/ | wc -l` → 10 ✅
- `ls ~/video_pipeline/graphify-out/` → GRAPH_REPORT.md graph.html graph.json ✅

Manual checks:
- `cat HANDOFF.md` → 讀取順序完整，跑法正確 ✅
- `cat roadmap.md` → 完成狀態 + deferred D1/D2/D3 正確 ✅

Regression risks:
- `video_tools.py` 是 snapshot，若 `~/.hermes/profiles/video_director/workspace/video_tools.py` 有改動，要手動同步（`cp workspace/video_tools.py ~/video_pipeline/video_tools.py && git commit`）
- skills/*.md 同上（snapshot，profile 改動需手動同步）

## Decision Notes

Accepted because:
co-location + git 是最輕量的跨 harness handoff 方案，不需要額外服務或 memory layer。任何能讀檔的 agent 都能用。

Tradeoffs:
- Snapshot 概念：`video_tools.py` / skills 以 profile 為 canonical，video_pipeline/ 是複製品 —— 有可能 drift。改動時需記得同步。
- graphify 只能從 Windows 跑（WSL 無安裝）—— 重建圖譜需要 Windows 環境

Open questions:
- 要不要加 git hook 在 commit 時自動同步 video_tools.py？（暫不做）
- 要不要加 remote origin 到 GitHub？（使用者決定）

## Git / Retrieval

Related files:
- `~/video_pipeline/.gitignore`
- `~/video_pipeline/HANDOFF.md`
- `~/video_pipeline/roadmap.md`
- `~/video_pipeline/graphify-out/GRAPH_REPORT.md`

Related commits:
- `add33d1` (init: hermes video_pipeline v2 — full handoff hub)

Graphify anchors:
- Node: `HANDOFF — Video Pipeline v2`（Community 1）
- Node: `graphify-out/GRAPH_REPORT.md`（Community 2 "Skill I/O Contracts & Workflow"）

Search tags: decision-log, handoff-hub, git-init, co-location, graphify-corpus, video-pipeline-v2, snapshot-pattern
