# Canon 67 150-Second L1 Picture Composition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the accepted 42-clip L0 v2 selection into one silent, reviewable 150-second L1 picture candidate through the registered Capability execution path.

**Architecture:** Keep `cap.material-map.rough-cut-plan-execute.v1` as the only picture renderer. Reuse the already tuned smooth photo-motion behavior in `mv_cut` by extracting its pure filter policy into one shared core module, then connect that module to the registered rough-cut executor; do not create another renderer. Prove mixed video/still motion with a four-second real-material probe, execute the frozen 150-second plan, and run registered final-product verification. L1/L5 evidence may describe quality, but only the owner can approve picture taste.

**Tech Stack:** Python 3.11, `unittest`, ffmpeg/ffprobe, `video_tools.py capability-run`, Material Map rough-cut executor, final-product verify, rendered-product QA, perception-field-check.

## Global Constraints

- Exactly three sections remain: `discipline_and_arrival`, `technical_craft`, and `life_and_bonds`.
- Each section remains 50.0 seconds; total duration is `150.0 +/- 0.5` seconds.
- Use the accepted 42 deterministic `clip_id` values: 26 video windows and 16 still-image holds.
- Picture only: source audio is not mapped; do not add music, ASR, subtitles, effects, title cards, transitions, or generated assets.
- The sealed L0 v2 packet and verdict are immutable. Carry the seven-person table-tennis correction from the integrator verdict into L1 metadata.
- Reuse the existing smooth `slow_push`, `pan_right`, `detail_push`, and `pan_left` treatments; do not reimplement or replace them with the older `vt_effects` zoompan path.
- Upgrade the registered existing executor; do not add a second renderer, private ffmpeg route, route runner, or run-local script.
- Run the full suite once, at the end, only because production code changes in Task 1.
- `human_creative_approval=false` and `final_delivery_claimed=false` throughout worker execution.

---

### Task 1: Connect the existing smooth photo-motion factory to the registered rough-cut executor

**Files:**
- Create: `video_pipeline_core/still_motion.py`
- Modify: `video_pipeline_core/mv_cut.py:346-389`
- Modify: `video_pipeline_core/edit_artifacts.py:1-48`
- Modify: `tools/rough_cut_plan_execute.py:18-307`
- Test: `tests/test_still_motion.py`
- Test: `tests/test_rough_cut_plan_execute.py`

**Interfaces:**
- Consumes: each clip record with `source_path`, `source_type`, `start_sec`, `duration_sec`, `clip_id`, and `asset_id`.
- Produces: one shared pure still-motion API, unchanged MV behavior, unchanged rough-cut CLI, correct mixed video/still-motion argv, stable 30 fps output, requested still duration, and trace fields in `rough_cut_preview_report.json`.

- [ ] **Step 1: Write red tests for still input argv, duration policy, trace retention, and real mixed rendering**

Add tests equivalent to:

```python
def test_ffmpeg_command_uses_shared_motion_for_requested_still_duration(self):
    clips = [
        {"source_path": "motion.mp4", "source_type": "video", "start_sec": 1.0, "duration_sec": 2.0},
        {"source_path": "portrait.jpg", "source_type": "photo", "start_sec": 0.0, "duration_sec": 2.0},
    ]
    command = build_rough_cut_ffmpeg_command(clips, out=Path("out.mp4"), fps=30)
    image_index = command.index("portrait.jpg")
    self.assertIn("-loop", command[:image_index])
    self.assertIn("-t", command[:image_index])
    self.assertNotIn("-ss", command[command.index("-loop", 1):image_index])
    filtergraph = command[command.index("-filter_complex") + 1]
    self.assertIn("scale=w='2560*", filtergraph)
    self.assertNotIn("zoompan", filtergraph)

def test_mixed_video_and_still_render_is_four_seconds_and_silent(self):
    from tools.rough_cut_plan_execute import execute_rough_cut_plan
    from video_pipeline_core.platform_tools import resolve_ffmpeg, resolve_ffprobe

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        motion = root / "motion.mp4"
        photo = root / "photo.jpg"
        plan = root / "plan.json"
        out = root / "out.mp4"
        report = root / "report.json"
        subprocess.run([
            resolve_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc=duration=2:size=320x180:rate=30",
            "-pix_fmt", "yuv420p", str(motion),
        ], check=True)
        subprocess.run([
            resolve_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc=size=640x360:rate=1",
            "-frames:v", "1", str(photo),
        ], check=True)
        plan.write_text(json.dumps({"clips": [
            {"track": "video", "clip_id": "v1", "source_type": "video", "source_path": str(motion), "start_sec": 0.0, "duration_sec": 2.0},
            {"track": "video", "clip_id": "p1", "source_type": "photo", "source_path": str(photo), "start_sec": 0.0, "duration_sec": 2.0, "still_treatment": {"mode": "slow_push"}},
        ]}), encoding="utf-8")
        payload = execute_rough_cut_plan(plan, out, report, width=320, height=180, fps=30)
        probe = subprocess.run([
            resolve_ffprobe(), "-v", "error", "-count_frames",
            "-show_entries", "stream=codec_type,duration,nb_read_frames",
            "-of", "json", str(out),
        ], check=True, capture_output=True, text=True)
        streams = json.loads(probe.stdout)["streams"]
        video = next(item for item in streams if item["codec_type"] == "video")
        self.assertTrue(payload["ok"])
        self.assertEqual(int(video["nb_read_frames"]), 120)
        self.assertAlmostEqual(float(video["duration"]), 4.0, places=2)
        self.assertFalse(any(item["codec_type"] == "audio" for item in streams))
        self.assertEqual([item["clip_id"] for item in payload["clips"]], ["v1", "p1"])
        self.assertEqual(payload["clips"][1]["still_treatment"]["mode"], "slow_push")
        early, late = root / "early.png", root / "late.png"
        for at, target in ((2.1, early), (3.8, late)):
            subprocess.run([
                resolve_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
                "-ss", str(at), "-i", str(out), "-frames:v", "1", str(target),
            ], check=True)
        self.assertNotEqual(early.read_bytes(), late.read_bytes())
```

The real-render test must also assert that the report preserves both `clip_id`
values, marks the image clip as a still, records its `still_treatment`, and
produces different early/late still-frame hashes so a static hold cannot pass.

- [ ] **Step 2: Run the focused test and capture RED evidence**

Run:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_rough_cut_plan_execute -v
```

Expected: exit `1` because the current executor probes still images as
zero-duration video and does not consume the existing smooth motion policy.

- [ ] **Step 3: Implement the minimal existing-tool upgrade**

Create a small shared pure module, preserving the current tuned behavior:

```python
# video_pipeline_core/still_motion.py
from pathlib import Path
from typing import Any

STILL_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
STILL_TREATMENT_MODES = ("slow_push", "pan_right", "detail_push", "pan_left")

def is_still_source(source_path: str | Path, source_type: str | None = None) -> bool:
    declared = str(source_type or "").casefold()
    return declared in {"photo", "image", "still"} or Path(source_path).suffix.casefold() in STILL_SUFFIXES

def still_motion_strength(duration_sec: float) -> dict[str, float]:
    seconds = float(duration_sec or 0.0)
    if seconds >= 12:
        return {"slow": 0.05, "detail": 0.12, "pan_zoom": 1.08}
    if seconds >= 8:
        return {"slow": 0.08, "detail": 0.16, "pan_zoom": 1.10}
    return {"slow": 0.22, "detail": 0.32, "pan_zoom": 1.18}

def build_still_motion_filter(
    duration_sec: float,
    *,
    treatment: dict[str, Any] | None = None,
    kenburns: bool = True,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
) -> str:
    hold = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,"
        f"fps={fps},format=yuv420p"
    )
    if not kenburns or (treatment or {}).get("mode") == "hold":
        return hold
    frames = max(1, round((duration_sec or 1.0) * fps))
    progress = max(1, frames - 1)
    t = f"(n/{progress})"
    mode = (treatment or {}).get("mode", "slow_push")
    strength = still_motion_strength(duration_sec)
    work_width, work_height = width * 2, height * 2
    if mode in {"pan_right", "pan_left"}:
        zoom = f"{strength['pan_zoom']:.2f}"
        x = f"(iw-ow)*{t}" if mode == "pan_right" else f"(iw-ow)*(1-{t})"
        return (
            f"fps={fps},"
            f"scale=w='{work_width}*{zoom}':h='{work_height}*{zoom}':force_original_aspect_ratio=increase:eval=frame,"
            f"crop={work_width}:{work_height}:x='{x}':y='(ih-oh)/2',"
            f"scale={width}:{height},setsar=1,format=yuv420p"
        )
    delta = strength["detail"] if mode == "detail_push" else strength["slow"]
    zoom = f"(1+{delta:.2f}*{t})"
    return (
        f"fps={fps},"
        f"scale=w='{work_width}*{zoom}':h='{work_height}*{zoom}':force_original_aspect_ratio=increase:eval=frame,"
        f"crop={work_width}:{work_height}:x='(iw-ow)/2':y='(ih-oh)/2',"
        f"scale={width}:{height},setsar=1,format=yuv420p"
    )
```

Make the following bounded changes:

- Move, without changing default output, the current `_still_motion_strength`
  and `_photo_vf` logic into the shared module. Keep thin compatibility
  wrappers in `mv_cut.py` so existing callers/tests see the same behavior.
- Make `edit_artifacts.py` import the shared `STILL_TREATMENT_MODES`; remove its
  duplicate private tuple without changing rotation order.
- `_clips()` carries `clip_id`, `source_type`, and `source_sha256` into the render/report record.
- `_adjust_clip_durations_to_source()` does not clamp a still to ffprobe duration; it retains the requested positive duration and forces `start_sec=0.0`.
- `build_rough_cut_ffmpeg_command()` keeps the existing seek path for video, but gives a still input `-loop 1 -framerate <fps> -t <duration> -i <path>`.
- `_filtergraph()` uses `build_still_motion_filter()` with the clip's frozen
  `still_treatment`, requested output size, and zero-based trim window; it
  preserves the existing video trim behavior.
- No new CLI, Capability ID, renderer module, dependency, or fallback path is introduced.

- [ ] **Step 4: Run focused and adjacent tests**

Run:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_still_motion tests.test_rough_cut_plan_execute tests.test_kenburns_smoothness tests.test_mv_cut tests.test_edit_artifacts tests.test_material_rough_cut -v
```

Expected: exit `0`.

- [ ] **Step 5: Audit the registered tool binding**

Run:

```powershell
C:/Users/user/miniconda3/python.exe video_tools.py registry-audit --json
C:/Users/user/miniconda3/python.exe video_tools.py dispatch-capabilities --id cap.material-map.rough-cut-plan-execute.v1 --json
```

Expected: both exit `0`; the Capability still binds to `tools/rough_cut_plan_execute.py` and no orphan/duplicate finding is created.

- [ ] **Step 6: Commit only the bounded capability change**

```powershell
git add -- video_pipeline_core/still_motion.py video_pipeline_core/mv_cut.py video_pipeline_core/edit_artifacts.py tools/rough_cut_plan_execute.py tests/test_still_motion.py tests/test_rough_cut_plan_execute.py
git commit -m "feat: reuse smooth photo motion in rough cut previews"
```

### Task 2: Verify frozen L1 inputs and initialize accountability once

**Files:**
- Read: `.tmp/canon67_150s_picture_first_longform/l1_picture_candidate/inputs/*.json`
- Read: `.tmp/canon67_150s_picture_first_longform/l0_revision_v2/proposal/l0_selects_proposal_v2.json`
- Read: `.tmp/canon67_150s_picture_first_longform/l0_revision_v2/review/integrator_verdict_v2.json`
- Create by command: `.tmp/canon67_150s_picture_first_longform/l1_picture_candidate/accountability/**`

**Interfaces:**
- Consumes: committed execution companion and three pre-frozen L1 input artifacts.
- Produces: one immutable accountability run instance.

- [ ] **Step 1: Read back all frozen hashes and 42 external source hashes**

Verify the exact hashes pinned by the work order and companion. Verify `42/42` source files exist and match `inputs/source_hash_manifest.json`. Abort before initialization on any mismatch.

- [ ] **Step 2: Initialize exactly once**

```powershell
C:/Users/user/miniconda3/python.exe video_tools.py capability-run --initialize --contract docs/construction-guides/work-orders/2026-07-13-canon67-150s-l1-picture-composition.execution.json --json
```

Expected: exit `0`. Do not delete or recreate accountability state.

### Task 3: Prove the mixed-media public path with real inputs

**Files:**
- Create by accountable command: `.tmp/canon67_150s_picture_first_longform/l1_picture_candidate/probe/mixed_media_probe.mp4`
- Create by accountable command: `.tmp/canon67_150s_picture_first_longform/l1_picture_candidate/probe/rough_cut_preview_report.json`

**Interfaces:**
- Consumes: `inputs/mixed_media_probe_rough_cut_plan.json`.
- Produces: four-second, 640x360, 30 fps, silent video/smooth-photo-motion proof.

- [ ] **Step 1: Execute `L1.mixed-media-render-probe` exactly once through `capability-run`**

Use the exact command in the work order. Expected: exit `0` with a PASS receipt.

- [ ] **Step 2: Probe objective shape and visible still motion**

Require duration `4.0 +/- 0.1` seconds, exactly 120 video frames at 30 fps, no
audio stream, two traceable clips, a still occupying its full requested two
seconds, and different early/late still-frame hashes. If this fails, stop as
`STRUCTURAL_MIXED_MEDIA_L1_RENDER_CAPABILITY_GAP`; do not render 150 seconds.

### Task 4: Render and verify the 150-second silent picture candidate

**Files:**
- Create by accountable command: `.tmp/canon67_150s_picture_first_longform/l1_picture_candidate/final.mp4`
- Create by accountable command: `.tmp/canon67_150s_picture_first_longform/l1_picture_candidate/rough_cut_preview_report.json`
- Create by accountable command: `.tmp/canon67_150s_picture_first_longform/l1_picture_candidate/l5/final_product_verify/**`

**Interfaces:**
- Consumes: `inputs/combined_rough_cut_plan.json` and the PASS probe receipt.
- Produces: 1280x720 H.264, 30 fps, silent candidate and registered L5 verification bundle.

- [ ] **Step 1: Execute `L1.render-150s-picture-candidate` exactly once**

Expected: exit `0`, report `ok=true`, 42 clips, rendered duration
`150.0 +/- 0.5`, all 16 frozen motion treatments recorded, and no
source-duration adjustment for any still.

- [ ] **Step 2: Execute `L5.verify-150s-picture-candidate` exactly once**

Expected: exit `0` and `final_product_verify_bundle.json` with `pass=true`. No-audio-stream is the intended picture-only policy, not a missing-audio defect.

- [ ] **Step 3: Run bounded non-accountable evidence tools**

```powershell
C:/Users/user/miniconda3/python.exe tools/rendered_product_qa.py --run .tmp/canon67_150s_picture_first_longform/l1_picture_candidate --out-dir .tmp/canon67_150s_picture_first_longform/l1_picture_candidate/l5/rendered_product_qa --json
C:/Users/user/miniconda3/python.exe video_tools.py perception-field-check .tmp/canon67_150s_picture_first_longform/l1_picture_candidate/final.mp4 --out .tmp/canon67_150s_picture_first_longform/l1_picture_candidate/l5/perception
```

Expected: both exit `0`. These produce review evidence only and do not substitute for owner taste.

### Task 5: Build the L1/L5 owner review packet

**Files:**
- Create: `.tmp/canon67_150s_picture_first_longform/l1_picture_candidate/l1/picture_composition_report.json`
- Create: `.tmp/canon67_150s_picture_first_longform/l1_picture_candidate/l1/semantic_trace.json`
- Create: `.tmp/canon67_150s_picture_first_longform/l1_picture_candidate/l5/fatigue_and_repetition_report.json`
- Create: `.tmp/canon67_150s_picture_first_longform/l1_picture_candidate/review/owner_review_index.md`
- Create: `.tmp/canon67_150s_picture_first_longform/l1_picture_candidate/review/owner_verdict_template.json`
- Create: `.tmp/canon67_150s_picture_first_longform/l1_picture_candidate/accountability/attestations/L1.picture-technical-review.json`

**Interfaces:**
- Consumes: accepted L0 verdict, frozen plans, render report, verify bundle, QA, and perception wall.
- Produces: evidence-carrying owner packet that separates objective facts from agent taste findings.

- [ ] **Step 1: Write machine-readable trace and objective reports**

Prove all 42 `clip_id` values appear once and in accepted order; section durations are 50/50/50; overall duration is within tolerance; source audio is absent; the table-tennis observation uses seven people; no L0 sealed file changed. Report min/median/max shot duration, consecutive category/family runs, repeated source hashes, and any source-duration adjustment.

- [ ] **Step 2: Review the actual 150-second wall and candidate**

Classify findings as `objective` or `taste`. Record coordinates, evidence paths, owner capability, and rerun gates. Do not convert `rendered QA PASS` into a creative PASS.

- [ ] **Step 3: Write the six-field carry-forward and owner template**

For every proposed owner decision record: `decision`, `reason`, `evidence_refs`, `affected_stable_ids`, `downstream_effect`, and `decided_by`. Leave the owner decision unset and both approval flags false.

- [ ] **Step 4: Write the run-bound agent attestation**

Bind it to the run instance, contract hash, render hash, verify hash, review packet paths, and the exact agent identity available to the worker. This attests actual review; it does not claim owner approval.

### Task 6: Close technical evidence and stop for owner taste

**Files:**
- Create: `.tmp/canon67_150s_picture_first_longform/l1_picture_candidate/final/worker_report.md`
- Create: `.tmp/canon67_150s_picture_first_longform/l1_picture_candidate/final/command_log.json`
- Modify: `.tmp/canon67_150s_picture_first_longform/campaign_status.json`
- Modify: `HANDOFF_CURRENT.md`

**Interfaces:**
- Consumes: all Task 1-5 evidence.
- Produces: strict technical closure plus `WAITING_OWNER_150S_FINAL_PICTURE_VERDICT`.

- [ ] **Step 1: Run strict closure at the contract accountability root**

```powershell
C:/Users/user/miniconda3/python.exe tools/no_skip_execution_trace.py --run .tmp/canon67_150s_picture_first_longform/l1_picture_candidate --contract docs/construction-guides/work-orders/2026-07-13-canon67-150s-l1-picture-composition.execution.json --out-dir .tmp/canon67_150s_picture_first_longform/l1_picture_candidate/accountability --json
```

Expected: exit `0`. Do not use `final/strict_closure`; `accountability_root` is the canonical output boundary.

- [ ] **Step 2: Run focused checks and the full suite once**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_still_motion tests.test_rough_cut_plan_execute tests.test_kenburns_smoothness tests.test_mv_cut tests.test_edit_artifacts tests.test_material_rough_cut tests.test_capability_execution_contract tests.test_final_product_verify tests.test_rendered_product_qa -v
C:/Users/user/miniconda3/python.exe -m unittest discover -s tests
git diff --check
```

Expected: every command exits `0`. The full suite gets one attempt with a 1,200,000 ms outer timeout.

- [ ] **Step 3: Record final worker state**

Update the campaign pointer and Handoff to `WAITING_OWNER_150S_FINAL_PICTURE_VERDICT`; report the final video SHA-256 and review links. Keep `human_creative_approval=false` and `final_delivery_claimed=false`. Do not upload or promote the candidate.
