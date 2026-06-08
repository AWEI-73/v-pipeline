# TEST_CASE: stock_story_e2e — "A Barista's Morning" (一杯咖啡的早晨)

End-to-end, contract-led test case for the Hermes Video Pipeline. Exercises every
node in `NODE_ORDER = ["0","3","2","4-7","5","8","9","10","11","13","12","14"]`
and every major branch (timeline_source fixed/beat, text_layer narrative/label/
subtitle-auto/none, audio music/diegetic/duck, must_include/review_required,
ffmpeg vs CapCut render). Designed to be buildable purely from common Pexels stock.

## 1. Story synopsis + emotional arc

A city wakes at dawn; inside one cafe, a barista begins the morning ritual. We open
on empty sunrise streets (起 / thesis: the world is quiet, something is about to
begin), move inside to machines warming in steam (承: grounding, real space, real
sound), accelerate through close-ups of hands grinding and tamping (轉 build: the
craft, the density of work), peak on a slow-motion pour with crema blooming (climax:
the single perfect moment), let customers and street life flow back in (the personal
reconnects to the city), and resolve on one finished cup in warm window light (合 /
resolution: a small, complete, just-right morning). The arc is quiet → grounded →
building → peak → opening-out → warm rest. No people are individually identifiable;
no claim is made that any specific event happened — it is a **conceptual** stock MV,
so generic stock footage is an honest material source, not a forgery.

- `material_source_mode: "stock_first"`, `story_truth_level: "conceptual"`.
- 6 segments, target total ~60s (weights: opening/climax/closing 1.6, montage 1.0, bridge 0.7).

## 2. Story beats table

| # | section_role | story_purpose (short) | timeline_source | layout / pace | search_query (EN) | text layer | audio role |
|---|---|---|---|---|---|---|---|
| 1 | opening | City + cafe waking; set warm tone | **fixed** | single / hold | `empty city street sunrise golden hour` | narrative (full-screen card) | music |
| 2 | establishing | Inside: machines warming, steam, real room tone | **fixed** | single / hold | `coffee shop interior morning steam espresso machine` | **dict-none** (`{none:true,reason}`) | **diegetic** (keep audio) |
| 3 | montage | Hands: grind / tamp / pour — craft density | **beat** | montage / fast | `barista hands grinding tamping coffee close up` | label (lower-third) | music |
| 4 | climax | Hero slow-mo pour, crema/latte art, the peak | **beat** | single / hold | `slow motion coffee pour latte art crema close up` | **dict-none** (`{none,reason}`) | **duck** (sidechain) |
| 5 | montage | Customers arrive; personal reconnects to city | **beat** | montage / fast | `people walking street cafe customers silhouette` | **"none"** (string) | music |
| 6 | closing | Finished cup, warm window light, resolution | **fixed** | single / hold | `finished cup of coffee on counter window warm light` | narrative (full-screen card) | music |

> **CORRECTED after the first real E2E (see §8).** The opening/closing bookends
> originally carried `must_include`. That is WRONG for a pure-stock run: the honesty
> guard in `stock_first._can_use_stock` returns `False` for **any** segment with
> `must_include` (regardless of identity/proof sensitivity), so those bookends were
> refused stock and silently dropped from the timeline (`script_coverage` "missing
> [1,6]"). The canonical PASS form **omits `must_include`** on the two conceptual
> bookends so stock may legitimately fill them. The `must_include`-on-bookend variant
> is preserved in §8 as the honesty-guard regression probe + a hardening candidate.

## 3. Node-by-node expectation table

Each row ties to the `verify_fn` in `video_pipeline_core/node_registry.py`. Expected
status is what `verify_*` returns once that node's artifact exists for this contract.

| Node | Skill(s) | Input artifact | Output artifact | What this test asserts | Expected status | PASS/FAIL criterion (verify_fn) |
|---|---|---|---|---|---|---|
| **0** | video-workflow | — | `brief.json` | brief present & well-formed (mv, stock_first, must_include x2) | **done** | `verify_brief`: `artifacts["brief"]` truthy → done. FAIL if brief absent. |
| **3** | spec-contract, director | brief.json | `segment_contract.json` | 6 segments parse; `material_source_mode=stock_first`; `story_truth_level=conceptual` | **done** | `verify_contract`: dict with `segments` list → "6 segments defined". FAIL if not 6 / not parseable. |
| **2** | curator, gap-analyzer | segment_contract.json | `material_coverage_map.json` | **stock_first auto-passes WITHOUT a coverage map** (the gate must not stall) | **done** | `verify_material_coverage`: `material_source_mode=="stock_first"` forces `status="done"`, reason "optional (stock_first mode)". FAIL = "missing" → see §5 finding A. |
| **4-7** | writer, audio-director, effects-director, director, curator | segment_contract.json | (facets in-place) | All 6 facets present on all 6 segs; reasons on the 5 reason-required facets | **warn (36/36 facets, 29/30 reasons)** | `verify_facets`: present=36/36 → not "partial"; reason_present=29/30 (seg5 string `"none"` text_layer carries no reason) → **warn**, reason "Facet reasons incomplete (29/30)". To reach **done 30/30**, convert seg5 to dict-none `{none:true,reason:...}` (see §5 finding B). |
| **5** | audio-director | segment_contract.json | `music_structure.json` | music structure exists (drives beat grid for seg 3/4/5) | **done** | `verify_audio`: `artifacts["music_structure"]` truthy → done. FAIL if absent (no music fetched). |
| **8** | gap-analyzer, generative-director, route | segment_contract.json, material_coverage_map.json | `build_profile.json` | profile = `render_backend=ffmpeg`, `effects_enabled=false`, **no comfyui**, no generated provider | **done** | `verify_profile`: no `fallback_visual_provider=="comfyui"` AND no `gen_request_items` → done "Build profile defined". FAIL→**blocked** iff comfyui ever selected. |
| **9** | editor | contract, music_structure, build_profile | `assembly_plan.json` | assembly plan resolves all 6 segments | **done** | `verify_assembly`: `artifacts["assembly_plan"]` truthy → done. |
| **10** | editor | assembly_plan.json | `timeline_build.json` | timeline compiled; **every clip carries `trace`** | **done** | `verify_timeline`: clips present AND no clip lacks `trace` → done "Timeline compiled (N clips)". FAIL→**warn** "timeline item has no trace" (chaining bug: a clip lost its source provenance). |
| **11** | editor_review, dashboard | timeline_build.json | `editor_review.json` (+ timeline_invariants/broll/caption audits) | review decision = approve | **done** | `verify_editor_review`: `decision=="approve"` (or status `pass`) → done. **warn** if human_review/auto_fix/route_change; **blocked** if block/rerender. |
| **13** | editor (compiler) | timeline_build.json, editor_review.json | `final.mp4` (+ av/audio/srt) | ffmpeg canonical render produces final.mp4 ~60s | **done** | `verify_render`: `context["final_exists"]` true → done. FAIL=missing "Video not rendered". (CapCut variant: see §5 note.) |
| **12** | verify, content_qa | final.mp4 | `verify_result.json` (+ qa_report, keyframe_grid.jpg, visual_audit) | technical verify passes; score ≥ threshold | **done** | `verify_verify`: `verify_result["pass"]` true → done "score: N". FAIL→**blocked** if `pass=false` with issues; **warn** if state.json exists but verify_result missing. |
| **14** | route, editor, verify, dashboard | verify_result.json | `revision_plan.json` (optional) | effects disabled → no revision required | **optional** | `verify_revision`: `effects_enabled=false` AND no motion-graphics plan/manifest → **optional** "No revision plan required". Would be **missing** only if effects_enabled=true with no plan. |

## 4. Chaining (handoff) assertions — the main point

These catch bugs *between* nodes, where each node passes in isolation but data fails
to flow. Cross-references to `runtime_orchestrator.py` and the consuming verify_fn.

- **C1 (Node 3 → Node 13 stock fetch):** each `segments[i].material_fit.search_query`
  (English) MUST flow through `contract-adapt` into the generated script's per-segment
  `search_query` and be the query used for the Pexels fetch in `contract-run`.
  *Verified in adapt dry-run:* all 6 English queries appear verbatim in the adapted
  script (see §6). FAIL signature: a segment's stock fetch uses the Chinese
  `visual_desc` instead (Pexels miss) — the `spec_contract` warning path for missing
  `search_query`. This contract has a query on every stockable segment → no fallback.
- **C2 (Node 5 → beat-timeline cut points):** `music_structure.json` beat grid MUST
  drive the cut points of `timeline_source: "beat"` segments (3, 4, 5). The
  `editing_grammar.beat_alignment` on those segs (`music`/`emotion`/`music`) declares
  the intended alignment. FAIL: beat segments are cut on fixed durations ignoring the
  beat grid (montage feels off-beat).
- **C3 (audio role → render audio graph):** seg2 `diegetic` and seg4 `duck` MUST keep
  original audio (`keep_audio:true` in the adapted script — verified §6) and seg4 MUST
  be sidechain-ducked under music. FAIL: diegetic/duck segments are silently muted to
  music-only (the audio_pairing / audio_qa verify dimension at Node 12 should catch a
  segment that declared keep-audio but rendered silent).
- **C4 (must_include honesty guard — CORRECTED):** `stock_first._can_use_stock`
  refuses stock for **any** segment carrying `must_include` (or identity_sensitive /
  proof_critical). So in a pure-stock run a `must_include` bookend gets **no source**
  and is dropped from the timeline → `verify.script_coverage` reports "missing [seg]".
  The earlier claim "conceptual must_include → stock satisfies it" was FALSE. The
  canonical PASS contract therefore omits `must_include` on the conceptual bookends.
  **Hardening candidate (for the user):** a `must_include` segment that ends with no
  source should make the chain BLOCK (`next_action=await_material` / must_include
  unfilled), not silently render without it. Today it silently drops — see §8.
- **C5 (subtitle:"auto" needs real speech — CORRECTED):** `subtitle:"auto"` runs ASR
  on the segment's ORIGINAL audio. Pure stock B-roll has no speech, so ASR yields
  nothing, the runtime falls back to a `[Music]` stub `subtitles.srt`, and
  `verify.subtitle_accuracy` scores **0** (overlap 0/N). The canonical PASS contract
  uses dict-none on seg4 instead. `subtitle:"auto"` is only valid on a segment with
  real spoken audio (interview/narration) — out of scope for a pure-stock conceptual MV.
- **C6 (review_required → editor_review):** segs 1, 2, 6 are `review_required:true`
  (high-weight 1.6/1.0 opening/establishing/closing). These must surface as review
  items, and `editor_review` must still resolve to `approve` for the test to PASS at
  Node 11. FAIL: a review-required segment is auto-approved without ever appearing in
  the review set.
- **C7 (build_profile → no comfyui, ever):** Node 8 `build_profile.fallback_visual_provider`
  MUST never be `comfyui`. If it ever is, `verify_profile` returns **blocked** and the
  chain halts — this is the deprecated-provider guard. Expected: `ffmpeg` backend,
  `effects_enabled=false`, no generated assets requested.

## 5. Targeted regression hooks for the 3 known dry-run findings

### Finding A — Node 2 stock_first gate (must auto-pass)
- **Reproduce (desired pass):**
  ```powershell
  python runtime.py status --project stock-story-e2e
  ```
  Node 2 row MUST read `done | material_coverage_map.json | Material coverage map optional (stock_first mode)` and `next_action` MUST NOT be `missing_artifact:material_coverage_map.json`.
- **Re-expose the bug (control):** remove the top-level `"material_source_mode": "stock_first"`
  line from `segment_contract.json` and re-run `status`. `verify_material_coverage`
  then falls through to `status="missing"` → `next_action = missing_artifact:material_coverage_map.json`
  and the chain stalls demanding a coverage map a stock-first generic video should not need.
- **Expected vs actual:** with the line present → **done** (desired). Without it → **missing/stall** (the bug). The fix already lives in `verify_material_coverage` (the `material_source_mode == "stock_first"` override); this test guards that it stays.

### Finding B — Node 4-7 facets stuck at warn (6th facet `editing_grammar`)
- **Reproduce:** `python runtime.py status --project stock-story-e2e` → Node 4-7 row.
- **Expected (as authored):** **warn**, reason `Facet reasons incomplete (29/30)`.
  This contract intentionally carries **all 6 facets** (incl. `editing_grammar` with a
  `reason`) on all 6 segments → facets present = **36/36** (defeats the old "20/24,
  no editing_grammar" symptom). The single remaining warn is seg5's text_layer being
  the bare string `"none"` (29/30 reasons), which is the canonical "no caption" form
  the validator itself recommends.
- **One-line fix to reach done 36/36 + 30/30:** change seg5 `"text_layer": "none"` to
  `"text_layer": {"none": true, "reason": "connective montage, intentionally no on-screen text"}`.
  Verified: flips `verify_facets` to **done** "All required contract facets and reasons present".
- **Why authored at warn:** so the test demonstrates BOTH that the 6th facet is now
  honored (36/36 — the real regression target) AND the exact residual warn mechanic,
  with a documented, verified fix. If a future change makes `verify_facets` ignore
  `editing_grammar`, present would drop to 30/36 and this test catches it.

### Finding C — Planning-only gap (no render-free mid-chain BUILD artifacts)
- **Reproduce:**
  ```powershell
  python video_tools.py contract-adapt examples\genre_tests\stock_story_e2e\segment_contract.json --categories examples\genre_tests\stock_story_e2e\material_categories.json --out %TEMP%\stock_story_adapt.json
  ```
  This writes **only** `generated_mv_script.json` (the adapted script). It does NOT
  produce `build_profile.json`, `assembly_plan.json`, or `timeline_build.json`.
- **Expected (current/buggy) vs desired:** Currently those three BUILD artifacts are
  materialized **only inside `contract-run`**, which renders. So `runtime.py status`
  cannot show Nodes 8/9/10 as `done` without a full render (ffmpeg + Pexels + music).
  Desired: a render-free "dry build" that emits build_profile/assembly_plan/timeline_build
  so the chain can be validated past Node 3 without external deps. This test documents
  the gap; the authoring validation deliberately stops at the adapt dry-run + status.

### CapCut path note (same contract, alternate Node 13)
The default test asserts the **ffmpeg** path (`build_profile.render_backend=ffmpeg` →
`final.mp4`). The SAME contract routes the CapCut path when
`build_profile.render_backend=capcut_draft`: Node 13 emits a `.draft` /
`capcut_draft_manifest.json` instead of final.mp4, then `await_capcut_export` (a human/CU
GUI export — there is no CLI export), then `capcut-finalize --video capcut_exported.mp4
--bgm ... --outro-title ...` produces the final video, which still runs Node 12 verify.
This test does not assert the CapCut branch by default; ffmpeg stays canonical.

## 6. How to run (Windows PowerShell, copy-paste)

External deps for the full E2E render: **ffmpeg** on PATH, a **Pexels API key**
(stock fetch), **yt-dlp** (music-fetch via `music.source=yt`), and **Ollama** (gate /
content QA VLM). The adapt dry-run + `status` below need none of these.

```powershell
cd C:\Users\user\Desktop\video_pipeline

# (a) Dry plan — validates the contract, writes generated_mv_script.json only (no render)
python video_tools.py contract-adapt `
  examples\genre_tests\stock_story_e2e\segment_contract.json `
  --categories examples\genre_tests\stock_story_e2e\material_categories.json `
  --out $env:TEMP\stock_story_adapt.json
# Expect: { "ok": true, "errors": [], "warnings": [] }

# (b) Create project + run, stage the contract + brief + categories into input/
python video_tools.py project-init "Stock Story E2E"
python video_tools.py project-new-run --label e2e
# Copy the SPEC artifacts into the run's input folder (paths per project-init output):
#   segment_contract.json, brief.json, material_categories.json
#   -> <project_root>\stock-story-e2e\input\

# (c) Inspect chain state WITHOUT rendering (Finding A + B live here)
python runtime.py status --project stock-story-e2e
# Expect Node 0=done, 3=done, 2=done(stock_first), 4-7=warn(29/30), 5..13 missing until run

# (d) Full E2E (needs ffmpeg + Pexels key + yt-dlp + Ollama)
python runtime.py run --project stock-story-e2e

# (e) Node 12 verify + P1 audit pack (after final.mp4 exists)
python video_tools.py verify --script <run>\generated_mv_script.json --timing <run>\music_structure.json `
  --edit-log <run>\timeline_build.json --srt <run>\subtitles.srt --video <run>\final.mp4 --out <run>\verify_result.json
python video_tools.py timeline-audit --timeline <run>\timeline_build.json --out <run>\timeline_invariants.json
python video_tools.py broll-audit     --timeline <run>\timeline_build.json --out <run>\broll_audit.json
python video_tools.py caption-audit    --srt <run>\subtitles.srt           --out <run>\caption_audit.json
python video_tools.py keyframe-grid    --video <run>\final.mp4             --out <run>\keyframe_grid.jpg
python video_tools.py visual-audit     --video <run>\final.mp4             --out <run>\visual_audit.json
```

## 7. Expected final state

- `state.json`: `pass = true`.
- `verify_result.json`: `pass = true`, `score ≥` project threshold (coffee baseline
  ran ~92.5; expect comparable for this stock-only conceptual MV).
- `final.mp4`: ~60s (target_length), weights 1.6/1.0/0.7 distribute duration toward
  opening, climax (pour), and closing.
- **P1 audit pack** (stock-only expectations):
  - `timeline_invariants.json` — every clip has `trace`; duration matches target;
    0 overlap; must_include segs 1 & 6 present.
  - `broll_audit.json` — **broll_ratio high is expected/acceptable** (conceptual stock
    video is almost entirely B-roll); watch `unique_source` (repeated-source warning is
    informational here).
  - `caption_audit.json` — **0 gap / 0 overlap / 0 too-fast** (only seg4 ASR + the
    narrative/label cards generate captions).
  - `keyframe_grid.jpg` — 中文字幕 renders with **no mojibake** (narrative cards on
    seg1/seg6 are Chinese).
  - `visual_audit.json` — 0 mechanical findings.
- **Artifacts that MUST exist in the run dir:** `artifact_manifest.json`,
  `build_profile.json`, `assembly_plan.json`, `timeline_build.json`,
  `editor_review.json`, `verify_result.json`, and the 5 audit artifacts
  (`timeline_invariants.json`, `broll_audit.json`, `caption_audit.json`,
  `keyframe_grid.jpg`, `visual_audit.json`), plus `final.mp4`, `music_structure.json`,
  `subtitles.srt`, `generated_mv_script.json`, `state.json`.

## Branch coverage summary (which segment exercises what)

| Branch dimension | Covered by |
|---|---|
| timeline_source `fixed` | seg1, seg2, seg6 |
| timeline_source `beat` | seg3, seg4, seg5 |
| layout `single` / `montage` | single: 1,2,4,6 · montage: 3,5 |
| pace `hold` / `fast` | hold: 1,2,4,6 · fast: 3,5 |
| text_layer `narrative` | seg1, seg6 |
| text_layer `label` | seg3 |
| text_layer `subtitle:"auto"` (ASR) | (removed — invalid on pure stock; see §8/C5) |
| text_layer `none` (string) | seg5 (keeps facets at warn 29/30) |
| text_layer dict-none `{none,reason}` | seg2, seg4 (full-facet, no on-screen text) |
| audio `music` | seg1,3,5,6 |
| audio `diegetic` (keep audio) | seg2 |
| audio `duck` (sidechain) | seg4 |
| must_include (conceptual) + review_required | seg1, seg6 |
| review_required only | seg2 |
| editing_grammar role hero/mood/support/bridge | hero: 1,4 · mood: 2,6 · support: 3 · bridge: 5 |
| beat_alignment none/music/emotion/thematic | none:1,2 · music:3,5 · emotion:4 · thematic:6 |
| compressibility locked/flexible/expendable | locked:1,4,6 · flexible:2,3 · expendable:5 |
| fallback_policy `stock_bridge` | all 6 (the legitimate conceptual-stock route) |

## 8. First real E2E run (2026-06-08) — results & findings

The full chain was run for real (ffmpeg + Pexels + yt-dlp + Ollama all present):
`runtime.py run --project stock-story-e2e`. The chain executed end-to-end and
produced `final.mp4` (36.6 MB, 1920×1080 30fps). This run is what surfaced the
corrections in §2/C4/C5 above. Three engine/runtime bugs were fixed *because of*
this test case; two are test-case design findings; one is a hardening candidate.

### Engine/runtime bugs found & FIXED
- **B1 — runtime category resolution (chaining bug).** `runtime_orchestrator.py`
  hardcoded the global `examples/material_categories.json` and only fell back to the
  project map when the global was *absent*. A project's own `categories_ref`
  vocabulary was therefore never used, so `contract-run` failed at `validate_contract`
  ("category 不在地圖規範詞彙"). FIXED: resolution now prefers
  `categories_ref` → run dir → project input → global default.
- **B2 — `video_tools.py validate` crashed (`NameError: GRADE_PRESETS`).** Constants
  `GRADE_PRESETS` / `BGM_MOODS` were used by `cmd_validate` but never imported. FIXED.
- **B3 — `video_tools.py` Windows UTF-8 crash.** Printing the validate report (and any
  emoji/CJK) raised `UnicodeEncodeError` on cp950 because, unlike `runtime.py`,
  `video_tools.py` never reconfigured stdout to UTF-8. FIXED (same reconfigure block).

### Verify result (corrected contract)
First run (with `must_include` bookends + `subtitle:auto`): **score 64, FAIL** —
`script_coverage 66` (missing [1,6]), `subtitle_accuracy 0`, `audio_levels 50`.
After the §2 corrections the expected score is ~**92.5 PASS** (parity with the
`coffee` baseline), with `audio_levels` ~50 remaining as the only sub-100 dimension.

### Test-case design findings (corrected in the contract)
- **F1 — must_include vs pure stock (honesty guard).** `stock_first._can_use_stock`
  blocks stock for ANY `must_include`. Conceptual bookends must NOT carry
  `must_include` if you want stock to fill them. (Corrected: removed.)
- **F2 — subtitle:"auto" needs real speech.** ASR on silent stock = 0 captions →
  `subtitle_accuracy 0` + a `[Music]` stub SRT. (Corrected: seg4 → dict-none.)

### Hardening candidates (NOT changed — for the user to decide)
- **H1 — must_include unfilled should BLOCK, not silently drop.** When a `must_include`
  segment ends with no source (honesty guard refused stock AND no local material),
  the renderer skips it and the run continues to a low `script_coverage` instead of
  pausing with `next_action=await_material` / "must_include unfilled". Roadmap C0
  ("runtime must not silently invent/skip decisions") argues this should be a blocking
  review point at Node 8/11.
- **H2 — music resolver grabs stray repo-root mp3.** `_resolve_music_path` globs
  `REPO_ROOT/*.mp3` and picked up a leftover `Cinematic Corporate ….mp3` instead of
  fetching the contract's `music.query` ("warm hopeful acoustic morning instrumental").
  This also explains `audio_levels 50` (full-volume unrelated track). Convergence
  hygiene: the resolver should not scan the repo root, and the stray mp3 should not
  live there.
