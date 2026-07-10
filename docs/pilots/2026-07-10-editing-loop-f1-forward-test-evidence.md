# Editing Loop f1 Forward-Test — Durable Evidence Summary

Date: 2026-07-10

Classification: **PASS_F1_RESOLVED**

Scope: Editing Loop Skill reproducibility for one bounded L1 picture replacement

Creative/delivery scope: `human_creative_approval=false`,
`final_delivery_claimed=false`

## Experiment

A fresh TERRA session received only the Editing Loop Skill, four carried-context
inputs and the raw f1 taste finding. It was not given the expected stable clip,
replacement asset or evaluator answer.

Question: can the new agent independently locate the repeated ending image,
propose an evidence-backed replacement, stop at the owner gate, apply exactly
one approved picture diff, render fresh evidence and preserve every unrelated
decision?

## Result

The agent identified `montage_014` and proposed `SPT10 → GA37`. After explicit
owner approval it created candidate_v2 with the same 40.867–42.562 second
window. `montage_015 / SPT13` remained the final landing.

The owner reviewed the 38.731–44.000 second before/after dynamic and marked f1
resolved because the new middle image changed foreground/depth composition while
preserving the collective ending.

## Stable Semantic Diff

| Field | Before | After |
|---|---|---|
| stable clip | `montage_014` | `montage_014` |
| select | `SPT10` | `GA37` |
| asset id | `accepted_8ba4f5b3f7a4` | `accepted_9219dc742352` |
| source | `運動會/大合照/IMG_1325.JPG` | `工安早會/工安早會合照/IMG_2121.JPG` |
| timeline | 40.867–42.562 | unchanged |

Unchanged by semantic read-back: every other picture clip, all timing, audio,
approved text/overlays, settings, transitions, effects and the locked final
landing.

## Fresh Verification

| Gate | Result |
|---|---|
| semantic diff | PASS — exactly one picture source/lineage change |
| beat alignment | PASS — 14/14 intended boundaries within one 30 fps frame; ratio `1.0` |
| rendered product QA | PASS — no blocking or warnings |
| stream/duration | PASS — H.264 1920×1080＋AAC; container 44.024s |
| perception coverage | PASS — 17 shots, 113 samples, zero coverage gaps |
| candidate_v1 preservation | PASS — five protected hashes unchanged |
| UTF-8/JSON read-back | PASS |

Candidate_v1 final SHA-256:
`D72BD96A3C38DD5255E1464FFB895163E9CF5A796FE03170F0E0D32FEC013CC0`

Candidate_v2 final SHA-256:
`EE6EFC6FE624A3CF20A0C8A616480FF63C7C04E250168D806E7DF3777C7DC3B6`

## Evidence Pointers

Durable doctrine and work order:

- `skills/editing-loop-director.md`
- `docs/construction-guides/work-orders/2026-07-10-editing-loop-f1-blind-reproducibility.md`

Raw local experiment evidence（可重建、未納入 Git）：

- `.tmp/loop_f1_blind_reproducibility/f1_blind_reproducibility_report.md`
- `.tmp/loop_f1_blind_reproducibility/owner_gate/f1_picture_revision_verdict.json`
- `.tmp/loop_f1_blind_reproducibility/candidate_v2/f1_final_taste_verdict_waiting.json`
- `.tmp/loop_f1_blind_reproducibility/candidate_v2/f1_semantic_diff.json`
- `.tmp/loop_f1_blind_reproducibility/candidate_v2/beat_cut_alignment_report.json`
- `.tmp/loop_f1_blind_reproducibility/candidate_v2/rendered_qa/rendered_product_qa.json`
- `.tmp/loop_f1_blind_reproducibility/candidate_v2/f1_before_after_ending_dynamic.mp4`
- `.tmp/loop_f1_blind_reproducibility/candidate_v2_perception/perception_field_report.json`

## Carry-Forward

- Editing Loop Skill reproducibility is PASS only for f1 and this bounded L1
  picture-replacement pattern.
- This does not certify L0, L2, L3, L4, L5, a complete 44-second L0–L5 flight,
  the 9.4-minute film, creative approval or delivery.
- The next first-of-kind is L5 Review Loop, using existing V Pipeline review and
  verify capabilities without a new orchestrator, driver or formal artifact.
