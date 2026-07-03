# Work Order: Clean Clone Verification

Date: 2026-07-04
Goal: prove the stranger's-machine experience. The asset store retrofit and
setup guide exist; only a real from-scratch walkthrough proves they work.
This order produces a gap report and guide fixes, NOT pipeline code changes.

## Owner zone

- The clone directory itself (create under a path OUTSIDE this repo,
  e.g. `C:\Users\user\Desktop\vp_clone_test\`) — everything there is yours.
- In THIS repo, you may modify ONLY: `docs/setup/setup-and-first-run.md`,
  `docs/setup/distribution-manifest.md`, `README.md` (setup-related lines
  only), and this work order (report append).

## Forbidden

- Any other file in this repo. If a gap requires a code fix, record it as a
  work-order candidate in your report — do not fix code in this order.
- Do not copy your working `.env`, caches, `.tmp/`, or `runs/` into the
  clone. The point is starting from nothing.

## Procedure

1. `git clone <this repo path> C:\Users\user\Desktop\vp_clone_test`
   (local clone is fine; note that a real user would also not have
   `reference repo/`, `runs/`, `.tmp/` — they are untracked/ignored, so the
   clone naturally lacks them; confirm and record what IS missing).
2. Open `docs/setup/setup-and-first-run.md` in the clone and follow it
   LITERALLY, line by line, as a stranger would. Every place where reality
   differs from the guide — missing step, wrong path, unstated assumption
   (e.g. miniconda already installed, ffmpeg on PATH), unclear wording —
   goes into the gap list with the exact guide line.
3. Verification battery inside the clone (all via the guide's commands):
   - `tools/preflight.py --strict`
   - both e2e-smoke cases
   - `registry-audit`
   - full suite
   - `asset-path-audit --strict` on a fresh smoke-produced run dir
   - start the dashboard server, load `/` in a browser, confirm the
     workbench renders with zero console errors (no run data is fine —
     record what an empty-state user sees, that IS the first-run UX).
4. Classify each gap: (a) guide fix — fix it in THIS repo's guide now;
   (b) code/packaging gap — work-order candidate with details;
   (c) empty-state UX observation — record only.
5. Re-clone into a SECOND fresh directory and re-walk the updated guide.
   Acceptance = the second walkthrough completes the whole battery with no
   undocumented steps.
6. Delete both clone directories when done.

## Acceptance

- Second clean walkthrough: preflight strict exit 0, both smokes exit 0,
  full suite OK, strict asset audit 0 findings, workbench loads.
- Guide fixes committed: `Fix setup guide against clean clone walkthrough`.
- Report appended below: gap list with classifications, work-order
  candidates, empty-state UX notes, second-walkthrough evidence tails.
  Report commit: `Record clean clone verification report`.
