# Canonical Route Solidification Review

Date: 2026-06-20
Status: accepted

## Purpose

Stabilize the full Hermes Video Pipeline route so a cold-start agent can run or
review the flow without relying on conversation history.

This is route/process solidification, not template solidification. Story
templates, genre routes, and reusable episode formats remain future extensions.

## What Was Added

- `docs/canonical-video-pipeline-route.md`
  - Stable stage order from Intake to Delivery.
  - Skill-to-tool mapping.
  - Artifact ownership and canonical/draft boundaries.
  - Legacy alias mapping for M6, SRP, FX, Node14, and Brownfield Edit.
- `skills/video-pipeline-route.md`
  - Operator entry skill for full-route execution.
  - Route selection for existing material, generated material, hybrid material,
    and Workbench/Brownfield edit.
  - Resume-existing-run checklist.
  - Minimal CLI skeletons for common routes.
- `tools/canonical_route_acceptance.py`
  - Static route acceptance harness.
  - Checks stage order, skill files, tool surface, required artifacts, roadmap,
    and docs index links.
- `tests/test_canonical_route_acceptance.py`
  - Focused regression tests for route order, operator skill content, index
    linkage, and harness failure mode.

## Canonical Stage Order

1. Intake
2. Story Soul
3. Director Shot Plan
4. Material Truth
5. Coverage / Decision Gate
6. BUILD Planning
7. Official Render
8. Verify
9. Workbench Draft Review
10. Brownfield Edit / Finishing
11. Delivery

## Acceptance Evidence

Commands run:

```powershell
python -m unittest tests.test_canonical_route_acceptance -v
python tools/canonical_route_acceptance.py --out .tmp/canonical_route_acceptance.json
python -m unittest tests.test_canonical_route_acceptance tests.test_interactive_skill_flow_docs tests.test_effects_roadmap_alignment_docs -q
python -m unittest discover -s tests -q
```

Results:

- Focused route tests: 5 OK.
- Static route acceptance: OK.
- Related docs tests: 14 OK.
- Full regression during this solidification pass: 1616 tests OK.
- Acceptance summary: 11 stages, 7 skills, 15 tools, 21 artifacts.

## Subagent Cold-Read Review

An explorer subagent was asked to cold-read:

- `docs/canonical-video-pipeline-route.md`
- `skills/video-pipeline-route.md`
- `tools/canonical_route_acceptance.py`
- `roadmap.md`
- `docs/INDEX.md`

First review:

- No route-order blocker.
- Operator skill was sufficient for cold start.
- Suggested non-blocker hardening:
  - add resume-existing-run steps;
  - add minimal CLI skeletons;
  - expand artifact acceptance coverage;
  - update roadmap/index metadata.

Those suggestions were implemented.

Second review found one real blocker in the CLI skeletons:

- `contract-run` skeleton missed required `--music`;
- `workbench-handoff-validate` used an invalid `--artifact-root` flag;
- `effect-revision-request` used invalid `--timeline`.

Those skeletons were corrected against each command's actual `--help` output.

Final subagent verdict:

- No blocker.
- Route solidification is acceptable.
- Remaining note: skeletons are examples and still require actual inputs such
  as `materials_db.json`, `bgm.mp3`, and `workbench_handoff.json`.

## Boundary

This does not rename existing implementation nodes or remove historical
roadmap evidence. It creates a stable public route map over the existing
implementation.

Do not treat Workbench, Remotion, or generated images as canonical truth:

- Workbench remains draft/patch authority.
- Remotion remains an optional effect adapter route.
- Generated images become material only after provider output mapping, import,
  explicit review, fresh material delta, and BUILD gate.

## Next Use

For a full project run, a cold-start agent should begin with
`docs/START_HERE_VIDEO_PIPELINE.md`, then use `skills/video-pipeline-route.md`
and `docs/video-pipeline-operating-map.md` to pick one of:

- existing-material route;
- generated-material route;
- hybrid route;
- draft review / Brownfield route.

## Addendum: Start-Here / Reviewer Policy Consolidation

Later on 2026-06-20, the route entrypoint was tightened without changing the
runtime:

- Added `docs/START_HERE_VIDEO_PIPELINE.md` as the single human/agent entry.
- Added `docs/video-pipeline-operating-map.md` as the full stage/skill/tool/
  artifact operating manual.
- Added `docs/artifact-reviewer-map.md` as the lightweight reviewer policy
  (`light`, `normal`, `deep`) so creative review does not get mixed into
  technical VERIFY.
- Updated `skills/video-pipeline-route.md`, `roadmap.md`, and `docs/INDEX.md`
  to point through the same entry path.
- Hardened `tools/canonical_route_acceptance.py` so route acceptance now fails
  if the start-here document, operating map, or reviewer map is missing or not
  linked.

Fresh focused evidence after this addendum:

```powershell
python -m unittest tests.test_canonical_route_acceptance -v
```

Result: 6 tests OK.
