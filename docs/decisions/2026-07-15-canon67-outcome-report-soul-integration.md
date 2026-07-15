# Decision: Canon67 outcome-report soul integration

Date: 2026-07-15
Status: accepted
Scope: Stage 0-5 story, coverage, picture, and finishing intent
Superpowers phase: review

## SPEC

Requirement:

Preserve Canon67 as an institutional training-outcome report while adding enough
story continuity to avoid a category-by-category evidence dump.

Why:

The paper-edit A/B comparison exposed complementary strengths. Variant A kept
institutional coverage and factual order but felt mechanical. Variant B had a
stronger emotional line but drifted toward an auteur documentary and could omit
required outcome evidence.

Direction:

Use Variant A's factual coverage and institutional order as the skeleton. Use
Variant B's story continuity only as connective tissue. Carry the emotional
motif `從學會，到接棒。` from Stage 0 through picture, audio, text, effects, and
finishing decisions.

Non-goals:

- Do not let a creative motif remove required people, events, or training results.
- Do not treat effects, music, or generated imagery as factual evidence.
- Do not turn the film into a futuristic AI manifesto or viral short.

## DO

Files / modules:

- Stage 0-2 intent, story-soul, and segment-contract artifacts.
- Stage 3-5 Material Map, retrieval report, picture plan, and layered edit plan.
- CapCut or local finishing handoffs created after picture review.

Function-level plan:

Require each segment to retain a factual coverage purpose and an optional
emotional/story function. Reject plans that satisfy the emotional line by
reusing one event family as evidence for several distinct outcomes.

Data / interface changes:

Finishing handoffs carry `product_mode`, `soul_integration`, and picture-lock
boundaries. These fields guide presentation but never replace Material Map truth.

Migration / compatibility:

Existing Canon67 artifacts remain evidence. Any new plan must explicitly state
whether it follows this accepted outcome-report direction.

## VERIFY

Pre-checks:

- Product mode is `institutional_outcome_report`.
- Required outcome coverage remains enumerated before creative finishing.

Tests:

- Retrieval/picture-plan gates continue to require material evidence and source hashes.
- Repeated event-family use across different claimed outcomes is surfaced for review.

Manual checks:

- The owner can identify both the factual training progression and the emotional
  movement from learning toward responsibility.
- Removing music/effects does not destroy the factual meaning of the cut.

Regression risks:

- Agents may interpret the motif as permission to invent facts.
- A complete roster or ceremony may be dropped because it slows narrative pace.

## Decision Notes

Accepted because:

It combines the strongest part of each paper edit without making creativity or
coverage the sole authority.

Tradeoffs:

The structure is less radically cinematic than Variant B and requires explicit
coverage accounting from Variant A.

Open questions:

- The final owner-approved wording of the motif may change without changing the
  underlying coverage-first decision.

## Git / Retrieval

Related files:

- `.tmp/canon67_540s_route_acceptance/stage1/story_soul_blueprint.json`
- `.tmp/canon67_540s_route_acceptance/stage5/l1_revision_v3/l1_picture_plan_v3.proposed.json`
- `.tmp/capcut_finishing_pilot/capcut_finishing_handoff.json`
- `skills/capcut-assisted-finishing.md` (finishing may express the motif but
  cannot replace factual coverage)

Related commits:

- None yet.

Graphify anchors:

Canon67, institutional outcome report, story soul, Stage 0-5, picture plan

Search tags:

decision-log, spec-do-verify, canon67, outcome-report, soul-integration,
picture-plan, finishing-intent
