# Review Response: M6a Material-Map Lifecycle Direction

Reviewer: Claude (Opus 4.8). Scope: review only, no code changed.
Reviews: `2026-06-14-roadmap-course-correction.md` + current code state (756 tests green).

## Verdict (summary)

**M6a APPROVED WITH MODIFICATIONS.** The lifecycle direction is correct and is
the right next move; stopping 67th-specific sensory tuning is correct. But two
contract gaps (F2 vocabulary fork, F3 missing satisfaction edge) must be
resolved *inside* the M6a spec step before any `material_delta` code, or the
delta will be built on a join that does not exist. The gate-severity correction
is right but was applied inconsistently (F1).

---

## Findings (before recommendations)

### F1 — Gate demotion is correct but inconsistent (incorrect gate severity)
Demoting `semantic_novelty_audit` (M5a) and `action_progression_audit` (M5b) out
of `delivery_gate.HARD_AUDITS` is correct: a perceptual/aesthetic proxy must not
become a tier-1 delivery blocker from one case + unit tests. Agreed and endorsed.

**But** `HARD_AUDITS` still contains `presentation_feel_audit` and
`visual_fatigue_audit`, which are aesthetic quality proxies by the doc's *own*
gate policy ("pacing, designed-sequence quality" = tier-2). The list is now
internally inconsistent: the weaker, newer aesthetic proxies were demoted while
older aesthetic proxies still hard-block.

A defensible, principled line (recommend adopting and documenting):
- **tier-1 = honesty + technical**: literal source over-reuse / literal-window
  replay (`broll_audit`, `new_visual_information_audit` — these are *anti-padding
  honesty*, not aesthetics), technical defect (`black_frame_audit`), caption
  sync (`caption_audit`), structural (`timeline_invariants`), `verify_result`.
- **tier-2 = perceptual/aesthetic quality**: `semantic_novelty_audit`,
  `action_progression_audit`, `presentation_feel_audit`, `visual_fatigue_audit`,
  `treatment_audit`.

Under that line, `presentation_feel_audit` and `visual_fatigue_audit` should also
leave `HARD_AUDITS`. This is a decision to make explicitly, not silently — flagging
per the doc's invitation to challenge gate severity.

### F2 — Three function vocabularies (duplicated responsibility, biggest blocker)
There are now three parallel "what is this shot for" taxonomies:
1. `gap-analyzer` material_needs `category`: 6 Chinese classes
   (動作鏡頭/情境鏡頭/空景過場/特定表情/字幕對應/靜態照片).
2. M5b `action_progression.FUNCTIONS`: establish/action/detail/result/reaction.
3. `sequence_grammar.required_functions` consumed by supply_review + M5b.

`material_delta` compares "required functions" against "actual functions". With
three vocabularies it cannot be coherent. This is the single largest
pre-implementation blocker — larger than the delta itself.

### F3 — Missing lifecycle state: the satisfaction edge (load-bearing gap)
The required side keys requirements as `need.id = "<segment>.<seq>"`. The actual
side keys assets as `asset_id` (filename-derived). **Nothing joins a need to the
asset(s) that satisfy it.** `supply_review` joins asset→segment (by path /
`material_map_ids`), never asset→need. Without an asset→requirement assignment,
`material_delta` has no edge to diff. The genuinely missing artifact is not
`material_delta.json` — it is the `satisfies: [need_id]` edge that delta consumes.

### F4 — material_needs.json is not yet canonical-grade
`gap-analyzer.md` states the file is agent-authored by convention and
`validate-needs` is "待加,目前手動 check". Promoting it to *the canonical
required map* means delta consumes unvalidated input. A schema + validator must
exist before "canonical" is a true claim.

### F5 — Two-mode model hides the partial case (missing lifecycle state)
`existing_material_edit` vs `planned_capture` are not two workflows — they are one
lifecycle (required map + actual map + delta) entered from different ends. The
67th reality is **partial**: some footage exists, some must be shot. If the two
modes are exclusive code paths, partial is homeless. Model one lifecycle, two
entry points; let delta carry partial.

### F6 — M5b is latent on real cases (confirmation, not objection)
67th declares no `required_functions`, so `action_progression` reviews 0 segments
and trivially passes. Codex flagged this correctly. It is an argument *for* M6:
the canonical required map should be the *source* of `required_functions`, which
finally wires M5b to real input instead of leaving it dark.

### Positive confirmations
- `black_frame_audit` fail-closed on unsamplable render: correct (a defect
  detector that passes when it cannot sample is worse than none). Precondition:
  only produce it on a real render, never in planning replay.
- "Do not claim dHash is semantic understanding": correct and important honesty.
- Reuse `material_needs.json` rather than a new schema: correct instinct.

---

## Answers to the five reviewer questions

**Q1 (material_needs as canonical required map?)** Yes in principle, no migration
needed — *extend*, don't replace. Two preconditions: (a) F4 schema+validator;
(b) F2 reconcile its 6-category vocabulary to the one canonical function set.

**Q2 (minimum stable ID model?)** Keep `need.id = "<segment>.<seq>"` as the
requirement key and `asset_id` as the asset key. Add exactly one new thing: a
`satisfies: [need_id]` field on the asset (or asset *scene*), assigned at
ingest / agent caption-review — that review is already the moment a human/agent
looks at footage and can say "this is need 1.1". Delta = join over that edge. Do
not invent a new global UUID space.

**Q3 (which delta outcomes block BUILD vs review?)**
- **tier-1 block**: a `must_have:true` need with no satisfying asset and no
  permitted fallback (= the existing unresolved required-material gap); an asset
  assigned to a proof/identity need that is wrong material.
- **human review (no auto-block)**: thin count (need count > satisfied count),
  tier-2/3 fallback substitution, function-phase incompleteness.
This is just the established policy applied to delta: honesty blocks, quantity
and quality route to review.

**Q4 (two-mode sufficient?)** Sufficient as *entry points*, not as workflows. Add
partial as first-class (F5). Risk if modes become exclusive branches.

**Q5 (smallest two-case disproof?)**
- (a) existing-material: 67th actual footage, script ambition capped at supply;
  delta should be near-empty and the film must not regress.
- (b) script-first: a `material_needs` with one impossible `must_have` and zero
  assets; delta MUST emit a tier-1 block + a shooting-brief line and BUILD MUST
  NOT proceed. If (b) can be silently bypassed, the architecture has failed.
Case (b) is the real disproof — it tests the satisfaction edge + the tier-1 gate
together.

---

## Smallest artifact-contract change before implementation

Two contracts, both small, both prerequisite to any delta code:
1. **One canonical shot-function vocabulary** + a documented mapping table from
   gap-analyzer's 6 categories and from `sequence_grammar.required_functions`
   into it (resolves F2; also wires M5b to real input per F6).
2. **The `satisfies: [need_id]` edge** on assets/scenes, written at ingest/
   caption-review (resolves F3).

`material_delta.json`, script revision, and the Material Map Skill are all
downstream of these two and should not start first.

## Tier-1 vs tier-2 (explicit, for the gate)

- **Tier-1 (block delivery/BUILD)**: capability `B5`, script_overreach `B6`,
  unresolved `must_have` material gap, wrong proof/identity material, technical
  `verify_result` fail, defective render `black_frame_audit` (fail-closed),
  `timeline_invariants`, `caption_audit`, anti-padding `broll_audit` /
  `new_visual_information_audit`.
- **Tier-2 (quality evidence; route to judge/dashboard, no auto-block)**:
  `semantic_novelty_audit`, `action_progression_audit`, `presentation_feel_audit`,
  `visual_fatigue_audit`, `treatment_audit`, pacing.
- **Action**: resolve F1 — move `presentation_feel_audit` and
  `visual_fatigue_audit` out of `HARD_AUDITS`, or document why they block.
