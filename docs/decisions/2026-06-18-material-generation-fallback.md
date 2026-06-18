# MGF1 Material Generation Fallback

Date: 2026-06-18

## Decision

Add a bounded material-generation fallback layer between `material_delta` and
external image/video providers.

The layer produces `material_generation_fallback.json`: provider-neutral jobs
for `missing` and `thin` needs. It does not produce accepted evidence and does
not bypass the material-map lifecycle.

## Why

The story-soul layer can describe required inserts and panels, but real projects
will still have gaps. Without a deterministic bridge from delta to generation
jobs, agents either:

- manually invent prompts outside the contract, or
- try to use generated assets as if they were already accepted material.

Both are unsafe.

## Contract

Inputs:

- required: `material_delta.json`
- optional: `material_needs.json`
- optional: `story_world.json`
- optional: `creative_concept.json`
- optional: `screenplay_beats.json`
- optional: `director_shot_plan.json`

Output:

- `material_generation_fallback.json`

Rules:

- `material_delta.ok=false` produces no jobs.
- only `missing` and `thin` outcomes produce jobs.
- generated assets return to material-map as `candidate`, never `accepted`.
- every job carries `source_type=generated`.
- every job carries `must_not_claim_real_event=true`.
- provider execution remains external.

## Verification

Focused:

```text
python -m unittest tests.test_material_generation_fallback tests.test_material_needs -q
38 tests OK

python -m unittest tests.test_video_tools_command_catalog -q
4 tests OK
```

Full:

```text
python -m unittest discover -s tests -q
1516 tests OK
```

Practical review:

- `.tmp/mgf1_director_review/case_a_training_066`
- `.tmp/mgf1_director_review/case_b_comic_5min`
- `.tmp/mgf1_director_review/case_c_event_bridges`
- `.tmp/mgf1_director_review/REVIEW.md`

The three cases confirm the useful scope:

- graduation/training symbolic memory inserts and chapter bridges;
- comic/photo story climax, aftermath, and resolution panels;
- real-event chapter and object bridges that do not pretend to be event proof.

## Deferred

Provider-specific execution remains outside this increment. Generated files
still need a provider run, ingest, material-map review, candidate satisfies edge,
fresh delta rerun, and human acceptance before BUILD.

