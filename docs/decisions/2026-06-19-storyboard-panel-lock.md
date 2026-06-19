# Storyboard Panel-Locked Rendering Boundary

## Decision

Generated comic/photo story material needs a `storyboard_panel_locked` mode.

For narrated comics, picture books, and storyboard-like videos, each generated
image is a semantic panel. BUILD should not fill a long voiceover segment by
borrowing other accepted images from the same need. It should extend the panel
duration, apply a light Ken Burns treatment, request more panels, or shorten the
narration.

## Why

The real imagegen E2E produced 21 manga-style panels. Two renders were compared:

- Auto-fill BUILD render: technically valid, but some panels felt semantically
  off because longer voiceover spans were filled with other accepted images.
- Single-use panel render: each of the 21 panels was used once and stretched to
  its TTS timing. This matched the story, subtitles, and voiceover better.

## Rule

```text
comic / picture-book / storyboard narration
  -> storyboard_panel_locked=true
  -> one panel per story beat
  -> stretch panel duration for voiceover
  -> generate more panels if needed

event MV / recap montage
  -> storyboard_panel_locked=false
  -> auto-fill accepted shots is allowed
```

## Acceptance Evidence

- `final_story_single_use_zh_voice.mp4`: 21 generated panels, each used once.
- `final_story_auto_fill_zh_voice.mp4`: normal BUILD auto-fill comparison.
- Both were uploaded to Drive under `video_pipeline_story_e2e_2026-06-19`.

## Boundary

This is a creative/rendering policy, not a material truth shortcut. Generated
assets still enter material-map as generated candidates and require explicit
review before they can count as coverage.
