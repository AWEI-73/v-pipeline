# Canon 67 Stage 3.5 story revision and role-bound retrieval

Date: 2026-07-18
Status: accepted for the next Stage 4 paper edit
Owner: user, delegated to the main-pipeline integrator for application

## Decision

Accept the bounded Stage 3.5 evidence review and stop deepening the Canon 67
material pool. The current pool supports a shorter, more truthful paper edit;
it does not support padding the earlier story ambitions.

The accepted segment changes are:

| Segment | Accepted treatment |
|---|---|
| A02 collective identity | 12 seconds; one strong cohort portrait and at most two genuinely different group contexts; no shared-action or formation-change claim |
| A07 technical detail | 0 seconds; merge useful manhole/cable windows into A04/A05 only when they replace weaker or repetitive material |
| A09 supervisor witness | preserve the approved 39.34-second source speech and 12 cues; ground cable cutaway for cues 03-04, pole/line cutaway for cues 05-06, cues 08-12 remain on speaker unless separately approved |
| A10 placement preference | 18 seconds; process-only description of discussing and recording future work-unit preferences; no named supervisor, individual rank, completed choice, or final placement claim |
| A11 collective landing | 24 seconds; two short distinct callbacks, one final group photograph, then a bounded hold; no literal-departure claim |

The resulting paper-edit target is 360.34 seconds before later timing review.
This is a truthful target, not a requirement to fill time.

Promote the proposed Stage 3.5 Material Map v3 byte-for-byte as the accepted
Canon 67 map. Its SHA-256 is
`704a1fed801218530d206665bf906f67a60ad28f216e3c954ee195b23775962c`.
It preserves all 16 prior accepted edges and adds 15 evidence-bound edges.

## Generic retrieval rule

A segment-level ranking list is insufficient when one segment contains several
story roles. For every video clip in a multi-role segment, the picture plan
must carry:

- stable `clip_id`;
- canonical `segment`;
- exact `need_id` for that clip's story role;
- `asset_id` / `scene_id` and source-hash binding;
- selection mode and ranking evidence.

The retrieval gate validates each clip against candidates for its own
`need_id`. A scene may satisfy multiple accepted needs; matching must consider
all accepted edges and select the edge relevant to the current role. Being
ranked for another role does not authorize the clip. Missing `clip_id`, missing
role binding, or an undeclared need fails closed.

An `accepted` need edge is reviewed evidence and therefore ranks above an
otherwise equivalent `candidate` edge. Candidate edges remain retrieval hints;
they must not crowd an accepted source out of a bounded Top-K list merely due
to stable-ID ordering.

This is a generic Material Map / L1 rule. Canon 67 asset IDs and durations must
not be hard-coded into production code.

## Evidence

- `.tmp/canon67_editorial_reconstruction_v2/stage3_5_targeted_gap_closure_v1/final/integrator_acceptance_v1.md`
- `.tmp/canon67_editorial_reconstruction_v2/stage3_5_targeted_gap_closure_v1/review/project_material_map_v3.proposed.json`
- `.tmp/canon67_editorial_reconstruction_v2/stage3_5_targeted_gap_closure_v1/review/material_map_delta_v2_to_v3.json`
- `.tmp/canon67_editorial_reconstruction_v2/stage3_5_targeted_gap_closure_v1/review/a09_cue_cutaway_map.json`
- `.tmp/canon67_editorial_reconstruction_v2/stage3_5_targeted_gap_closure_v1/retrieval_replay_v2/picture_plan_retrieval_report.json`

## Boundaries

- This decision authorizes Stage 4 paper-edit construction, not rendering.
- It does not authorize new ASR, whole-pool review, music, effects, finishing,
  creative-quality approval, or delivery.
- `human_creative_approval=false`.
- `final_delivery_claimed=false`.
