# M5 Real-Render Sensory Acceptance Decision Log

## Goal

Verify the material-aware M0-M4 result as a true rendered video, compare its
viewing rhythm with the student edit, and prevent technical or file-identity
metrics from being mistaken for human-edit acceptance.

## Evidence

Agent render:
`C:\Users\user\Desktop\video_project\67th-graduation-film\runs\20260613-m5-real-render\final.mp4`

Student edit:
`C:\Users\user\Downloads\微電影素材\_整理後\最終版的最終版.MP4`

Four-layer agent evidence:
`C:\Users\user\Desktop\video_project\67th-graduation-film\runs\20260613-m5-real-render\m5_verify_evidence`

Student 48-frame overview:
`C:\Users\user\Desktop\video_project\67th-graduation-film\runs\20260613-m5-real-render\student_overview_48.jpg`

The agent render completed successfully. Technical VERIFY passed with score
98.7: script coverage 100, duration fit 98, subtitle accuracy 96, audio levels
100, and technical quality 100.

## Sensory Findings

Sensory acceptance: **FAIL**.

The material-aware replay fixed major planning defects: it removed unsupported
chapters, reduced the film to the supportable 180.5 seconds, stopped source-file
reuse, and no longer forces a ten-minute target. Those are necessary
improvements, but they do not make the result human-edited.

Dense montage review exposed the remaining gap:

1. Source identity is not semantic visual novelty. Different files can still
   show nearly identical group, classroom, or ceremony compositions.
2. Motion-peak snapping is not action progression. Critical grids can show the
   same visible action state across every sample even when the edit point was
   mechanically snapped to motion.
3. The opening holds one aerial composition for about six seconds. It
   establishes location but does not create a designed hook.
4. The back half contains long runs of similar group and ceremony
   compositions. Tension drops despite unique-source and NVI metrics passing.
5. The ending moves from a group image to a fixed campus view, but lacks a
   designed emotional payoff or visual callback.

The student overview shows a different editing model. It uses a designed title
sequence, explicit course cards, changes in aspect and composition, action
close-ups, people-focused punctuation, and a branded closing identity. Its
advantage is therefore not only more or better material. It turns the material
into designed sequences with visible beats.

## Metric Gap

M4 planning acceptance was too optimistic:

| Existing metric | What it proves | What it misses |
|---|---|---|
| unique source ratio | files are not reused | semantically repeated compositions |
| new visual information ratio | source windows differ | whether the viewer perceives a new beat |
| motion-peak snap | local pixel motion exists | action setup, execution, and result progression |
| technical VERIFY | render and delivery mechanics pass | story tension and human editing judgment |

Technical VERIFY remains a required gate, but it cannot authorize final
delivery by itself.

## Decision

M5 true rendering is complete, but the candidate is not accepted for delivery.
The next work must target sensory evidence rather than raise the existing
planning scores.

## 2026-06-14 Scope Correction

The mechanisms added after this review do not fully close the sensory gap:

- M5a uses dHash as a perceptual-composition proxy. It is useful evidence, but
  it is not semantic understanding and is not a tier-1 delivery gate.
- M5b now checks declared function coverage and order. The 67th contract and
  timeline do not currently provide reviewable `required_functions`; the
  honest result is `no_required_functions`, not a passing coverage score.
- M5c/M5d/M5e are deferred until a richer-material case exists. Continuing to
  tune the limited 67th case would overfit proxy metrics rather than prove
  general editing quality.

The active next direction is the material-map lifecycle: canonicalize the
existing requirement-side `material_needs.json` / `shooting_brief.md`, compare
them with actual `*.map.json` / `supply_review.json`, produce
`material_delta.json`, and revise the executable script from that evidence.

## Verification

- True agent render completed and technical VERIFY passed at 98.7.
- Agent evidence contains 48-frame overview, 15 chapter grids, 15 critical
  grids, and a rhythm strip.
- Student 48-frame overview completed.
- Manual review covered the agent opening, ceremony/back-half, ending, and
  critical high-density grids.
