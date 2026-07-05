# Material-First Golden Fixture

This fixture is a tracked deterministic recipe, not a media archive. The
acceptance helper reads `fixture_manifest.json`, generates tiny JPEG media under
`.tmp/material_first_golden_path/source`, writes a matching wall verdict, and
runs the material-first boundary acceptance chain.

Official replay command:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py replay-acceptance --scenario material-first-golden-path --out .tmp/material_first_golden_replay.json
```
