# M0e SPEC Field Census

Date: 2026-06-13

Purpose: retain fields that have a decision consumer and verification route;
stop treating descriptive completeness as executable authority.

| Field / family | Decision | Consumer | Verifier | Violation action |
|---|---|---|---|---|
| `core.story_purpose`, `blueprint_ref` | keep | writer/director, blueprint gate | blueprint coverage | revise director |
| `core.proof_critical`, `identity_sensitive` | keep, tier 1 | route, curator, judge | delivery/spec review | block |
| `material_fit.visual_desc`, `must_include` | keep, tier 1/2 | matcher, curator | coverage/judge | GAP or revise |
| `required_capabilities` | keep, tier 1 | spec review | capability manifest | block B5 |
| `editing_intent`, `sequence_grammar` | keep, tier 2 | treatment/shot planning | treatment/editorial QA | revise |
| `pacing`, `visual_style.pace` | merge semantics, tier 2 | allocator/editor | pacing/visual fatigue | revise or shorten |
| `target_length` | downgrade to tier 3 | allocator | M1 supply review | shorten to honest duration |
| `visual_style.transition/layout` | keep, tier 3 | renderer | capability/spec review | downgrade unsupported |
| `audio.role`, `original_audio_policy` | keep, tier 1/2 | audio/render | audio/editorial QA | block or revise |
| facet `reason` fields | keep for review trace, not runtime authority | reviewer/dashboard | perfunctory-spec check | warn/block only when systemic |
| duplicate legacy flat fields | merge into canonical facet | adapter only | schema tests | remove after migration |
| fields with no consumer and no verifier | remove | none | none | census before deletion |

## Enforcement Rules

1. A field without a named consumer, verifier, and violation action is
   documentation, not an executable requirement.
2. Tier 3 preferences may be dropped to preserve tier 2 quality.
3. Tier 2 quality may be reduced to preserve tier 1 semantic honesty.
4. Existing failed audits and unresolved GAPs block final delivery.
5. Capability manifest is generated from runtime constants; it is never hand
   authored.
