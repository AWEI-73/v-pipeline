# Material Phase M3 Edit Points Plan

## Goal

Cut on meaningful speech and action boundaries, and make jump cuts reviewable
before destructive processing.

## Tasks

1. Plan speech-safe edit windows with priority: speech, scene, motion.
2. Derive action phases (`rise`, `peak`, `settle`) from mapped motion evidence.
3. Produce jump-cut plans from speech/silence maps and apply agent verdicts.
4. Apply approved jump cuts with lineage into processed material.
5. Wire M3 edit-point planning into the render plan and verify real material.

## Acceptance

- A keep-audio window never cuts through a mapped speech run.
- Action windows enter before the peak and exit after settle.
- Bridge scenes are excluded from primary action selection.
- Jump-cut apply requires an accepted verdict and records lineage.
