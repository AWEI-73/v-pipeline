---
name: video-intent-planner
description: Use at Stage 0 before story, material, or BUILD work to decide input state, entry path, follow-up questions, and handoff.
---

# Video Intent Planner

Stage 0 is **Video Intent Planner**. It is infrastructure, not a template for a
specific video type.

Use it before Story Soul, Material Truth, generated material fallback, BUILD,
Workbench, Brownfield, Node14, or Remotion.

## Responsibility

Decide only what changes the route:

- video purpose and goal;
- audience;
- target length;
- video type;
- existing material availability, quality, and quantity;
- text/article/outline/story availability;
- input state: `material_available`, `text_available`, `idea_only`, or
  `unknown`;
- entry path: `material-first`, `structure-first`, or `needs-context`;
- whether generated material fallback may be needed;
- the next handoff target.

Do not write a teaching template, event template, renderer plan, BUILD ranking
rule, or effect/Remotion route here.

## Canonical Artifact

Write `video_intent.json` through:

```powershell
python video_tools.py video-intent-plan project_brief.json --out video_intent.json
```

Required shape:

```json
{
  "artifact_role": "video_intent",
  "stage": "Video Intent Planner",
  "input_state": "material_available | text_available | idea_only | unknown",
  "entry_path": "material-first | structure-first | needs-context",
  "video_type": "teaching | storybook | graduation-event | personal-memory | brand-product | ...",
  "audience": "...",
  "goal": "...",
  "material_availability": "existing | none | partial",
  "text_availability": "article | outline | brief | script | story | none | unknown",
  "route": "material-first | structure-first | needs-context",
  "legacy_route": "existing-material-first | story-first | hybrid | null",
  "required_followup_questions": [],
  "assumptions": [],
  "handoff_to": "material_map_lifecycle | upstream_structure_route | ask_followup",
  "handoff_packet": {
    "owner": "material_map_lifecycle | upstream_structure_route | Video Intent Planner",
    "first_action": "material_map_quick_inventory | story_soul_blueprint | ask_followup_questions",
    "required_inputs": [],
    "expected_outputs": [],
    "return_to": "..."
  }
}
```

## Interaction Rule

If route-changing information is missing, ask a small number of key questions
instead of guessing:

- What kind of video is this: teaching, event recap, story, brand short,
  personal memory, or other?
- Do you already have material? Is it complete, partial, or uncertain quality?
- Do you have an article, outline, script, story, or only a loose idea?
- Roughly how long should the final video be?
- Who is the audience?
- Should the style feel documentary, energetic, warm, story-driven, MV-like, or
  clearly instructional?

## Handoff

- `material-first` -> run material map lifecycle first, then use map findings
  to reduce ambiguity and build structure.
- `structure-first` -> run upstream structure route; if no material exists, run
  initial material delta before generated material fallback.
- `needs-context` -> ask follow-up questions before choosing a handoff.

`handoff_packet` is the run-folder / route-task handoff summary. It records the
next owner, first action, required inputs, expected outputs, and return point so
the next operator can continue without starting VIP1/VIP2 templates.

Compatibility:

- `existing-material-first` maps to `material-first`.
- `story-first` maps to `structure-first`.
- `hybrid` is not a primary Stage 0 entry path; partial material enters
  `material-first`, then material delta chooses generation, reshoot, rewrite,
  drop, or waiver.

Generated material remains fallback/candidate material until provider mapping,
import, explicit review, and fresh material delta pass.
