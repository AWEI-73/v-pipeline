# Decision: D1 Single-Segment Gate & Photo (Ken Burns) Fallback

Date: 2026-05-29
Status: verified
Scope: content_qa.py / video_pipeline.py / pipeline() retry loop
Superpowers phase: execute

## SPEC

### Requirement:
- **D1 Strict Single-Segment Gate**: Prevent "average score dilution" where a single bad segment is ignored because the overall average score passes. If any individual segment scores `< 60` under Content QA, the pipeline must fail the gate and selectively trigger retries for that segment.
- **Node-level Photo Fallback (Ken Burns)**: Graduation videos are heavily composed of student-submitted photos rather than videos. When a video segment fails VLM alignment and video candidates are exhausted, the orchestrator must automatically switch to `"photo"` mode, search stock photos, and use `video_tools.py kenburns` to render a premium panning/zooming clip.
- **Unfixable Escape & Localized Chinese Guidance**: If both video and photo searches exhaust or fail, output a beautiful localized shooting instruction for that segment (e.g. `"無人深空: 已暫用後備畫面。建議補拍：...特寫/空鏡，中景，時長 5 秒，命名為 seg2_user.mp4"`), write it to `qa_report.json` under `material_gap_guidance`, and allow the pipeline to exit successfully (exit 0) with warnings instead of failing or looping.

### Why:
- Abstract poetic terms and student-submitted assets often have zero exact video coverage. Photos have 10x higher stock accuracy. Fallback-to-photo maintains premium visuals while resolving search deadlocks.
- Average score dilution allowed bad segments (VLM score as low as 10) to slip into final videos just because other segments scored 100. A strict segment gate ensures uniform high-quality visuals.

### Direction:
- Strict single-segment gate enabled by default (`--no-strict` to disable).
- Auto-transition from `video` to `photo` type inside the retry loop upon video candidates exhaustion.
- Detailed Chinese warnings specify segment name, search terms, segment duration, and expected upload filename `seg{n}_user.mp4`.
- Override final pipeline status to success (exit 0) if the only failing issues are unfixable material gaps, so automated pipelines can pass.

---

## DO

### Files / modules:
- `content_qa.py` (strict pass check and issues payload generation)
- `video_pipeline.py` (retry loop, fetch_photo_candidates, photo-fallback transitions, unfixable warnings, pass override, command line parser)

### Function-level plan:
- **`content_qa.py`**:
  * Set `qa["pass"] = False` if strict mode is active (`not args.no_strict`) and `low_segs` (score `< 60`) is not empty.
  * In the issues loops, force `content_alignment` as a failed dimension if strict mode is active and `low_segs` exists, even if its overall average score is $\ge 80$.
- **`video_pipeline.py`**:
  * Implement `fetch_photo_candidates(search_query, verbose)` utilizing `run_tool(["pexels-search", ...])` and `pixabay_search()`.
  * Propagate `--no-strict` from `video_pipeline.py`'s command line options into `pipeline()` and `compose_and_qa()`.
  * Refactor retry loop: when a segment's video candidates are exhausted (`new_pick is None`), change `media_pref = "photo"` in script and candidates list, call `fetch_photo_candidates()`, reset `exclude[n]`, and trigger another repick.
  * If photo candidates are also exhausted, populate `unfixable[n]` with Chinese localized guidance text.
  * Write visual warning blocks to console and save them into `qa_report.json` under `material_gap_guidance`.
  * Scan final issues list: if the only remaining failures are `content_alignment` on `unfixable` segments, override `qa["pass"] = True` and print a warning.

---

## VERIFY

### E2E Test 1: Successful Self-Reflection Fix
- **Script**: `mock_script.json` (Segment 2 has abstract query `"將散未散"` which initially scored 10).
- **Results**:
  * **Attempt 0**: `seg2` scores `10`. Overall score is `86.5`, but since strict mode is active, **`qa_pass` sets to `False`** and triggers retries. (Strict gate confirmed working!).
  * **Attempt 1**: Re-picked next video (`cand 9`). Still failed VLM checks (`score=10`).
  * **Attempt 2**: Re-picked video (`cand 12`). Success! `seg2` rose to `60` under VLM evaluation.
  * **Result**: Overall score reaches `94.0`, all segments pass. **Pipeline successfully exits with code 0!**

### E2E Test 2: Material Exhaustion & Localized Guidance
- **Script**: `mock_script_exhausted.json` (Segment 2 has impossible/garbage query. Initial video candidate mock set to 1 to force exhaustion).
- **Results**:
  * **Attempt 0**: Initial run. `seg2` scores `10`. Overall gate fails.
  * **Attempt 1**: Re-picking videos. Since candidates are exhausted, it prints:
    `[retry] seg2 video candidates exhausted or rejected. Falling back to PHOTO mode.`
    Swaps `media_pref` to `"photo"`, fetches photos, downloads photo candidate `1`, and calls `kenburns`. High-quality dynamic pan/zoom photo rendered cleanly.
  * **Attempt 2**: Since the photo also scored `10`, it attempts another photo repick. Photo candidates are exhausted, triggering:
    `seg2 unfixable — photo candidates exhausted`
  * **E2E Result**:
    Prints high-visibility guidance block:
    ```
    ============================================================
    ⚠️  【素材缺口與拍攝指引】 ⚠️
    ============================================================
      - 無人深空: 已暫用後備畫面。建議補拍：xyzlmnopgarbagequerythatwillreturnabsolutelyzeroresults特寫/空鏡，中景，時長 5 秒，命名為 seg2_user.mp4
    ============================================================

    [warning] Pipeline passed with material gap warnings.
    ```
    Overrode overall status to `qa_pass: true`, and the script exited cleanly with **code 0**! (Unfixable escape and guidance confirmed working!).

### Regression checks:
- Executed the full control panel test suite inside WSL:
  `============================= 114 passed in 0.48s ==============================`
  All 114 unit tests pass successfully. Decoupling and interfaces preserved.

---

## Decision Notes

### Accepted because:
- Graduation videos are predominantly photo-based, making photo fallback a critical real-world feature.
- Ken Burns panning/zooming on photos maintains high-end production aesthetics.
- Programmatic localized warnings give students direct and intuitive action items to improve their videos manually.

### Tradeoffs:
- Photo search and Ken Burns rendering take computational time, but are much faster and cheaper than failure loops.

---

## Git / Retrieval

### Related files:
- `content_qa.py` (gate updates)
- `video_pipeline.py` (retry loop, fallback, unfixable guidance)

### Related commits:
- `d883873` (feat: D1 strict gate, photo fallback (Ken Burns) and localized Chinese shooting instructions)

### Graphify anchors:
- Hyperedge: "D1 single-segment gate + photo fallback routing"
- Community 0 "Pipeline Orchestrator Core": `run_content_qa`, `compose_and_qa`, `pipeline()`
- Community 1 "Content QA & Retry Decisions": `content_qa.py` pass check, `unfixable` warnings
- Node: `fetch_photo_candidates()`, `video_tools.py kenburns`

### Search tags:
decision-log, d1, single-segment-gate, photo-fallback, ken-burns, pexels-search, pixabay-search, shooting-guidance, material-gap-guidance, unfixable, exit-0
