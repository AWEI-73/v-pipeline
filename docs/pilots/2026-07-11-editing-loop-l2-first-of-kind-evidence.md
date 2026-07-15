# Editing Loop L2 First-of-Kind — Durable Evidence Summary

Date: 2026-07-11

Classification: **PASS_L2_TITLE_LIFECYCLE**

## Owner Verdict (verbatim)

```text
PASS_L2_TITLE_LIFECYCLE
Owner viewed the left-old/right-new comparison and stated the new version had no problem.
```

## Certified Scope

The Editing Loop L2 Skill is certified only for this bounded first-of-kind
case:

- candidate: Canon 67 `candidate_l2`, derived from frozen `candidate_v2`;
- duration: 44 seconds;
- layer and stable ID: `opening_title_text` lifecycle only;
- applied lifecycle: start `3.5s`, reveal complete `9.0s`, end `11.0s`;
- verification: repo-owned `render_edit_decision`, title lifecycle QA, rendered
  product QA, final-product verification, semantic diff, and owner review of
  the left-old/right-new dynamic.

This certification does **not** certify another effect, the complete film,
picture lock, audio mix, transcript truth, creative quality, music/legal
clearance, or delivery. `human_creative_approval=false` and
`final_delivery_claimed=false` remain unchanged.

## Candidate Preservation and Technical Evidence

| Artifact | SHA-256 / result |
| --- | --- |
| frozen `candidate_v2` final.mp4 | `EE6EFC6FE624A3CF20A0C8A616480FF63C7C04E250168D806E7DF3777C7DC3B6` |
| `candidate_l2` final.mp4 | `F1EF6951FA29E17C105518119B5B18DC2F847BEA4B005FD41E6E3857FFBC53A9` |
| lifecycle contract | `3.5s / 9.0s / 11.0s`, PASS |
| semantic invariant diff | PASS; picture, audio, poem, montage, ending, and 44-second duration unchanged |
| rendered product QA | PASS; no blockers or warnings |
| final-product verify | PASS; visual and audio checks passed |

The rendered candidate and all ephemeral evidence remain reproducible under
`.tmp/editing_loop_certification_campaign/l2/`:

- `candidate_l2/l2_semantic_diff.json`
- `evidence/title_ass_timing_readback.json`
- `candidate_l2/rendered_qa/rendered_product_qa.json`
- `candidate_l2/final_verify/final_product_verify_bundle.json`
- `review/current_v2_to_candidate_l2_title_dynamic.mp4`

## Finding Disposition

| Finding | Disposition | Scope and constraint |
| --- | --- | --- |
| `l5_f01` | **RESOLVED** | The approved-script title lifecycle mismatch was repaired only for `opening_title_text` at `3.5s / 9.0s / 11.0s`. |
| `l5_f02` | OPEN taste finding | The 0.18–0.19s full-poetry dwell remains owner-pending; it is not an objective unreadability claim or an authorized repair. |
| `l5_f03` | OPEN objective finding | Final landing form/hold remains outside this L2 scope and was not changed. |

## Decision Record and Limits

```jsonc
{
  "proposal_by": "agent",
  "verdict_by": "owner PASS_L2_TITLE_LIFECYCLE",
  "delegation_scope": "Canon 67 / 44s / opening_title_text lifecycle / first-of-kind",
  "evidence_refs": [
    ".tmp/editing_loop_certification_campaign/l2/candidate_l2/l2_semantic_diff.json",
    ".tmp/editing_loop_certification_campaign/l2/evidence/title_ass_timing_readback.json",
    ".tmp/editing_loop_certification_campaign/l2/review/current_v2_to_candidate_l2_title_dynamic.mp4"
  ],
  "applied_diff": "opening_title_text only: start_sec=3.5, reveal_complete_sec=9.0, end_sec=11.0",
  "carry_forward": [
    "candidate_v2 and candidate_l2 hashes are preserved",
    "l5_f02 and l5_f03 remain open",
    "human_creative_approval=false",
    "final_delivery_claimed=false"
  ]
}
```

No delivery claim follows from this evidence.
