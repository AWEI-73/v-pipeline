# Graph Report - video_pipeline  (2026-06-06)

## Corpus Check
- 61 files · ~89,779 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 968 nodes · 1434 edges · 78 communities (47 shown, 31 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 145 edges (avg confidence: 0.79)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3666f246`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]

## God Nodes (most connected - your core abstractions)
1. `ToolError` - 54 edges
2. `run()` - 22 edges
3. `load_dashboard_state()` - 20 edges
4. `pipeline()` - 18 edges
5. `run_tool()` - 16 edges
6. `ContractToMvScriptTest` - 16 edges
7. `ValidateSegmentContractTest` - 15 edges
8. `run_mv()` - 13 edges
9. `_audio_duration()` - 13 edges
10. `compose_and_qa()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `_run_pipeline()` --calls--> `resolve_python()`  [INFERRED]
  route.py → video_pipeline_core/platform_tools.py
- `main()` --calls--> `resolve_python()`  [INFERRED]
  run_with_ollama.py → video_pipeline_core/platform_tools.py
- `cmd_mksrt()` --calls--> `ToolError`  [INFERRED]
  video_tools.py → video_pipeline_core/vt_core.py
- `cmd_burnsub()` --calls--> `resolve_font()`  [INFERRED]
  video_tools.py → video_pipeline_core/platform_tools.py
- `ResolvePythonTest` --uses--> `ToolError`  [INFERRED]
  tests/test_platform_tools.py → video_pipeline_core/vt_core.py

## Communities (78 total, 31 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (78): Exception, RuntimeError, apply_effects(), atomic_write_json(), _bgm_plan(), build_filter_chain(), build_state(), collect_fix_actions() (+70 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (55): ContentQATest, test_fresh_run_compiles_video(), test_non_repo_cwd_resolution(), test_rerun_node_12_runs_verification_directly_without_deleting_final(), test_wait_for_generated_provider_arrived_triggers_rebuild(), TestRuntime, Return the Python interpreter command for the current platform., resolve_python() (+47 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (6): BuildLayerVocabTest, FallbackRouteTest, SPEC 合約層 validator(canonical JSON)。對應 skills/spec-contract.md。 Node 0-1 brief ga, 鎖住 Node 9-14 canonical 詞彙(skill 契約與未來程式須一致)。, ValidateBriefTest, ValidateSegmentContractTest

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (9): CaptionMatchScoreTest, ClassifyAssetTest, ClassifyEntryTest, FormatMaterialMapTest, IngestWorkDirsTest, MatchScriptToMaterialTest, ParseResTest, Material intake funnel Stage 1: classify_asset (pure, content-agnostic).  Defaul (+1 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (33): caption_asset(), _caption_match_score(), _cjk_bigrams(), classify_asset(), _classify_entry(), cmd_caption_meta(), cmd_ingest_meta(), cmd_match_mv() (+25 more)

### Community 5 - "Community 5"
Cohesion: 0.12
Nodes (27): adapt_contract_file(), _apply_stock_first_if_enabled(), contract_to_mv_script(), _hash_file(), _hash_json(), _load_category_ids(), _manifest(), contract_adapter.py — canonical-first runtime adapter(see roadmap.md).  公開 SPEC (+19 more)

### Community 6 - "Community 6"
Cohesion: 0.09
Nodes (18): DashboardStateSpecTest, Generated request artifact uses the canonical object shape with items., 4. ComfyUI provider in build profile produces blocked/deprecated finding., 5. Existing route state.json dashboard mode still works., 2. Missing optional effects artifact does not fail when effects_enabled=false., 1. Manifest-based dashboard state includes required nodes., 3. Generated requests without generated manifest produce warn status on Fallback, load_dashboard_state() (+10 more)

### Community 7 - "Community 7"
Cohesion: 0.13
Nodes (22): video tools 統一錯誤。`fix_class`(material/spec/human)可選,讓 route/dashboard     像 Reco, run(), ToolError, cmd_burnsub(), cmd_concat(), cmd_cut(), cmd_download(), cmd_meta() (+14 more)

### Community 8 - "Community 8"
Cohesion: 0.09
Nodes (9): Tests for platform_tools.py — cross-platform executable resolver., Test the generic _resolve_executable helper., ResolveExecutableTest, ResolveFfmpegTest, ResolveFontTest, ResolveOllamaTest, ResolveOllamaUrlTest, ResolvePythonTest (+1 more)

### Community 9 - "Community 9"
Cohesion: 0.13
Nodes (19): cmd_verify(), _now_iso(), vt_verify.py — VERIFY(品管:5 維技術 QA + 內容對齊),從 video_tools 解耦。 共用原語取自 vt_core,避免循環匯, 維度3: SRT 內容 vs script.subtitle 字元重疊率, 維度1: 每個 script segment 是否都有對應的影片段落, 維度5: 解析度、framerate、有音軌、有視軌、無黑幀, VERIFY：對成片做 5 維度評分 + 路由修正指示, 維度4: 音量是否在合理範圍 (-30dB ~ -6dB peak, -25dB ~ -14dB mean) (+11 more)

### Community 10 - "Community 10"
Cohesion: 0.17
Nodes (17): _is_windows(), platform_tools.py — cross-platform executable and resource resolver.  Centralize, Find yt-dlp executable., Find ollama executable., Return Ollama HTTP endpoint., Generic resolver: env → PATH → known locations → ToolError., Find ffmpeg executable., Find ffprobe executable. (+9 more)

### Community 12 - "Community 12"
Cohesion: 0.15
Nodes (7): BuildBlockStateTest, FixClassMapTest, FixTaxonomyAlignmentTest, BUILD recoverable blocks + VERIFY fix_class taxonomy (material/spec/human).  A p, 錯誤分類單一真相:vt_core 與 video_pipeline 的 fix_class→target 必須一致     (收斂時 video_pipelin, RecoverableBuildErrorTest, _state()

### Community 13 - "Community 13"
Cohesion: 0.12
Nodes (16): _cjk_font(), compare_to_gold(), _extract_frame(), grid_durations(), _mv_result(), plan_mv(), MV-cut — beat-driven timeline for the Unified Segment Model (timeline:beat).  In, (I/O) Grab a single frame at time t (seconds) → jpg. Returns bool ok. (+8 more)

### Community 14 - "Community 14"
Cohesion: 0.14
Nodes (15): cmd_gen_bgm(), cmd_mix_audio(), 混合人聲 + BGM：BGM 降到指定音量，含淡入淡出, 合成一段情境氛圍墊樂（placeholder）。真曲可直接覆蓋 bgm/<mood>.mp3。, _audio_duration(), 用 ffprobe 取得媒體長度(秒)。共用底層原語。, cmd_collage(), cmd_grade() (+7 more)

### Community 15 - "Community 15"
Cohesion: 0.12
Nodes (7): GridDurationsTest, MV-cut increment ①: beat → cut_grid (timeline:beat driver).  Pure-function tests, increment ③ I/O loop — frame extract + VLM scoring injected as fakes., RunMvArtifactTest, ScoreWindowsTest, ShotMidpointsTest, SrtTsTest

### Community 16 - "Community 16"
Cohesion: 0.22
Nodes (15): _allows_generated(), attach_generated_manifest_to_artifact_manifest(), build_generated_asset_requests(), _is_identity_or_proof(), _items(), _load_json(), generated_assets.py — generated fallback request/manifest artifacts.  This modul, Validate externally generated outputs and write generated_asset_manifest.json. (+7 more)

### Community 17 - "Community 17"
Cohesion: 0.13
Nodes (16): _drawtext_chain(), mv_chain(), _mv_music_mix(), _photo_vf(), 靜照→影片片段的 vf。kenburns=緩慢推近(救開場/收尾照片,避免死板靜止);     否則純 hold(scale+pad)。輸出 1920x1080, 編劇文字層 → ffmpeg drawtext:narrative(全屏故事字卡:暗化+大字置中)+     label(底置中標籤)+ name_super(, (I/O) increment ④：依 plan 從各原片抽段 → 統一 1920x1080 → 硬切拼接(對拍)     → 鋪音樂(trim 到視覺長度)→, 單一入口(roadmap #0 接線):material_db × 劇本 → match-mv → render。     把 curator 理解(capti (+8 more)

### Community 18 - "Community 18"
Cohesion: 0.13
Nodes (16): beats_to_cut_grid(), detect_shots(), filter_shots(), fixed_windows(), _is_image(), _merge_short_spans(), Clean a shot list (contiguous (start, end) spans from detect_shots):     fold sh, Window a continuous take into candidate spans (the RIGHT primitive for raw     s (+8 more)

### Community 19 - "Community 19"
Cohesion: 0.18
Nodes (15): cmd_analyze(), cmd_curate(), cmd_rank_local(), _filter_candidates(), _find_best_window(), vt_curate_legacy.py — 舊版小編(whisper analyze / pexels-search curate / rank-local)。, 小編：Whisper 轉譯 + 找最匹配 query 的時間窗口, 過濾掉太短/太長/talking-head/news (+7 more)

### Community 20 - "Community 20"
Cohesion: 0.17
Nodes (15): cmd_pexels_download(), cmd_pexels_search(), _download_url(), fetch_stock_video(), fetch_stock_video_with_provider(), _pexels_request(), _pexels_video_candidates(), _pixabay_video_candidates() (+7 more)

### Community 21 - "Community 21"
Cohesion: 0.14
Nodes (6): Longform Duration Policy — TTS actual duration must drive material selection and, Validity filter must key off the real TTS target, not script duration_sec., Too-short video must be recoverable, never abort., SegTargetLenTest, VideoCandidateFilterTest, VideoFillPlanTest

### Community 22 - "Community 22"
Cohesion: 0.26
Nodes (12): _find_material(), _load_state(), _looks_like_segment_contract(), main(), 找學員素材 seg{n}_user.* 或 seg{n}.*（圖或影片）。, MV 派工:無 state→跑 mv_chain;有 state→依 next_action 報告複核點。     MV 缺口(gap/必放/bookend)需, MV 模式:route 驅動 canonical adapter 或 legacy mv_chain,寫 state.json 到 outdir。     (旁, 印 MV state 的人工複核點(gap/必放/bookend)= 人在迴圈的接點。 (+4 more)

### Community 23 - "Community 23"
Cohesion: 0.18
Nodes (11): cmd_music_fetch(), cmd_srt(), cmd_tts(), _fmt_srt_time(), _music_ytdlp_cmd(), vt_audio.py — audio-director(TTS/混音/BGM/music-fetch)+ subtitle-director(SRT), 從, 秒數轉 SRT 時間戳 HH:MM:SS,mmm, 從 tts_timing.json 生成 phrase-level 時間同步 SRT。      跟舊版 mksrt（靜態 per-segment）不同： (+3 more)

### Community 24 - "Community 24"
Cohesion: 0.15
Nodes (5): BgmPlanTest, CmdMusicFetchInvokeTest, MusicYtdlpCmdTest, Real BGM source — music-fetch (yt-dlp audio) + pipeline bgm resolution plan.  Pi, 實際呼叫 cmd_music_fetch(mock yt-dlp/ffprobe)——抓「拆模組漏 import」這類     pure-builder 測不到

### Community 25 - "Community 25"
Cohesion: 0.15
Nodes (13): allocate_segments(), detect_beats(), _plan_matched_segment(), _plan_stock_segment(), (I/O) Detect tempo + beat timestamps from an audio file via librosa.     Returns, (I/O) Detect tempo + beat timestamps from an audio file via librosa.     Returns, 純函式:把音樂總長分給各段 → 每段幾個 clip、每 clip 多長。     montage/pace:fast → 多個快剪(~fast_clip 秒,預, local 段:用 match-mv 已配好的 clip 開窗(不 live 重評)。`_winfn` 可注入測試。 (+5 more)

### Community 26 - "Community 26"
Cohesion: 0.21
Nodes (7): _get_ffmpeg(), _get_ffprobe(), _get_ytdlp(), _LazyTool, vt_core.py — video tools 共用底層原語(無領域邏輯)。 拆出讓 video_tools.py / curator.py 共用而不循環匯入, Descriptor that resolves on first access and caches the result., _ToolPaths

### Community 28 - "Community 28"
Cohesion: 0.25
Nodes (10): _audio_policy(), build_assembly_plan(), build_timeline_build(), edit_artifacts.py — Node 9/10 build-facing JSON artifacts.  This module separate, Build Node 9 assembly_plan from generated MV payload., Write assembly_plan.json and optionally timeline_build.json., Write assembly_plan.json and optionally timeline_build.json., Build Node 10 timeline_build from concrete render plan clips. (+2 more)

### Community 29 - "Community 29"
Cohesion: 0.2
Nodes (10): load_material_categories(), spec_contract.py — SPEC 合約層的程式面(canonical = normalized JSON)。  對應 skills/spec-co, 純函式:依覆蓋狀態 + 段性質 → 建議 fallback 路由(Node 8)。     鐵則:**must_include / identity-sensi, 純函式:驗 Node 0-1 brief(JSON dict)。回 {ok, errors, warnings}。     不補預設、不改值;只報缺漏/非法值,, (I/O) 讀地圖規範詞彙(examples/material_categories.json)→ {id: category} dict。, 純函式:驗 Node 3 segment contract(core+facets normalized JSON)。     contract = {segm, _seg_id(), suggest_fallback_route() (+2 more)

### Community 31 - "Community 31"
Cohesion: 0.31
Nodes (3): _args(), route.py MV mode (roadmap #7 route↔MV).  These cover the dispatch/report logic w, RouteMvTest

### Community 32 - "Community 32"
Cohesion: 0.39
Nodes (8): build_light_effects_plan(), _profile_enabled(), light_effects.py - ffmpeg-safe light effects plan runner.  This module turns can, _segment_id(), _segment_operations(), _text_ops(), _write_json(), write_light_effects_artifacts()

### Community 33 - "Community 33"
Cohesion: 0.25
Nodes (9): find_clips(), find_photos(), _plan_live_segment(), (I/O) 找 material_root 底下、路徑含 material_hint 的影片(scoping)。, (I/O) 找 material_root 底下、路徑含 material_hint 的照片(救開場/收尾 bookend)。, live 段:find_clips/photos → (照片 still) 或 (開窗→靜止預篩→VLM 評分→必放選段)。, live 段:find_clips/photos → (照片 still) 或 (開窗→靜止預篩→VLM 評分→必放選段)。, Pick `n_slots` windows for an MV, **must-include-aware**（必放守門）.      candidates: (+1 more)

### Community 38 - "Community 38"
Cohesion: 0.39
Nodes (7): call_ollama_full(), main(), Map (primary, related) verdicts → 0-100 content-alignment score (D3).      Grade, Score content alignment by matching the image against a Chinese VISUAL     descr, rubric_score(), score_segment(), yn()

### Community 39 - "Community 39"
Cohesion: 0.46
Nodes (7): _backend_for(), build_motion_graphics_render_plan(), _finding(), motion_graphics.py — Node 14 effects contract scaffold.  The core edit flow shou, validate_motion_graphics_contract(), _write_json(), write_motion_graphics_artifacts()

### Community 40 - "Community 40"
Cohesion: 0.36
Nodes (7): build_music_structure(), _density_hint(), _fmt_mmss(), music_structure.py — V3 P1 music timing artifact.  Turn detected tempo/beats int, Pure builder: tempo/beats -> normalized music_structure.json shape., Detect beats and write music_structure.json. Detector is injectable for tests., write_music_structure()

### Community 45 - "Community 45"
Cohesion: 0.52
Nodes (6): default_build_profile(), load_build_profile(), build_profile.py — BUILD-layer tool/provider profile artifact.  The canonical se, validate_build_profile(), _validate_choice(), write_build_profile()

### Community 46 - "Community 46"
Cohesion: 0.48
Nodes (5): default_model_routes(), load_model_routes(), model_routing.py — model route artifact for agent-driven video workflow.  This m, _validate_routes(), write_model_routes()

### Community 47 - "Community 47"
Cohesion: 0.29
Nodes (7): _asr_srt(), _burn_asr_subtitle(), (I/O) faster-whisper 轉錄 clip 原音 → SRT(時間軸相對 clip)。回 srt 或 None。     model_size 預, (I/O) faster-whisper 轉錄 clip 原音 → SRT(時間軸相對 clip)。回 srt 或 None。     model_size 預, (I/O) 對講話段 clip 跑 ASR → 燒演講字幕(CJK)。回 subbed 路徑或 None。, (I/O) 對講話段 clip 跑 ASR → 燒演講字幕(CJK)。回 subbed 路徑或 None。, _srt_ts()

### Community 48 - "Community 48"
Cohesion: 0.33
Nodes (6): Find a CJK font file for ffmpeg drawtext / subtitle burning.      Returns the ab, resolve_font(), cmd_title_card(), cmd_title_sequence(), 片頭/片尾：產生獨立的動態標題片段（文字滑入→hold→淡出）於深色底 + 暈影。     1920x1080/30fps/bt709。--anim slide, 字卡：在影片開頭疊加標題（淡入→hold→淡出），可選副標。保留規格與時長。

### Community 49 - "Community 49"
Cohesion: 0.33
Nodes (5): cmd_assemble(), cmd_merge_final(), vt_editor.py — 剪輯師(assemble + merge-final,檔案層級組裝),從 video_tools 解耦 (= editor ski, 剪輯師：依 TTS 時長剪每段素材 → 統一 1920x1080 → concat。      輸入：       clip_list.json   小編產出，, 剪輯師最終組合：把音軌 + 字幕套到無音軌的視覺上。      輸入：       --visual  rough_cut.mp4（assemble 的輸出，純

### Community 58 - "Community 58"
Cohesion: 0.53
Nodes (5): _finding(), _overlap(), editor_review.py — Node 11/12 lightweight clip review checks.  These checks are, review_timeline_build(), write_editor_review()

### Community 59 - "Community 59"
Cohesion: 0.33
Nodes (6): filter_static_windows(), _parse_freeze_ratio(), 純函式:從 ffmpeg freezedetect stderr 算「凍結秒數佔窗比例」(0~1)。     解析 freeze_start/freeze_en, (I/O) 跑 freezedetect 於 [start,start+dur] → 回凍結比例(0~1)。失敗回 0(視為動態,不誤殺)。, 純邏輯(ratio 可注入測試):丟掉「凍結比例 >= max_static」的窗。     全被丟 → 回原 windows(寧可送 VLM 也不要 0 候選, window_static_ratio()

### Community 64 - "Community 64"
Cohesion: 0.5
Nodes (5): audio_qa(), build_mv_state(), 純函式:MV 音訊搭配 QA(verify 的音訊維度,roadmap #6)。     檢查原音/音樂編排一致性——抓「該保留原音卻沒保留→被音樂蓋掉」這類, 純函式:MV 音訊搭配 QA(verify 的音訊維度,roadmap #6)。     檢查原音/音樂編排一致性——抓「該保留原音卻沒保留→被音樂蓋掉」這類, 把 MV 段落寫成 dashboard 認得的 state.json(放在 out_path 同目錄)。     純函式 → state dict;附帶寫檔。每

### Community 65 - "Community 65"
Cohesion: 0.5
Nodes (4): cmd_mksrt(), _fmt_srt_ts(), 秒數轉 SRT 時間戳格式 HH:MM:SS,mmm, 從劇本 JSON 生成中文 .srt 字幕檔      劇本 JSON 格式（陣列）：     [       {"start": 0,  "end": 15,

### Community 72 - "Community 72"
Cohesion: 0.5
Nodes (4): _default_scorer(), Wrap content_qa.score_segment (lazy import) → fn(frame, desc)->(score,desc,reaso, increment ③ I/O: score each candidate window by grabbing its midpoint     frame, score_windows()

## Knowledge Gaps
- **242 isolated node(s):** `MV 模式:route 驅動 canonical adapter 或 legacy mv_chain,寫 state.json 到 outdir。     (旁`, `印 MV state 的人工複核點(gap/必放/bookend)= 人在迴圈的接點。`, `找學員素材 seg{n}_user.* 或 seg{n}.*（圖或影片）。`, `MV 派工:無 state→跑 mv_chain;有 state→依 next_action 報告複核點。     MV 缺口(gap/必放/bookend)需`, `Minimal .env loader (no external deps). KEY=VALUE per line; '#' comments.     D` (+237 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **31 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ToolError` connect `Community 7` to `Community 0`, `Community 65`, `Community 4`, `Community 6`, `Community 8`, `Community 9`, `Community 10`, `Community 14`, `Community 48`, `Community 17`, `Community 49`, `Community 19`, `Community 20`, `Community 23`, `Community 25`, `Community 26`?**
  _High betweenness centrality (0.188) - this node is a cross-community bridge._
- **Why does `load_dashboard_state()` connect `Community 6` to `Community 1`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Why does `resolve_python()` connect `Community 1` to `Community 10`, `Community 22`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Are the 50 inferred relationships involving `ToolError` (e.g. with `ResolvePythonTest` and `ResolveExecutableTest`) actually correct?**
  _`ToolError` has 50 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `run()` (e.g. with `cmd_search()` and `cmd_meta()`) actually correct?**
  _`run()` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `load_dashboard_state()` (e.g. with `.test_manifest_based_state_includes_all_nodes()` and `.test_missing_optional_effects_does_not_fail_when_effects_disabled()`) actually correct?**
  _`load_dashboard_state()` has 18 INFERRED edges - model-reasoned connections that need verification._
- **What connects `MV 模式:route 驅動 canonical adapter 或 legacy mv_chain,寫 state.json 到 outdir。     (旁`, `印 MV state 的人工複核點(gap/必放/bookend)= 人在迴圈的接點。`, `找學員素材 seg{n}_user.* 或 seg{n}.*（圖或影片）。` to the rest of the system?**
  _242 weakly-connected nodes found - possible documentation gaps or missing edges._