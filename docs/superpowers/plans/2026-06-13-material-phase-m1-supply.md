# Material Phase M1 Supply Plan

## Goal

Make script duration and segment feasibility derive from actual material supply,
not from requested story length.

## Tasks

1. Add deterministic per-asset material maps with scene, speech, and motion
   evidence.
2. Add a supply review that estimates useful shots, function coverage, and
   `max_honest_duration_sec` for each segment.
3. Add SPEC review rule B6 so scripts cannot promise more duration than the
   available material can honestly support.
4. Extend the existing `material-map` CLI without breaking its Markdown mode.
5. Verify focused tests, the full suite, and a CLI smoke run.

## Acceptance

- A 30-second segment backed by 2 videos and 3 photos is marked `thin` when its
  estimated useful-shot supply supports less than 30 seconds.
- A segment with no usable material is marked `gap`.
- SPEC review blocks `script_overreach` when requested duration exceeds the
  supply review's maximum honest duration.
