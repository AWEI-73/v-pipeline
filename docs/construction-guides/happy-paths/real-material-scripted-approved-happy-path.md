# Real-Material Scripted Approved Happy Path

Date: 2026-07-06

## Status

This is the first completed real-material scripted delivery happy path for the
current video pipeline.

It proves the technical route can run from real source material to an approved
delivery package:

```text
real source folder
  -> human_preproduction_brief.json
  -> scripted story contract
  -> story_to_material_map.json
  -> source speech preservation
  -> VoxCPM narration
  -> source-folder music
  -> subtitles / audio mix
  -> final.mp4
  -> delivery gate
  -> human story approval
  -> delivery package
```

## Source And Package

Source folder:

`C:\Users\user\Downloads\微電影素材\_整理後`

Approved delivery package:

`C:\Users\user\Desktop\video_pipeline\deliveries\real_material_scripted_approved_20260706-200007`

Final video:

`C:\Users\user\Desktop\video_pipeline\deliveries\real_material_scripted_approved_20260706-200007\final.mp4`

Technical state:

- `pipeline_home.py`: `DONE / complete`
- `delivery_gate`: `pass=true`
- `story_human_review_decision.json`: `decision=approved`, `reviewer=human`
- final duration: about 48 seconds
- streams: video + audio

## What This Proves

- The pipeline can ingest real material and produce a complete technical
  candidate.
- VoxCPM narration can be integrated.
- Source speech can be preserved.
- Music can come from source-folder audio instead of a synthetic generated bed.
- The delivery gate and human story approval gate can both close.
- A delivery package can be created with ffprobe, checksums, gate evidence,
  approval evidence, review packet, and music-use evidence.

## What This Does Not Prove

This happy path must not be treated as mature final creative quality.

Known content/product issues from review:

- Opening and closing are not strong enough for a polished graduation film.
- The closing relies on white title-card style text and feels closer to a
  slideshow than a designed ending.
- The film lacks a clear higher-level theme beyond a sequence of training
  materials.
- Music, narration, and source speech can compete for attention.
- Preserved source speech needs readable subtitles and intelligibility review.
- Some package/review artifacts had Chinese mojibake or placeholder text.
- Vertical footage appears with large black side bars.
- The training section is not yet a structured MV catalog.

## Current Product Interpretation

This is a technical happy path:

`real-material scripted production happy path with source-folder music and explicit human approval`

It is not yet the target product path for a polished graduation training film.

## Graduation Film Direction From User

The target product is a graduation training film, not a generic event recap.

Canonical shape:

1. Opening story.
2. Training MV catalog as the longest body section.
3. Supervisor speech / encouragement.
4. Teacher and class introduction.
5. Closing story.

Training MV catalog modules:

- basic training items
- advanced training items
- certification items
- physical activity items
- encouragement / morale activities
- daily life records, optional
- other special activities, extensible

Editorial intent:

- The MV body is long because the training class spans about 5.5 months.
- The stable core is the training catalog; the variable parts are mainly the
  opening story, closing story, and the logical ordering/emphasis of modules.
- Hot-blooded music belongs mainly in the training MV section.
- Supervisor speech should preserve real source speech when intelligible and
  must have subtitles.
- Teacher/class introduction can use music and effects, but must remain
  readable.
- Opening and closing should be designed story sections, not plain white cards.

## Next Product Route

The next route should build:

```text
graduation film canon
  -> graduation film blueprint
  -> story shell
  -> training catalog map
  -> reviewable dry-run packet
```

This should happen before another render. The pipeline needs to understand the
graduation-film product structure before it can produce a stronger final film or
support story retargeting.

