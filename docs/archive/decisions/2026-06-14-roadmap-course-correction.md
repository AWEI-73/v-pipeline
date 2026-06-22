# Roadmap Course Correction For External Review

## Review Request

Review whether the proposed next direction is technically coherent and avoids
overfitting the 67th graduation-film case. Challenge schema duplication,
incorrect gate severity, and acceptance criteria. Do not implement M5c-M5e or
M6 until this direction is reviewed.

## Current Product Position

The pipeline has reached a usable material-limited editing baseline:

- Actual material supply constrains script duration and chapter count.
- Missing material cannot be silently replaced by unrelated or repeated clips.
- Explicit director source and duration choices survive into BUILD.
- True render, technical VERIFY, and four-layer montage evidence exist.

The 67th candidate is materially honest and substantially better than earlier
versions, but it is not a human-edit-quality reference. Limited source material
makes further sensory tuning difficult to evaluate objectively.

## Correction To Recent Claims

The recent mechanisms are useful but were overstated:

| Mechanism | Keep | Correction |
|---|---|---|
| black/blank-frame audit | Yes, tier-1 technical gate | Decode/sample failure must fail closed; intentional black/white design exceptions are still missing |
| dHash novelty audit | Yes, tier-2 evidence | Detects perceptually similar composition, not semantic sameness |
| action progression audit | Yes, tier-2 evidence | Checks declared phases and order, but 67th currently has no reviewable required-function lineage |

M5a and M5b must not be in `delivery_gate.HARD_AUDITS`. Unit-test success and a
single rendered case are insufficient evidence for tier-1 promotion.

## Recommended Next Direction

Move from more 67th-specific sensory tuning to a canonical material-map
lifecycle:

```text
story discussion
  -> required material map / shooting brief
  -> collect or ingest material
  -> actual material map / supply review
  -> material delta
  -> revise script
  -> build and verify
```

The required and actual sides already exist under different names:

- Required: `material_needs.json`, `shooting_brief.md`
- Actual: per-asset `*.map.json`, `supply_review.json`
- Missing bridge: `material_delta.json`

The next implementation should connect these artifacts rather than introduce
new parallel schemas.

## Review Resolution

The external review was accepted with these corrections:

- Tier-1 is limited to honesty and technical validity. Mixed aesthetic reports
  (`visual_audit`, `presentation_feel_audit`, `treatment_audit`,
  `visual_fatigue_audit`, and `editorial_qa`) remain dashboard evidence and do
  not directly block delivery.
- M6a must validate `material_needs.json` and add the
  `satisfies: [need_id]` edge before any delta implementation.
- Existing-material and planned-capture are lifecycle entry points, not
  exclusive workflows; partial availability is first-class.
- The prior M5b action spine is not the canonical function vocabulary. It is
  deprecated as an acceptance direction.
- Before M6a, a bounded VD0 step establishes shallow scene-review labels and
  lineage only. It does not implement a complete diversity guard.
- Claude F6 is rejected: M6 must not revive M5b's
  `establish -> action -> result` spine. Requirement purpose and visual
  diversity are separate contracts.

## Implementation Status

- VD0 is complete: reviewed scenes preserve `visual_family`, `angle_scale`,
  `action_family`, and `subject`; `media_type` continues to derive from the
  asset-level `asset_type`.
- Gate demotion is complete through all three layers: delivery gate, dashboard
  severity, and runtime routing. Tier-2 quality failures remain visible as
  warnings and do not block completion.
- Complete Visual Diversity rules and M6 delta remain intentionally unstarted.
- Verification: focused gate/material-map/dashboard/runtime tests and the full
  `760 tests` regression passed on 2026-06-14.

## Proposed Order

1. Define canonical artifact contracts, stable requirement IDs, validated
   `material_needs.json`, and the `satisfies: [need_id]` edge.
2. Implement `material_delta.json` with evidence-backed routes.
3. Drive script revision from accepted delta decisions.
4. Expose the lifecycle as an independent Material Map Skill.
5. Validate with both an existing-material case and a script-first capture case.

## Non-Goals

- Do not force a ten-minute runtime.
- Do not make CLIP or a cloud model mandatory.
- Do not claim dHash is semantic understanding.
- Do not promote aesthetic proxy metrics to tier-1 from one case.
- Do not continue tuning the 67th case merely to make M5 metrics pass.
- Do not build effects expansion before the material lifecycle is coherent.

## Questions For Reviewer

1. Should `material_needs.json` become the canonical required-material map, or
   is there a concrete incompatibility that requires migration?
2. What is the minimum stable ID model needed to preserve lineage from a
   requirement through shooting, ingest, delta, and revised script?
3. Which delta outcomes must block BUILD, and which should remain human review?
4. Is the two-mode entry model sufficient, or does it hide a materially
   different workflow?
5. What smallest two-case validation would disprove this architecture before
   broader implementation?

## Expected Review Output

Return findings before recommendations:

1. Identify any incorrect premise, duplicated responsibility, or missing
   lifecycle state.
2. State whether M6a should be approved, modified, or rejected.
3. Propose the smallest artifact-contract change needed before implementation.
4. Separate objective tier-1 blockers from tier-2 quality evidence.
5. Do not implement code as part of this review.
