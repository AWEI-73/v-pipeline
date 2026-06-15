# Decision Log: SRP1 Hardening, SRP2/3 Integration, and AR1 Refactoring

**Date:** 2026-06-16  
**Status:** APPROVED  
**Participants:** Antigravity (Agent), User, Codex (Advisor)

---

## Context

Following the course correction on 2026-06-14, the Hermes Video Pipeline has transitioned to a strict, material-aware planning system where evidence correctness is paramount. As we introduced automatic timeline structuring capabilities—specifically **SRP1 (Segment Sequence Planner)** and **SRP2 (Opening Hook Planner)**—the complexity within the core orchestration loop in `run_mv` reached a critical threshold, leading to:
1. **Accidental Complexity**: Dict mutations, runtime VLM hooks, and time-snapping rules were tightly coupled.
2. **Lineage Drift**: Early implementations of sequence compilers inadvertently generated default metadata values (like setting `is_photo=False` on video segments), which diluted the lineage evidence needed for downstream audits.
3. **Silent Failure Risks**: Catching generic `Exception` wrappers in the beat sequence compiler allowed programming errors to fail silently into fallback timelines, degrading diagnostic trace quality.

To resolve these issues while continuing to build out the story arc planner (SRP3), we executed a series of hardening, refactoring (AR1), and integration steps.

---

## Decisions

### 1. Hardening Evidence Lineage (SRP1)
We enforced a strict "copy-only-if-exists" contract on all asset evidence fields (`is_photo`, `scene_id`, `retrieval_score`, `visual_family`, `angle_scale`, `kenburns`, `caption`, `function`):
* **No Default Generation**: If the source slot lacks a field (e.g. `is_photo`), neither the derived shot in the compilation pool nor the final beat clip shall contain that field.
* **Exact Window Preservation**: `segment_pool_from_plan` retains the exact `extract_start` and `extract_dur` properties of source slots, preventing float-rounding mismatches.

### 2. Narrow Graceful Fallback catching
We restricted the exception handling block for auto-sequence compilation:
* **Narrow Catch**: Only catch predicted domain-logic exceptions—specifically `ValueError` and `TypeError` (e.g. librosa failed to find beats, or empty clips returned). These trigger a fallback to original slots + record a diagnostic trace.
* **Bubbling Uncaught Exceptions**: Any `RuntimeError`, `KeyError`, or `NameError` must propagate upward loudly to ensure code quality issues are caught immediately.
* **Manual Recipes**: Manual beat recipes remain untouched by the try-except wrapper and fail loudly on all exceptions.

### 3. run_mv Runtime Planning Extraction (AR1 Refactoring)
To address the size and cognitive load of the 400-line `run_mv` god-function, we extracted its logical phases into isolated, stateless private helper functions:
* `_plan_story_timeline`: Manages the per-segment selection loop, auto/manual sequence compilation, anti-presentation checks, and `shared_history` updates.
* `_apply_opening_bookend`: Integrates manual BR1 and auto SRP2 opening planning, including the dynamic `target_sec` budget trimming.
* `_apply_ending_bookend`: Prepend ending sequence (BR4).
* `_finalize_timeline`: Computes exact clip edit points and snaps to the music beat grid.

*Constraint*: This is a zero-behavior-change refactoring locked by characterization tests in `tests/test_ar1_run_mv_characterization.py`.

### 4. Whole-Film Target Budget Snapping (SRP2)
Auto-opening sequences must respect the whole-film budget (`target_sec`):
* If the story duration plus the requested auto-opening duration exceeds `target_sec`, the helper `trim_opening_for_budget` dynamically drops context beats, then the title reveal, and finally shortens the hook.
* Manual openings bypass this budget trimming, allowing explicit user overrides.

### 5. Shallow Emotional Arc Weights (SRP3)
We introduced a deterministic, whole-film level arc planner:
* `story_arc_planner.plan_story_arc` assigns emotional intensity and weight multipliers based on segment order (setup -> challenge -> progression -> climax -> resolution).
* Climax segments are weighted higher than setup, directing `allocate_segments` to allocate more duration budget to climax shots.
* Applied atomically on a trial copy before allocation, ensuring original scripts are never mutated.

---

## Consequences

* **Zero Regressions**: The 1225-test regression suite is fully green. The behavior of existing timeline planning, bookends, and rendering remains byte-for-byte identical.
* **Low Diagnostic Friction**: Fallback traces are clearly written into the segment and entry results, and programming errors bubble up immediately, allowing quick debugging.
* **Clean Codebase**: `run_mv` is reduced to a clean 110-line orchestrator, preparing the system for future extension without technical debt accumulation.
* **Database as Truth**: Live VLM scoring is deprecated in favor of reading pre-analyzed `project_material_map.json` assets, keeping compile runs extremely fast and offline-capable.
