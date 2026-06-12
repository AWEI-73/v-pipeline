# Decision: S4c Creative Exception

Date: 2026-06-12
Status: verified
Scope: Sensory Phase S4c / segment-level review exceptions

## SPEC

Use one reviewable segment-level exception shape:

```json
{
  "creative_exception": {
    "rule_bent": "hold_discipline",
    "reason": "Hold for the reveal.",
    "risk": "The sequence may lose momentum.",
    "requires_review": true
  }
}
```

A matching exception changes a blocking/failing finding to
`warn-with-ack`. It must remain in the review list and must not waive unrelated
rules or other segments.

## DO

- Added shared schema validation, exact rule matching, and acknowledgment
  metadata in `creative_exception.py`.
- Preserved the field through canonical adapter, runtime MV render plan,
  assembly plan, and timeline build.
- Applied exact matching in `spec_review`, `pacing_review`, `visual_fatigue`,
  and `presentation_feel_audit`.
- Normalized legacy `allow_long_hold_when` / `hold_reason` style exemptions
  into visible acknowledged hold warnings while retaining old input support.

## VERIFY

- TDD RED confirmed missing schema, consumer downgrade, artifact propagation,
  runtime propagation, and legacy normalization behavior.
- Focused S4c suite: 93 tests PASS.
- Final fresh full regression: 653 tests PASS.
- City-lite real-video baseline:
  `C:\Users\user\Desktop\video_project\city-lite\runs\20260612-sensory-s4c-v1`
- Independent pacing, visual-fatigue, and presentation-feel fixtures each pass
  with the intended acknowledged warning.
- A combined fixture with unrelated violations remains blocked, proving the
  exception is not a global bypass.

## Decision Notes

Exceptions are explicit debt with a named risk and required review. They are
not suppression flags. Matching is exact by rule name and scoped to the
affected segment.

Search tags: `s4c`, `creative_exception`, `warn-with-ack`, `review`
