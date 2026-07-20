<!-- DOCUMENT_ROLE: EVIDENCE -->

# Canon 67 first long-form closure

Date: 2026-07-20

Canon 67 is closed as V Pipeline's first long-form case evidence. This is an
accepted internal candidate with known limitations, not a final-delivery or
music-rights-clearance claim.

## Result

- State: `CLOSED_FIRST_LONGFORM_CASE_WITH_KNOWN_LIMITATIONS`
- Candidate duration: 315.022 seconds
- Candidate SHA-256:
  `10f9a1f2b6f75ddbe9ace15e7be62ebaa383020c21cb69f5363a7c70f8f59017`
- Human creative approval for case closure: `true`
- Final delivery claimed: `false`
- Music legal clearance claimed: `false`

## What the closure proves

- Stage 0–10 produced a real long-form candidate and returned Brownfield
  finishing through Verify.
- The last audio revision changed only the audio elementary stream; the video
  elementary stream stayed at
  `0aac79ca016d1ff6f19a3ec313a4abf11b0beacb770278ccc7869f268fbd8943`.
- The supervisor segment uses one stable ducking window from 236.00 to 275.34
  seconds while preserving the 39.34-second speech waveform.
- Rendered-product QA and final-product Verify pass.
- A fresh-context Editorial Reviewer independently identified three useful
  structural/taste findings. The owner accepted them as calibration evidence
  and chose not to reopen this candidate.
- Full suite: 2,928 tests passed, one skipped.

## Honest limitation

The Stage 9 v3 fast path did not originally produce its normal work-order,
execution-receipt, attestation, and manifest chain. Closure reconstructed a
hash-bound retrospective receipt. It proves current artifact identity and
behavior, but it does not pretend the original run used the accountability
executor or recover the missing original command/timing metadata.

This remains one open system-level finding: make render, mix, review, and
verify receipts normal tool outputs before the second long-form case.

## Durable pointers

- Current campaign state:
  `.tmp/canon67_editorial_reconstruction_v2/closure_v1/campaign_status.json`
- Closure manifest:
  `.tmp/canon67_editorial_reconstruction_v2/closure_v1/closure_manifest.json`
- Owner verdict:
  `.tmp/canon67_editorial_reconstruction_v2/closure_v1/owner_verdict.json`
- Finding ledger:
  `.tmp/canon67_editorial_reconstruction_v2/closure_v1/finding_ledger.json`
- Retrospective Stage 9 receipt:
  `.tmp/canon67_editorial_reconstruction_v2/closure_v1/stage9_audio_revision_retrospective_receipt.json`
- Verification state:
  `.tmp/canon67_editorial_reconstruction_v2/closure_v1/verification_state.json`

## Next proof

Use a second, better-annotated long-form material set. Measure wall-clock time,
agent turns, render count, human-review minutes, and whether the owner has to
rediscover the same findings. Canon 67 should not be reopened without new owner
direction.
