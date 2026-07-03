# Work Order Template: Storybook Run × Happy-Path Probe

Purpose: every storybook demo video doubles as a real happy-path probe.
Copy this file to `2026-MM-DD-storybook-<case-name>.md`, fill the brackets,
dispatch. One video per order.

Two deliverables per run: (1) a finished video + its storybook entry,
(2) a probe report of every rough edge met on the way.

## Fill before dispatch

- Case name: [e.g. graduation-mv]
- Brief (verbatim, as a real user would type):
  [「幫我把這場畢業典禮的素材剪成 3 分鐘回顧 MV,溫暖收尾」]
- Materials: [path to real source folder / "none — story-first" / stock]
- Expected entry path: [material-first / structure-first / needs-context]
- Target length & delivery: [e.g. 180s, 16:9, subtitles required]

## Rules (probe ≠ repair)

1. Enter through the front door: `docs/START_HERE_VIDEO_PIPELINE.md`
   Rule Zero → `skills/video-pipeline.md` → `runtime.py` /
   `state.json.next_action`. NEVER hand-run ffmpeg or stitch materials
   outside the pipeline — the probe is only valid if you travel the same
   road a user's agent would.
2. You may answer interactive questions the pipeline asks (record Q&A
   verbatim). You may make workbench draft adjustments (record them).
3. When the route stalls, dead-ends, or does something surprising:
   capture `state.json`, the dashboard next_action, and the artifact that
   caused it → write a probe finding → then TRY to continue via legitimate
   means (revision loop, workbench patch, rerun). If truly stuck, stop and
   report — do NOT modify pipeline code, tests, skills, or registry in this
   order. Repairs become separate work orders.
4. Owner zone: your run folder under `runs/`, plus this order's report
   section. Nothing else in the repo.

## Record throughout (the storybook entry needs all of this)

- Full prompt(s) and interactive answers.
- Every `next_action` transition (the trace is the story of the route).
- Gates passed and their evidence artifacts.
- External costs: API calls made (provider, count, est. cost), wall time.
- Human/agent interventions: what needed a decision vs what was automatic.
- Final artifacts: final.mp4 (or furthest artifact reached), verify result.

## Report format (append below when done)

```
### Result: [completed / stalled at <next_action>]
- Video: runs/<run>/final.mp4, duration Xs, verify score N
- Route trace: intent → ... → complete (with timestamps)
- Cost: $X.XX (breakdown), wall time Xh
- Interventions: [list]
### Probe findings
- [P1] <symptom> | state: <next_action> | artifact: <file> |
  severity: blocker/rough/cosmetic | suggested fix owner: <module/skill>
### Storybook entry draft
- One-paragraph pitch + prompt + cost + gates, ready for README storybook
### Smoke candidate
- [yes/no] this route is now proven and worth pinning as an e2e-smoke case
```

## After acceptance (integrator's checklist, not yours)

- Blocker/rough findings → repair work orders.
- Proven new route → e2e-smoke case order.
- Storybook entry → README.
