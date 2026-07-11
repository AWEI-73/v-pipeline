# L3 Preview-Mix / Delivery-Eligibility Contract Work Order

Status: **READY — OWNER-APPROVED BOUNDED CONTRACT REPAIR**

## Goal

Repair the verified L3 factory gap without creating a new mixer, route runner or
orchestrator:

```text
truthful internal-only BGM
+ preserved original speech
→ existing audio handoff acceptance
→ existing audio mix-plan executor with ducking
→ reviewable 22-second interview audio/video preview
→ final delivery remains fail-closed
```

The owner approved one product decision: **mix eligibility and delivery
eligibility are separate**. A track may be explicitly authorized for an
internal preview mix while remaining forbidden from final delivery.

This work order repairs and forward-tests that contract. It does not approve
the music license, the transcript, the picture edit, the audio taste or the
candidate for delivery.

## Verified Source Evidence

Read in this order:

1. `AGENTS.md`
2. this work order — the sole construction basis
3. `skills/pipeline-boundary.md`
4. `skills/editing-loop-director.md` — L3 and evidence-carrying loop rules only
5. `docs/construction-guides/work-orders/2026-07-11-editing-loop-unattended-interview-wave-a.md`
6. `.tmp/editing_loop_certification_campaign/l3/audio_trial/b5_audio_factory_capability_gap.json`
7. `.tmp/editing_loop_certification_campaign/l3/audio_trial/a4_repaired_audio_director_handoff.json`
8. `.tmp/editing_loop_certification_campaign/l3/audio_trial/a4_repaired_soundtrack_plan.json`
9. `.tmp/editing_loop_certification_campaign/interview/picture_trial/b4_repaired_picture_trial_evidence.json`
10. `.tmp/editing_loop_certification_campaign/consolidated_review/owner_review_index.md`

The verified gap is:

`CONTRACT_GAP_MIX_ELIGIBILITY_VS_DELIVERY_ELIGIBILITY`

The existing mixer already supports section timing, original-speech placement
and `duck_under_voice`. The missing capability is a truthful public handoff
contract for a non-delivery preview track.

## Frozen Inputs

These values must be re-read before construction and unchanged after the real
forward test:

| Input | Required SHA-256 / value |
|---|---|
| `.tmp/loop_f1_blind_reproducibility/candidate_v2/run/final.mp4` | `EE6EFC6FE624A3CF20A0C8A616480FF63C7C04E250168D806E7DF3777C7DC3B6` |
| `.tmp/editing_loop_certification_campaign/l2/candidate_l2/run/final.mp4` | `F1EF6951FA29E17C105518119B5B18DC2F847BEA4B005FD41E6E3857FFBC53A9` |
| `.tmp/editing_loop_certification_campaign/l2/candidate_l2/run/assets/bgm.mp3` | `3B4BAA4B50E6949AF2D596E40FB9E16886C648D82E5FF524FFF32265DFFC503A` |
| `.tmp/editing_loop_certification_campaign/interview/picture_trial/picture_trial_repaired.mp4` | `F2BC84A1A397133F6532989E7927A686DD0DAB4619DA14815C9E339FCB80DD4D` |
| `.tmp/editing_loop_certification_campaign/interview/picture_trial/picture_trial_plan.json` | `4D6F7D512CAD0A0ADFB3C4B9A12F5FD987CF7DAA4F462B42ACF95B83413C19DA` |
| `.tmp/editing_loop_certification_campaign/l3/audio_trial/a4_repaired_soundtrack_plan.json` | `C6D21165FA873AAEFDC95F5CF728843B6CE8827B15A70B97E48549ABC77B3823` |
| interview duration | `22.000` seconds, `660` frames at `30 fps` |

The original B5 gap artifact and failed acceptance attempt are immutable before
evidence. Write the repaired forward test under a new directory.

## Contract Decision

Keep the existing artifact roles and `version: 1`; this is an additive,
backward-compatible field contract.

### Track Eligibility Table

| Input state | Mix result | Delivery result |
|---|---|---|
| `delivery_allowed=true`; preview fields absent | Existing behavior: mixable | Not changed by this work order |
| `mix_allowed=true`, `preview_only=true`, `delivery_allowed=false`, valid internal `music_use_basis` | Mixable for internal preview | Forbidden |
| `delivery_allowed=false` without the complete preview contract | Block exactly as before | Forbidden |
| `source_type=reference_only` or bad license status | Block exactly as before | Forbidden |
| contradictory booleans or missing internal-use provenance | Fail closed | Forbidden |

The preview-only music item must carry portable provenance:

```json
{
  "mix_allowed": true,
  "preview_only": true,
  "delivery_allowed": false,
  "usage_scope": "internal_technical_reference",
  "music_use_basis": {
    "status": "human_declared_allowed",
    "usage_scope": "internal_technical_reference",
    "declared_by": "human",
    "basis_note": "Owner authorized this track only for an internal preview mix; no delivery or legal approval is claimed.",
    "legal_approval_claimed": false
  }
}
```

Add `internal_technical_reference` to the existing internal-use scope vocabulary.
Do not create a second provenance schema.

### Aggregate Artifact Rules

If any accepted track is preview-only, all downstream aggregate artifacts must
carry:

```json
{
  "preview_only": true,
  "delivery_allowed": false,
  "external_publication_requires_rights_review": true
}
```

This applies to `audio_handoff_acceptance.json`, `audio_mix_plan.json` and
`audio_mix_report.json`. Each accepted track must also retain its own scope,
eligibility and provenance fields.

`audio_handoff_acceptance.ok=true` means accepted for the declared scope; it is
not a delivery approval. A preview-only success uses
`next_action=audio_preview_mix_plan_ready`.

The executor may render the plan through the existing path, but its successful
preview report uses `next_action=review_internal_audio_preview`, never
`audio_ready_for_build`.

Preview-only music remains subject to the existing soundtrack probe and vocal
conflict checks. The new mix eligibility must not bypass those checks merely
because `delivery_allowed=false`.

## Environment

- Repo: `C:\Users\user\Desktop\video_pipeline`
- Python: `C:\Users\user\miniconda3\python.exe`
- Shell: PowerShell
- ffmpeg/ffprobe: repo-configured executables
- Full suite: forbidden in this work order; run only focused and adjacent tests

Do not install dependencies or change environment configuration.

## Owner Zone

The worker may edit only:

- `video_pipeline_core/audio_handoff_acceptance.py`
- `tests/test_audio_handoff_acceptance.py`
- `video_pipeline_core/audio_mix_plan_executor.py`
- `tests/test_audio_mix_plan_executor.py`
- `video_pipeline_core/delivery_gate.py`
- `tests/test_delivery_gate.py`
- `tools/pipeline_home.py`
- `tests/test_pipeline_home.py`
- `.tmp/editing_loop_certification_campaign/l3/audio_trial/preview_mix_contract_v1/**`
- `.tmp/editing_loop_certification_campaign/consolidated_review/owner_review_index.md`
- `.tmp/editing_loop_certification_campaign/consolidated_review/owner_verdict_template.json`
- `.tmp/editing_loop_certification_campaign/consolidated_review/cloud_handoff_manifest.json`
- `.tmp/editing_loop_certification_campaign/consolidated_review/capabilities_called.json`
- `.tmp/editing_loop_certification_campaign/campaign_status.md`

Stage and commit only the four production/test pairs above. Evidence and owner
review artifacts remain uncommitted for integrator inspection.

## Forbidden Zone

Read-only even if a test or worker recommendation suggests otherwise:

- `skills/**`
- `AGENTS.md`
- `video_pipeline_core/soundtrack_arranger.py`
- `video_tools.py`
- `tools/audio_mix_plan_execute.py`
- `tools/final_av_assemble.py`
- artifact dictionaries, branch registries and ownership contracts
- route runners and orchestrators
- raw source media
- `.tmp/editing_loop_certification_campaign/l2/**`
- `.tmp/editing_loop_certification_campaign/interview/**`
- the original B5 gap, failed attempt and Wave A worker report
- every existing unrelated dirty-tree path

Do not set `delivery_allowed=true` on the candidate_l2 BGM. Do not copy or
rename the preview output to `final.mp4` or `final_audio.wav`.

## Ordered Construction

### Piece 0 — Freeze And Red Evidence

1. Record HEAD, `git status --short` and all frozen hashes.
2. Add focused tests first and run them against pre-fix behavior.
3. Store the failing command, exit code and relevant tail under
   `preview_mix_contract_v1/red/`.

Required red behaviors:

- a complete preview-only item with `delivery_allowed=false` cannot currently
  enter the mix plan;
- a preview-only mix report is not currently stopped explicitly by the final
  delivery gate;
- Home does not currently return a review stop for a preview-only output.

Synthetic media may test contract mechanics. The real candidate is required in
Piece 5 for behavioral acceptance.

### Piece 1 — Separate Handoff Eligibility

In `audio_handoff_acceptance.py`:

1. Add one private, named predicate for track mix eligibility; do not scatter
   boolean expressions through `accept_audio_handoff`.
2. Preserve delivery-track behavior when new fields are absent.
3. Accept the preview-only branch only when every field and the existing
   `music_use_basis` are valid.
4. Preserve old `reference_only`, missing-file, license, required-track-count,
   probe and vocal-conflict blocks.
5. Run probe/vocal checks for preview-only music as well as delivery music.
6. Carry scope fields and provenance into accepted tracks and aggregate output.

Malformed or contradictory preview intent must have a stable blocking rule and
must not contribute to `accepted_track_count`.

### Piece 2 — Propagate And Validate Scope In The Mixer

In `audio_mix_plan_executor.py`:

1. Fail closed on a contradictory aggregate preview/delivery contract.
2. Render a valid preview-only plan through the existing executor and ducking
   implementation.
3. Carry aggregate and per-track scope/provenance into
   `audio_mix_report.json`.
4. Keep delivery-eligible output behavior backward-compatible.
5. Use `review_internal_audio_preview` as the next action for preview output.

Do not add a second executor or a preview-specific ffmpeg implementation.

### Piece 3 — Home Must Stop At Review

In `tools/pipeline_home.py`:

1. Recognize a successful preview-only `audio_mix_report` and its existing
   `output_audio` path before demanding `final_audio.wav`.
2. Return a review stop owned by the existing audio owner, with
   `next=review_internal_audio_preview`.
3. If the declared preview output is missing, return repair rather than review.
4. Do not add a route runner, branch-registry entry or new department.

### Piece 4 — Delivery Defense

In `delivery_gate.py`, a preview-only or explicitly non-delivery audio mix must
block complete delivery with the stable rule:

`preview_only_audio_not_delivery_allowed`

This block is required even if the media streams, ducking, peak level and other
delivery evidence pass. Existing delivery-eligible fixtures must remain green.

### Piece 5 — Real A4 Forward Test

Create a fresh run only under:

`.tmp/editing_loop_certification_campaign/l3/audio_trial/preview_mix_contract_v1/`

Use the frozen repaired picture, exact 0–22 second original speech, existing
candidate_l2 BGM and existing soundtrack plan. Create a new handoff with the
approved preview contract and human provenance above.

Run these existing public capabilities in order:

1. `tools/soundtrack_probe.py` on the BGM with ASR/vocal analysis enabled;
2. `video_tools.py soundtrack-audio-handoff-accept` with the fresh probe;
3. `tools/audio_mix_plan_execute.py` with
   `--output-name interview_audio_preview.wav`;
4. `tools/final_av_assemble.py --no-effects` to mux the frozen picture and
   preview audio into `interview_audio_preview.mp4`, using
   `--source-audio-policy preview_only_internal_mix`;
5. `tools/final_product_verify.py` on the preview MP4;
6. `tools/pipeline_home.py` on the preview run.

Do not handcraft audio or muxing with a private ffmpeg command. ffprobe and hash
commands are allowed as read-only evidence.

Real forward-test acceptance:

- handoff acceptance `ok=true`, `accepted_track_count=2` and no blocking;
- mix plan `ready_for_mix=true`, `preview_only=true`,
  `delivery_allowed=false`;
- report `ok=true`, original-speech track present, music track present,
  `ducking_applied=true`, peak `<= -0.5 dBFS`;
- preview WAV and MP4 are `22.000s` within `0.05s` tolerance;
- preview MP4 contains one video and one audio stream;
- Home stops at `review_internal_audio_preview`;
- the final delivery gate rejects a copied test fixture containing this report
  with `preview_only_audio_not_delivery_allowed`;
- all frozen hashes remain unchanged.

Create a minimal listening packet linking:

- `interview_audio_preview.mp4`;
- `interview_audio_preview.wav`;
- the exact source-speech review audio already in L4;
- the fresh probe, handoff acceptance, mix plan, mix report and verify bundle.

Update the consolidated owner packet so audio taste is reviewable but remains
`UNKNOWN`. Keep picture and transcript verdicts unchanged.

### Piece 6 — Report And Commit Boundary

Write:

`.tmp/editing_loop_certification_campaign/l3/audio_trial/preview_mix_contract_v1/phase_l3_preview_mix_contract_report.md`

The report must contain:

- final state and PASS/FAIL/UNKNOWN table;
- commit(s) and exact changed paths;
- red and green commands with exit codes and tail lines;
- real forward-test invocation records, hashes and artifact links;
- Home and delivery-gate read-backs;
- deviations, repairs, skips, blind spots and exact final git status;
- `human_creative_approval=false`;
- `final_delivery_claimed=false`.

The successful stop state is:

`WAITING_OWNER_VALID_INTERVIEW_PICTURE_AUDIO_TRANSCRIPT_VERDICTS`

L3 technical preview construction may be PASS. Audio taste, picture taste,
transcript truth, delivery and general L3 certification remain UNKNOWN.

## Required Tests

Capture red-first evidence for new behavior, then make these focused commands
green:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_audio_handoff_acceptance tests.test_audio_mix_plan_executor tests.test_pipeline_home tests.test_delivery_gate -v
```

Expected: exit `0`.

Then run only the adjacent contract suite:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_soundtrack_arranger tests.test_soundtrack_flow_acceptance tests.test_delivery_gate_report tests.test_parent_agent_delivery_contract -v
```

Expected: exit `0`.

Finally:

```powershell
git diff --check
```

Expected: exit `0`; pre-existing line-ending warnings may be reported but no new
whitespace errors are allowed.

Do **not** run the full suite. Full-suite integration remains deferred until the
editing-loop campaign's remaining production-code work is complete, per owner
instruction.

## Stop-Loss

- One LOCAL repair attempt per failure class.
- On the second occurrence of the same failure class, classify it STRUCTURAL
  and stop at the last green commit.
- Stop on any need to edit the Forbidden Zone, weaken delivery checks, bypass
  public handoff acceptance, handcraft a private mixer, or mark the BGM
  `delivery_allowed=true`.
- Stop if an old delivery-eligible path cannot remain backward-compatible.
- Stop if the final delivery gate cannot independently reject the preview-only
  report.
- Preserve all last-green commits and all red evidence.

## Worker Report Contract

Return only:

- exact stop state;
- commit hashes and changed-file list;
- focused/adjacent test counts and exit codes;
- real preview artifact paths and SHA-256 values;
- handoff, mix, Home and delivery-gate acceptance read-backs;
- frozen-hash preservation;
- repairs, deviations, skips and blockers;
- exact `git status --short`;
- both approval flags, which must remain false.
