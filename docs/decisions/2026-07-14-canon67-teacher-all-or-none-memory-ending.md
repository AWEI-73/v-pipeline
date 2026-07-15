# Decision: Canon 67 teacher roster is all-or-none and the ending becomes a reviewed memory wall

Date: 2026-07-14
Status: accepted
Scope: Canon 67 540-second candidate / L1 picture plan / ending effect
Superpowers phase: review

## SPEC

Requirement:

- The teacher/adviser sequence may appear only when all 13 people, their approved order, identity text, and source evidence are complete. Otherwise the whole sequence is omitted.
- The closing must use reviewed existing material to express responsibility and forward motion without claiming an unrecorded departure.
- The 70-second closing is shortened to 40 seconds and becomes a restrained memory-photo composition that resolves into one final group image with approved animated copy.

Why:

- The current single 100-second adviser source cannot prove a complete 13-person roster.
- The current closing uses five similar group photographs and does not visually prove departure.
- Effects may organize memory and emotional direction, but may not invent people, events, identity, or factual departure evidence.

Direction:

- `seg09_people_who_held_the_line` is deferred at zero seconds for this candidate. Reopening it requires a 13/13 owner-approved roster and evidence packet.
- Preserve the 540-second target by assigning the recovered time to factual training, daily-life, and supervisor material:

| Segment | Revised seconds |
| --- | ---: |
| seg01 | 30 |
| seg02 | 45 |
| seg03 | 55 |
| seg04 | 95 |
| seg05 | 105 |
| seg06 | 45 |
| seg07 | 65 |
| seg08 | 60 |
| seg09 | 0 |
| seg10 | 40 |

- `seg10` uses the reviewed `memory_photo_wall` Remotion capability: individual reviewed photos appear, accumulate into a memory field, converge on one final group photograph, then hold for readable text.
- Approved draft closing copy:
  - `最後一次，站成一個集體`
  - `下一站，各自把責任接住`

Non-goals:

- Do not generate missing teacher portraits, names, units, quotations, or departure footage.
- Do not delete the existing teacher source or Material Map evidence.
- Do not render the full 540-second candidate in this revision round.
- Do not let the Remotion worker own material truth, rough-cut selection, or `final.mp4`.

## DO

Files / modules:

- `.tmp/canon67_540s_route_acceptance/stage4/segment_contract_v3.proposed.json`: apply the revised duration and all-or-none roster gate.
- `video_pipeline_core/material_retrieval.py`: bounded evidence-quality ranking only if red-first tests prove the current tie.
- `.tmp/canon67_540s_route_acceptance/stage5/l1_revision_v2/`: revised retrieval/window proposal and storyboard evidence.
- `.tmp/canon67_540s_route_acceptance/stage5/effects/seg10_memory_ending/`: Effect Factory and Remotion review artifacts.

Function-level plan:

- Keep need matching as the admission gate; use review confidence, direct story evidence, resolved story function, and existing diversity controls to differentiate same-need candidates.
- Use the existing `plan_ranked_windows` and `source-highlight-plan` capabilities for source windows. A run-local builder must not replace them with `start_sec=0` defaults.
- Build the ending from reviewed photo/keyframe refs only, preserve faces, and finish on one group image.

Data / interface changes:

- Add optional ranking evidence fields only inside the existing score breakdown; do not introduce a parallel ranking schema.
- Record `seg09` as `deferred_all_or_none`, with `required_roster_count=13`.

Migration / compatibility:

- Keep all v1 artifacts frozen. Write proposed v2/v3 artifacts beside them until owner approval.

## VERIFY

Pre-checks:

- Freeze hashes for the current Material Map, L1 plan, storyboard packet, and source media.
- Preserve the current all-score-4 and 30-zero-start findings as before evidence.

Tests:

- Same-need candidates with direct, resolved, higher-confidence evidence rank above unresolved/support-only candidates.
- Filename/folder prior still cannot admit a scene by itself.
- `plan_ranked_windows` produces bounded, evidence-backed windows and does not default every selected video to zero.
- Existing material retrieval and picture-plan gate tests remain green.

Manual checks:

- Revised storyboard shows the nine active sections in story order.
- No teacher/adviser card or the unresolved 100-second adviser source enters the candidate.
- The ending preview visibly builds memory, preserves faces, resolves into one group photograph, and keeps both text lines readable.

Regression risks:

- Evidence-quality weights could suppress a scarce but necessary support shot; unresolved candidates remain eligible only when no stronger evidenced alternative exists.
- Repeated material families may be intentional inside one technical micro-story; diversity penalties must not randomize task causality.

## Decision Notes

Accepted because:

- It keeps factual honesty while preserving the intended emotional landing.
- It upgrades the existing factory path instead of adding a new selector or final renderer.

Tradeoffs:

- The candidate will not thank teachers individually until the complete roster exists.
- A memory-wall ending communicates departure symbolically rather than as documentary proof.

Open questions:

- The final approved teacher order remains unresolved until a 13-person roster packet exists.
- Final font, music, and logo timing remain later L2/L3/L4 decisions.

## Git / Retrieval

Related files:

- `.tmp/canon67_540s_route_acceptance/stage5/l1_picture_plan.json`
- `.tmp/canon67_540s_route_acceptance/stage5/l1_owner_review/owner_review_summary.json`
- `skills/material-map.md`
- `skills/video-effect-factory.md`

Related commits:

- none yet

Graphify anchors:

- Canon 67 L1 retrieval review
- teacher roster truth
- memory photo wall closing

Search tags:

- `decision-log`
- `canon67`
- `teacher-all-or-none`
- `memory-photo-wall`
- `evidence-carrying-editing-loop`
