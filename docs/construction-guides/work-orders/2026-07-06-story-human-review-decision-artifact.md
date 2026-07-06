# Work Order: Story Human Review Decision Artifact

Date: 2026-07-06

## Goal

Add a formal human story review decision artifact so `story_human_review_required` can be cleared intentionally. A scripted technical candidate with agent-filled or inferred story-to-material mapping should remain in `WAITING / human_story_review` until a human decision accepts, requests revision, or rejects the story mapping.

This closes the current gap after scripted delivery gate hardening: the system can now surface human review, but it cannot yet consume a human review decision.

## Owner Zone

- `video_pipeline_core/delivery_gate.py`
- `tools/pipeline_home.py`
- `tests/test_delivery_gate.py`
- `tests/test_pipeline_home.py`
- New focused tests under `tests/` if needed
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/construction-guides/work-orders/2026-07-06-story-human-review-decision-artifact-report.md`

## Forbidden Zone

- `.env`
- `.venv_voxcpm/`
- `reference repo/`
- `Downloads/`
- Existing `.tmp/` runs except read-only smoke inspection
- Provider/runtime code
- Git commit, branch, push, or PR operations

## Runtime

Use only:

`C:\Users\user\miniconda3\python.exe`

Do not use bare `python`, `pytest`, or another interpreter.

## Artifact Contract

Canonical artifact name:

`story_human_review_decision.json`

Minimum shape:

```json
{
  "artifact_role": "story_human_review_decision",
  "version": 1,
  "decision": "approved | revision_requested | rejected",
  "reviewer": "human",
  "reviewed_artifacts": {
    "story_contract": "story_contract.json",
    "story_to_material_map": "story_to_material_map.json",
    "story_to_final_alignment_report": "story_to_final_alignment_report.json"
  },
  "approved_beat_ids": ["..."],
  "revision_notes": [],
  "rejected_beat_ids": [],
  "created_at": "ISO-8601 or repo-local timestamp"
}
```

Rules:

- Only `reviewer="human"` or `reviewer_type="human"` may clear `story_human_review_required`.
- Agent/self review artifacts may remain visible but must not clear the warning.
- `decision="approved"` clears `story_human_review_required` only if all required story beats are approved or no beat-level list is required by the existing map shape.
- `decision="revision_requested"` keeps the run in review/repair state and should route to revise story/material mapping.
- `decision="rejected"` blocks or routes to repair; it must not pass silently.
- Missing or malformed decision leaves current `story_human_review_required` behavior unchanged.

## Ordered Pieces

1. Add red-first tests for approved human decision clearing `story_human_review_required` from delivery gate warnings.
2. Add red-first tests proving agent/self review does not clear the warning.
3. Add red-first tests for `revision_requested` and `rejected` routing in delivery gate and/or `pipeline_home`.
4. Implement decision loading and validation in the existing gate/home boundary.
5. Update `pipeline_home`:
   - approved human review + delivery gate pass + final.mp4 -> `DONE / complete`
   - revision requested -> `WAITING` or `REPAIR` with next action to revise story/material mapping
   - rejected -> fail-visible repair/review stop
6. Update docs/registry to list the artifact and state transitions.
7. Smoke the repaired scripted run read-only:
   - Without decision: still `WAITING / human_story_review`.
   - With a temporary copied run or temp fixture containing approved decision: expected `DONE / complete`.
   - Do not mutate the existing `.tmp` run unless writing inside a temp copy.
8. Write final report.

## Acceptance Commands

Run from repo root and record exit codes.

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_delivery_gate tests.test_pipeline_home
```

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_delivery_gate tests.test_delivery_gate_report tests.test_pipeline_home tests.test_final_product_verify
```

```powershell
git diff --check
```

Report content check:

```powershell
@'
from pathlib import Path
import sys
p = Path("docs/construction-guides/work-orders/2026-07-06-story-human-review-decision-artifact-report.md")
text = p.read_text(encoding="utf-8")
required = ["Decision artifact", "approved", "revision_requested", "rejected", "Acceptance", "Deviations", "Next recommended work"]
missing = [x for x in required if x not in text]
print({"report_exists": p.exists(), "missing": missing})
sys.exit(0 if p.exists() and not missing else 1)
'@ | C:\Users\user\miniconda3\python.exe -
```

## Stop-Loss Rules

- Do not make non-human or missing review clear `story_human_review_required`.
- Do not remove existing story-to-material warning behavior for runs without a decision artifact.
- Do not mutate existing production `.tmp` runs for acceptance; use temp copies/fixtures.
- If the intended product state for `rejected` is ambiguous, implement fail-visible repair state and record the open question.

## Delegated Decisions

- Exact helper names and where to load the artifact, provided existing delivery gate/pipeline home style is followed.
- Whether `revision_requested` appears as `WAITING` or `REPAIR`, provided the next action is explicit and not `complete`.
- Exact beat-level approval validation, provided partial approval cannot silently clear review for uncovered required beats.
- Exact doc wording in registry/operating map.

## Final Report Requirements

Write:

`docs/construction-guides/work-orders/2026-07-06-story-human-review-decision-artifact-report.md`

Include:

- Files changed.
- Red-first evidence for approved, agent/self review, revision, and rejected cases.
- Implemented artifact shape and accepted decision values.
- How `delivery_gate` and `pipeline_home` behave for each decision.
- Acceptance commands and exit codes.
- Smoke result using the repaired scripted run or a temp copy.
- Deviations/skips/blockers.
- Next recommended work grounded in this artifact path.
