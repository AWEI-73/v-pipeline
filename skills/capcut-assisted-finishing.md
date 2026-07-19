---
name: capcut-assisted-finishing
description: Use when a reviewed Hermes picture candidate needs bounded high-quality finishing in CapCut Desktop, such as one or more native effects, licensed/local music, final preview, or export, while Hermes retains story, material, picture, text, Verify, and delivery authority.
---

# CapCut-Assisted Finishing Skill

Use this Skill only after the upstream Hermes decisions are concrete enough to
survive a round trip through a GUI editor. It is a Stage 6 candidate-render or
Stage 9 bounded-finishing backend, not a replacement for Stage 0-5.

## Tool Contract

<!-- TOOL_CONTRACT_START -->
{
  "version": 1,
  "skill": "capcut-assisted-finishing",
  "stage_owner": "capcut_assisted_finishing",
  "triggers": [
    "reviewed picture/text truth needs a bounded CapCut effect, music, preview, or export pass",
    "local renderer is an acceptable fallback but the owner requests a higher-quality interactive finishing surface"
  ],
  "canonical_tools": [
    {
      "tool": "video_tools.py capcut-draft",
      "when": "serialize a reviewed Hermes timeline into the provider-neutral CapCut draft handoff before bounded GUI finishing",
      "inputs": [
        "reviewed timeline_build.json",
        "unique project name",
        "local source media"
      ],
      "outputs": [
        "capcut_draft_manifest.json",
        "CapCut draft inputs"
      ],
      "stop_if": [
        "picture or text truth is not reviewed",
        "local media carries unresolved remote-catalogue identity",
        "the project name would overwrite an existing draft"
      ],
      "capability_id": "cap.capcut-assisted-finishing.draft.v1",
      "execution_class": "deterministic",
      "capability_role": "adapter",
      "loops": [
        "L2",
        "L3",
        "L4"
      ],
      "maturity": "bounded",
      "certified_scope": "reviewed local-media timeline to CapCut 8.x draft handoff"
    }
  ],
  "supporting_tools": [
    {
      "tool": "tools/rendered_product_qa.py",
      "when": "check the exported candidate for required media streams and objective render health",
      "inputs": [
        "CapCut export copied into a Hermes QA run folder"
      ],
      "outputs": [
        "rendered product QA report and frame evidence"
      ],
      "stop_if": [
        "required video or audio stream is missing",
        "decode or media-health checks fail"
      ]
    },
    {
      "tool": "tools/final_product_verify.py",
      "when": "return a CapCut export to the canonical Stage 7 Verify route",
      "inputs": [
        "CapCut export candidate"
      ],
      "outputs": [
        "final product verify bundle"
      ],
      "stop_if": [
        "visual or audio evidence cannot be produced"
      ]
    }
  ],
  "forbidden_tools": [
    "Do not start CapCut from a fuzzy whole-video request",
    "Do not let CapCut redefine story, material, picture, subtitle, roster, or factual truth",
    "Do not use paid, Pro, cloud-AI, or community-template assets without explicit owner authority",
    "Do not mutate draft JSON while CapCut is open",
    "Do not treat successful export as creative, legal, or delivery approval"
  ],
  "capability_namespace": "cap.capcut-assisted-finishing.*",
  "capability_lookup_owner": "capcut-assisted-finishing"
}
<!-- TOOL_CONTRACT_END -->

Shared hard boundary: read `skills/pipeline-boundary.md`. New fuzzy video work
still starts at Stage 0. CapCut receives a reviewed handoff; it never becomes a
second orchestrator.

## Authority Split

Hermes owns:

- product mode, story spine, coverage, Material Map, picture order and source windows;
- approved text/subtitles and factual identity;
- effect/music intent, legal status, Verify evidence and delivery gate.

CapCut owns only the bounded interactive finishing operation named in the
handoff: native effects, music placement/mixing, visual preview, and export.
Computer Use may operate those controls, but its clicks are execution evidence,
not canonical truth.

## Handoff Modes

Choose exactly one mode and record it in the handoff:

- `flattened_candidate`: provide one reviewed MP4 whose picture, audio and text
  are already locked. CapCut may add only the named visual finishing operations
  and export. Music, ducking or subtitle changes return upstream to Brownfield;
  do not pretend the flattened file is an adjustable multitrack timeline.
- `separated_stems`: provide a clean picture master, source-speech/dialogue
  stem, music stem, optional SFX stem, approved SRT/text contract and effect
  cue list. Every input carries path, SHA-256, duration and authority. Use this
  mode when CapCut must adjust music, ducking or text presentation.

Both modes must declare `return_route: S7_VERIFY`. CapCut never owns story,
picture, approved text or delivery truth.

For the Canon67 outcome-report family, retain the accepted A/B integration:

- A is the institutional coverage and factual skeleton;
- B is the emotional continuity and connective tissue;
- the motif `從學會，到接棒。` may shape presentation but may not remove or
  invent outcome evidence.

## Required Handoff

Before opening CapCut, record at least:

- unique project/run ID and installed CapCut version;
- input path, SHA-256, duration, resolution and expected audio state;
- `product_mode`, `soul_integration`, locked picture/text boundaries;
- each effect cue: intent, target range, intensity and protected content;
- each recurring motif: explicit `allowed_windows`,
  `outside_scope_behavior: none`, and whether chapter-boundary reuse is
  approved. Do not infer that an opening/ending motif belongs at every chapter;
- each music cue: local/catalogue source, time range, gain, fades, dialogue
  ducking intent and license/delivery status;
- continuous formal speech/interview cues must declare
  `ducking_policy: speech_segment` and the full protected placement window;
  do not automate gain recovery from sentence-level VAD gaps;
- free-only/paid policy, expected export path and owner review questions.

Missing story or picture truth returns to Stage 0-5. Missing effect design
returns to Effect Factory. Missing music/license truth returns to Soundtrack
Arranger. Do not solve these gaps by browsing randomly inside CapCut.

## Operating Loop

1. Freeze and hash the reviewed source plus handoff.
2. Use the registered draft adapter for deterministic media/timecode work.
   Bulk placement belongs in JSON/backend logic; UI insertion occurs at the
   current playhead and is not a reliable timecode compiler.
3. Close CapCut before any deterministic draft mutation. Back up the draft,
   apply once, reopen, and verify source identity, duration, tracks and timing.
4. In CapCut, perform only the bounded free operation. Prefer subtle effects
   that preserve faces, actions, approved text and the factual skeleton.
5. For catalogue assets, run export preflight before trusting a free-looking
   badge. If it becomes Pro, remove it; never pay, subscribe or bypass the gate.
6. Prefer local music with recorded provenance when catalogue availability is
   unstable. `preview_only` or unresolved license status must remain
   non-deliverable even when export succeeds.
7. Export locally without publishing or sharing. Record the exported hash,
   media probe and exact deviations from the handoff.
8. Copy the candidate back into the Hermes run and execute Stage 7 rendered QA,
   final-product Verify, and perception coverage. Then request owner taste and
   legal verdicts. Only the canonical delivery route can promote it.
9. Build the 0.5-second whole-timeline wall and verify every declared motif
   window plus at least one excluded middle window. A correct draft JSON does
   not prove the exported pixels obey the scope.

## CapCut 8.x Draft Rules Learned From The Forward Test

- Local audio uses the full desktop `extract_music` material/segment shape;
  thin `type=audio` JSON can be silently ignored.
- Local video must not inherit an online skeleton's catalogue identity.
  Changing only `path` is insufficient: CapCut may resolve the old product ID
  and rewrite the path to its online cache.
- GUI music/effect insertion uses the current playhead and may create duplicate
  tracks. Use deterministic placement for exact timing, then inspect the GUI.
- CapCut auto-save can overwrite an external patch. Never patch while it runs.
- Free/Pro availability is version, region and account dependent. A named
  catalogue item is never a durable dependency without current preflight.

## Stop Conditions

Stop and return a finding when:

- the visible source, baked text, duration or locked picture order differs;
- a Pro/payment/cloud/community gate appears and no approved free alternative exists;
- the only available music lacks delivery-compatible rights evidence;
- exact dialogue ducking, subtitle equality or multi-track timing cannot be
  evidenced from the exported candidate;
- continuous-speech BGM rises between sentences instead of remaining a stable
  low bed for the complete protected segment;
- CapCut crashes, auto-save races with a draft patch, or export cannot be read
  back into Hermes;
- Verify fails or the owner rejects the finishing taste.

## Verified Scope And Honest Limit

Forward-tested on CapCut Desktop 8.9.1.3802 with one 40-second, 1920x1080,
30-fps local source: one free native film-frame effect from 0-32 seconds, one
local instrumental track at -16.5 dB with a 2-second fade, local export, and
successful Hermes rendered QA, final-product Verify and perception coverage.

Also forward-tested on CapCut Desktop 9.0.0.3858 with one 315-second
`flattened_candidate`: two bounded free film-frame windows (opening and ending
only), local export, and a return through rendered QA, final-product Verify and
a 0.5-second whole-timeline wall. The music, ducking, subtitles and factual
labels were baked and verified upstream; this does not certify CapCut as their
editor in flattened mode.

This does **not** certify an unattended 540-second edit, native catalogue music,
dialogue ducking, subtitle editing, multi-effect composition, cross-version UI
stability, creative approval, music licensing or delivery.
