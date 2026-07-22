# Hermes Pipeline Boundary Charter

This file is the shared route boundary for every Hermes Video Pipeline skill.
Every pipeline branch must fail closed when these rules are not satisfied.

## Stage 0 entry lock

Do not direct-cut from a fuzzy request.

This lock applies to new, fuzzy, or whole-video intake. Before story, material
map, generated fallback, effects, Remotion, `contract-run`, or render work for
such an intake, create or verify the Stage 0 package:

- `project_brief.json` or `brief/project_brief.json`
- `project_brief.md` when user-facing summary is useful
- `interaction_log.md`
- `video_intent.json`

Existing candidate/draft bounded patch is the explicit exception. When an exact
candidate/run and its locked and dirty layers are already bound, the patch does
not require a new Stage 0 package; read the existing route context and enter
Workbench/Brownfield. If the candidate/run or layer boundary is unknown, fail
closed and recover that context instead of inventing a new intake.

`video_intent.json` must be produced by Video Intent Planner and must include
`input_state`, `entry_path`, `route`, `video_type`, `audience`, `goal`,
`target_length`, `material_availability`, `text_availability`,
`required_followup_questions`, `assumptions`, `handoff_to`, and
`handoff_packet`.

If the user gave a target duration, write it as `target_length`. If target
duration is unknown and changes the route or build shape, include it in
`required_followup_questions`.

If `required_followup_questions` is non-empty, stop and ask. Do not enter the
next pipeline branch by guessing.

## No direct-cut rule

For requests like "make/edit/cut a graduation/event/training/story video",
missing route-changing facts must block:

- material path or material availability;
- target length;
- audience;
- purpose / desired effect;
- tone or style direction;
- generation / reshoot permission;
- must-have people, scenes, events, or beats.

The operator may write assumptions, but assumptions do not unlock BUILD.

## Branch ownership

- Main route owns orchestration and `next_action`.
- Material Map owns material truth and coverage.
- Generated Material Producer owns generated candidate files, not truth.
- Effect Factory owns effect design and bounded effect handoff.
- Remotion Effect Worker owns short effect assets, not final assembly.
- Workbench/Brownfield owns draft patches, not canonical story or material truth.
- Verify owns delivery findings after a candidate render.

No branch may overwrite another branch's canonical artifact to make progress.

## BUILD and delivery locks

Do not run `contract-run`, render, or write `final.mp4` unless all are true:

- Stage 0 has no blocking `required_followup_questions`;
- route handoff names the next owner in `handoff_packet`;
- required material/story/effect branch artifacts exist for that route;
- current branch gate says ready, not candidate/thin/missing/blocked;
- draft Workbench/Brownfield changes have been accepted by the backend route.

When unsure, set `next_action` to ask/review/repair. Fail closed.
