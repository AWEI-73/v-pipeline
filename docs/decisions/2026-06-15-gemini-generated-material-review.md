# Gemini-generated material review (2026-06-15)

## Scope

Synthetic test set:
`C:\Users\user\.gemini\antigravity\brain\b9af86b4-38e1-4748-890b-9e2c7d0a991b`

Theme: mountain-rescue training graduation. The set intentionally includes
seven story needs plus three distractors.

## Mechanical review

- Requested/generated: `36/36`; no missing or duplicate filenames.
- Need distribution: N01=4, N02=5, N03=6, N04=5, N05=5, N06=4, N07=4,
  DISTRACTOR=3.
- Claimed scale distribution: wide=10, medium=16, close=10.
- Actual dimensions: 29 images are `1024x1024`; 7 are `896x504`.
- No exact byte-identical duplicate images.
- `generated_material_manifest.json` is parseable and references every image.

## Visual and semantic findings

1. The set is usable for Pipeline testing. It contains clear establishing,
   action, detail, reaction, payoff, night, ceremony, and distractor images.
2. The requested 16:9 constraint was not followed consistently. Most images
   are square; this is useful for testing crop/treatment behavior.
3. Character identity drifts between images. Uniform color and rescue theme are
   fairly consistent, but faces, gender mix, helmets, and instructor identity
   vary. Treat this as a real-world continuity defect, not as one canonical cast.
4. The intentional assembly duplicate is visually similar but not exact. The
   forest distractor is clearly irrelevant. The bad-group-photo distractor is
   visibly weaker and edge-cropped.
5. The generated manifest must not be accepted as canonical review evidence:
   11 scenes use `Cinematic documentary` as `visual_family`, which describes
   style rather than visible content; other family/action values use inconsistent
   granularity and casing. Some Chinese prose fields are mojibake.

## Pipeline baseline

Generated artifacts are under `.tmp/gemini-generated-test/`.

- `ingest-meta`: 36 photos recognized.
- `material-map`: 36 per-asset maps written.
- `project-material-map`: asset_count=36, scene_count=36.
- Baseline VD0 shallow-label coverage: `0/36`.
- `ready_for_vd2=false`, blocked by visual-family coverage, angle-scale
  coverage, and missing independent consistency evidence.

This is correct: the Pipeline inventories the files but does not trust the
generator-authored manifest as an independent visual review.

## Next worker acceptance contract

An independent reviewing Agent must inspect the actual images and write
`visual_diversity_review_gemini.json` against asset IDs in
`.tmp/gemini-generated-test/project_material_map.json`.

The review must:

- not copy labels from `generated_material_manifest.json`;
- use coarse visible-content families, not style names;
- use only `wide|medium|close` for `angle_scale`;
- label all 36 scenes, including distractors;
- explicitly preserve similar images as the same family where appropriate;
- report continuity, aspect-ratio, and metadata defects separately;
- make no BUILD or VD2-ready claim.

Codex will apply the verdict with `visual-diversity-review`, run
`visual-diversity-coverage`, compare it with an independent second review, and
only then decide whether VD2 soft-ranking has sufficient evidence to begin.
