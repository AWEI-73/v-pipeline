# Decision: CapCut-assisted finishing forward test

Date: 2026-07-15
Status: accepted (bounded verified scope)
Scope: Stage 6 render candidate / Stage 9 bounded finishing / Computer Use
Superpowers phase: execute

## SPEC

Requirement:

Test CapCut Desktop as the primary high-quality finishing backend for reviewed
Hermes picture decisions, with the local renderer retained as the unattended
fallback and Hermes Verify retained as delivery authority.

Why:

Three.js, Remotion, and OpenMontage can reach high quality but require repeated
effect-specific development and tuning. CapCut offers a stronger ready-made
finishing surface for native effects, music, text, and visual judgment.

Direction:

Extend the verified clone-skeleton draft route. Use deterministic draft mutation
for timeline/text/audio data and Computer Use only for bounded free-asset effect,
music, preview, and export actions. Return every export to Stage 7 Verify.

Build/buy principle:

- Hermes builds and owns intent-bearing truth: story, material evidence, picture
  lock, approved text, Verify, and delivery decisions.
- Mature effects, music libraries, and NLE finishing are taste-crystallized
  capabilities; integrate them before proposing a new generic renderer.
- Remotion remains appropriate for project-specific effects that a mature
  provider does not supply. CapCut is a hybrid integration: Hermes owns intent
  and evidence while CapCut executes bounded finishing.

Non-goals:

- Do not make CapCut the source of story, material, subtitle, or picture truth.
- Do not automate a 540-second edit from an empty CapCut project.
- Do not copy the private Video Autopilot Kit operation core.
- Do not require paid, Pro, cloud-AI, or community-template assets.
- Do not create a second orchestrator.

## DO

Files / modules:

- Reuse `video_pipeline_core/capcut_backend.py` and its clone-skeleton serializer.
- Add a finishing handoff/receipt surface only after the real pilot proves the fields.
- Add a concise CapCut finishing Skill only after the real pilot is verified.

Function-level plan:

Stage a verified CapCut draft from a reviewed Hermes asset. Open it in CapCut,
apply one bounded free effect and one free instrumental track, export locally,
record the exact UI choices/deviations, then run Hermes rendered-product QA and
final-product verification.

Data / interface changes:

Pilot contract: `.tmp/capcut_finishing_pilot/capcut_finishing_handoff.json`.
The durable schema will be based on actual fields used successfully in the pilot.

Reference-repo findings:

- `reference repo/video-autopilot-kit-main` exposes useful public patterns for
  CapCut draft I/O/synchronization, text/audio/effect mutations, and post-export
  QA.
- Its export-only operator flow, template/catalogue browsing, paywall map, and
  daily-limit behavior depend on a closed or absent operation core. Those parts
  cannot be treated as reusable source code or a reproducible Hermes backend.
- Hermes therefore does not install or fork that repository as a second runtime.
  It keeps the existing `capcut_backend.py` serializer, uses bounded Computer
  Use for visible GUI decisions, and brings the export back to Hermes Verify.

Migration / compatibility:

This extends the verified P3 CapCut draft serializer. ffmpeg/local rendering
remains available and existing runs do not change backend automatically.

## VERIFY

Pre-checks:

- Installed CapCut version and editable draft format are recorded.
- Source hash, duration, resolution, and picture mutation policy match the handoff.
- CapCut project uses a unique name and does not overwrite an existing draft.

Tests:

- `python -m unittest tests.test_capcut_backend -v`
- Focused tests for any new handoff validator or command surface.
- Registry/skill audits only after a durable tool or Skill is added.

Manual checks:

- CapCut opens the draft and displays the correct 40-second source.
- The chosen asset is free and does not trigger a paid export gate.
- Effect intent remains subtle; faces and baked text remain readable.
- Music is audible, instrumental, restrained, and fades out at the end.

Regression risks:

- CapCut UI and free-asset availability are version/region dependent.
- Draft edits while CapCut is running may be overwritten by auto-save.
- GUI automation may accidentally cross a paid or cloud boundary.
- A CapCut export can look polished while violating picture or text truth.

## Decision Notes

Accepted because:

The 40-second forward test completed the intended round trip: reviewed Hermes
source -> deterministic CapCut draft repair -> bounded native effect/music UI
operation -> local export -> Hermes Stage 7 verification. Deterministic truth
and Verify remained inside Hermes while CapCut supplied only finishing value.

Tradeoffs:

The high-quality route is interactive and less reproducible than the local
renderer. The handoff and receipt must make the remaining uncertainty visible.

Verified observations:

- Actual desktop version: CapCut 8.9.1.3802.
- Free native `膠片框` / `影片框` effect exported without a Pro gate.
- Native `Warm Piano` appeared usable but export preflight identified it as
  Pro. It was removed; no payment, subscription or bypass was attempted.
- A local instrumental file could be placed at -16.5 dB with a 2-second fade
  and exported with the free effect.
- Computer Use completed the bounded UI operation, export, and local read-back.
- CapCut UI insertion used the current playhead and created duplicate/wrongly
  placed tracks; deterministic draft placement was required for exact timing.
- The existing skeleton leaked remote catalogue identity into a local video.
  CapCut rewrote its path to an online cache until the serializer cleared the
  remote identity fields.

Forward-test evidence:

- Source SHA-256: `A92EE5E6F3D62E7CB67FF618EDF814CE3615E761553144B332BD556C91D4C63D`
- Export SHA-256: `E5E3265BE289036C28E89166CF5F520647C3E192A0E3B404FC405F0C0652C0AE`
- Export probe: H.264 1920x1080 30 fps plus AAC stereo 44.1 kHz,
  40.009 seconds.
- Rendered product QA: PASS, exit 0.
- Final-product Verify: PASS, exit 0, 12 visual samples plus extracted audio.
- Perception field: PASS, exit 0, 71 samples, four wall pages, zero gaps.
- Focused backend tests: 19/19 PASS.

Remaining UNKNOWN:

- owner creative/taste approval;
- delivery-compatible approval for the CC BY-NC-ND 3.0 local music candidate;
- unattended 540-second operation, dialogue ducking, subtitle editing,
  multi-effect composition, and cross-version/region asset availability.

## Git / Retrieval

Related files:

- `video_pipeline_core/capcut_backend.py`
- `tests/test_capcut_backend.py`
- `docs/capcut-pipeline-integration-design.md`
- `docs/archive/decisions/2026-06-08-p3-capcut-draft-serializer.md`
- `docs/archive/decisions/2026-06-12-capcut-text-audio-gui-gate.md`
- `.tmp/capcut_finishing_pilot/capcut_finishing_handoff.json`
- `.tmp/capcut_finishing_pilot/export/capcut_exported.mp4`
- `.tmp/capcut_finishing_pilot/qa_run/rendered_qa/rendered_product_qa.json`
- `.tmp/capcut_finishing_pilot/qa_run/final_verify/final_product_verify_bundle.json`
- `.tmp/capcut_finishing_pilot/qa_run/perception/perception_field_report.json`
- `skills/capcut-assisted-finishing.md`

Related commits:

- `aca8f90` clone-skeleton draft serializer

Graphify anchors:

CapCut, Computer Use, Stage 6, Stage 7 Verify, Stage 9 finishing,
capcut_finishing_handoff

Search tags:

decision-log, spec-do-verify, capcut, computer-use, finishing-backend,
render-candidate, forward-test
