# Decision: Handoff hub co-location + git init

Date: 2026-05-29
Status: verified
Scope: ~/video_pipeline/ (repository structure)
Superpowers phase: execute

## SPEC

Requirement:
隞颱? agent嚗??摰?harness嚗???`~/video_pipeline/` 撠梯?亦???workflow嚗?靘陷 session memory ?摰極?琿???
Why:
?閮剛??辣???剁?`~/.hermes/profiles/video_director/`嚗kills/vault/workspace嚗~/video_pipeline/`嚗?撘Ⅳ嚗C:\Users\user\vaults\hermes-video-graph\`嚗???嚗蝯曹??脣暺?頝?session/harness ?圈??
Direction:
- `~/video_pipeline/` 雿 canonical handoff hub嚗o-locate ??身閮極隞?- 敺? profile/vault 銴ˊ snapshot嚗?蝘駁 canonical source嚗ideo_tools.py/skills/design 隞誑 profile ?箔蜓嚗?- git init嚗?gitignore ????run-output 慦?嚗?mp4/.wav/.jpg嚗ogs?er-run JSON
- graphify-out/ co-located嚗raph 敺身閮? staging 撱綽?? 127 ??擃?嚗?頛詨?曉? graphify-out/
- HANDOFF.md 雿?脣暺?霈??摨?+ 頝? + ?瑟??隤芣?嚗?- roadmap.md 雿??嚗2 摰????+ deferred D1/D2/D3嚗?
Non-goals:
- 銝?圈?蝡荔?local git only嚗 GitHub/GitLab嚗?- 銝宏??~/.hermes/profiles/video_director/ ??canonical source
- 銝蕭頩?nightmarket ??擃?run-output嚗?gitignore ??嚗?
## DO

Files / modules:
- `~/video_pipeline/` ?啣?嚗HANDOFF.md`, `roadmap.md`, `video_tools.py`嚗napshot嚗? `skills/*.md`嚗?0 ??snapshot嚗? `design/*.md`嚗? ??snapshot嚗? `docs/archive/decisions/`嚗甈?3 ?捱蝑?, `graphify-out/`嚗raph.json/html/GRAPH_REPORT.md嚗?- `~/video_pipeline/.gitignore`嚗???*.mp4/wav/jpg/jpeg/png/heic/mp3??.log?ightmarket/ ??per-run JSON?offee_v2/?_pycache__/

Graphify corpus嚗?2 閮剛?瑼?銝慦?嚗taging ??頛詨??graphify-out/嚗?- 189 nodes, 369 edges, 14 communities
- 敺?Windows miniconda graphify嚗SL ?∪?鋆?頝?頛詨銴ˊ??WSL

## VERIFY

Pre-checks:
- `git status` ??28 files staged, 0 media/logs ??
Tests:
- `git log --oneline` ??1 commit `add33d1` ??- `ls ~/video_pipeline/skills/ | wc -l` ??10 ??- `ls ~/video_pipeline/graphify-out/` ??GRAPH_REPORT.md graph.html graph.json ??
Manual checks:
- `cat HANDOFF.md` ??霈??摨??湛?頝?甇?Ⅱ ??- `cat roadmap.md` ??摰????+ deferred D1/D2/D3 甇?Ⅱ ??
Regression risks:
- `video_tools.py` ??snapshot嚗 `~/.hermes/profiles/video_director/workspace/video_tools.py` ???閬???甇伐?`cp workspace/video_tools.py ~/video_pipeline/video_tools.py && git commit`嚗?- skills/*.md ??嚗napshot嚗rofile ?孵?????郊嚗?
## Decision Notes

Accepted because:
co-location + git ?舀?頛??楊 harness handoff ?寞?嚗??閬?憭??? memory layer?遙雿霈瑼? agent ?質?具?
Tradeoffs:
- Snapshot 璁艙嚗video_tools.py` / skills 隞?profile ??canonical嚗ideo_pipeline/ ?航?鋆賢? ?????drift????閮??郊??- graphify ?芾敺?Windows 頝?WSL ?∪?鋆????遣???閬?Windows ?啣?

Open questions:
- 閬?閬? git hook ??commit ???甇?video_tools.py嚗??思???
- 閬?閬? remote origin ??GitHub嚗?雿輻?捱摰?

## Git / Retrieval

Related files:
- `~/video_pipeline/.gitignore`
- `~/video_pipeline/HANDOFF.md`
- `~/video_pipeline/roadmap.md`
- `~/video_pipeline/graphify-out/GRAPH_REPORT.md`

Related commits:
- `add33d1` (init: hermes video_pipeline v2 ??full handoff hub)

Graphify anchors:
- Node: `HANDOFF ??Video Pipeline v2`嚗ommunity 1嚗?- Node: `graphify-out/GRAPH_REPORT.md`嚗ommunity 2 "Skill I/O Contracts & Workflow"嚗?
Search tags: decision-log, handoff-hub, git-init, co-location, graphify-corpus, video-pipeline-v2, snapshot-pattern
