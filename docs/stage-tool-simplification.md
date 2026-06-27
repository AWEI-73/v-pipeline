# Stage Tool Simplification

This document is the compact operating map for Hermes stage tools.

Do not make readers open an attachment to understand the tool route. References
may add depth, but the main skill/tool relationship must be visible here and in
each skill's `Tool Contract` block.

## Driver Principle

Agents fail when they know a tool exists but do not know whether the current
skill may use it. The project therefore keeps three layers aligned:

1. Skill text: human-readable trigger, boundary, allowed tools, forbidden tools,
   outputs, and stop conditions.
2. Shared tool layer: reusable Python CLIs and `video_tools.py` commands.
3. Audit script: machine check that every `tools/*.py` script has a skill owner
   and that skill contracts have enough operational detail.

The skill body is the memo body. It should be detailed enough to execute the
route without chasing attachments, but compact enough to fit in agent context.

## Entry Precedence

Use this order when a user request matches multiple skills:

1. **resume existing run**: a run folder, "stuck run", "continue", "resume", or
   "review this output" starts with `tools/pipeline_home.py`. The current cursor
   decides the owner.
2. **whole-video request**: making a whole film, recap, memory video, story
   video, graduation video, or broad revision starts at Stage 0 even when the
   sentence includes side-branch words such as music, transition, warm,
   hot-blooded, cinematic, subtitle, or effect.
3. **bounded side branch**: Effect Factory or Soundtrack Arranger may be first
   owner only when the user asks for a bounded effect or music/song/BGM job,
   not a full video.
4. **draft patch**: existing draft, rough cut, clip replacement, subtitle patch,
   and local finishing edits belong to Brownfield/Workbench until reviewed.
5. **soundtrack intent vs audio repair**: soundtrack intent means music, song,
   BGM mood, source, license, or reference track. audio repair means volume,
   normalization, ducking, speech preservation, or final audio mix; route it
   through Brownfield/Workbench or Audio Director after state inspection.
   whole-video subtitle intent is a child intent after Stage 0; subtitle repair
   on an existing draft belongs to Brownfield/Workbench or Subtitle Director.
6. **generated candidate fallback**: story/article/idea first produces
   structure, material needs, and material delta. Generated assets are candidate
   fallback only after that gate and explicit review.

## Stage Tool Matrix

Stage 0 package is the minimum intake bundle before branch work:
`project_brief.json`, `interaction_log.md`, and `video_intent.json`.
`video_intent.json` records `target_length` when known; if target length or
another route-changing fact is unknown, it must appear in
`required_followup_questions` and the next branch must not guess.

| Stage / branch | Purpose | Canonical entry | Key outputs | Stop / pass rule |
|---|---|---|---|---|
| Route / Stage 0 | classify input state, entry path, and next handoff | `skills/video-pipeline-route.md`, `tools/pipeline_home.py`, `video_tools.py video-intent-plan` | `project_brief.json`, `interaction_log.md`, `video_intent.json`, route cursor | stop on missing route-changing information or non-empty follow-up questions |
| Material Map | prove material truth, coverage, deltas, gaps, and rough-cut supply | `skills/material-map.md`, material-first acceptance tools, material lifecycle commands | `materials_db.json`, `project_material_map.json`, `material_delta.json`, `rough_cut_plan.json` | stop on `await_map_review`, missing must-have needs, invalid maps, or unreviewed generated assets |
| Spec / Build | validate and dry-build the contract without guessing around gates | `skills/spec-contract.md`, boundary/build smoke tools | `segment_contract.json`, `build_profile.json`, dry-build reports | pass only when spec/supply/build invariants are green |
| Brownfield / Workbench | draft local edits without overwriting canonical truth | `skills/brownfield-edit.md`, workbench patch tools | draft patch artifacts, preview handoff, review reports | stop before canonical promotion; never write `final.mp4` from draft status |
| Effect Factory | translate effect intent into reviewable controls and bounded worker payloads | `skills/video-effect-factory.md`, visual technique and effect acceptance tools | `visual_technique_plan.json`, effect contracts, review/handoff artifacts | stop on unconfirmed candidate parameters or missing rendered evidence for required effects |
| Soundtrack | plan music/song/licensing and hand off accepted audio decisions | `skills/soundtrack-arranger.md`, soundtrack tools | `soundtrack_plan.json`, `music_source_candidates.json`, `sound_license_manifest.json` | block delivery when license metadata is missing or music is reference-only |
| Verify / Delivery | inspect outputs, evidence, and fail-closed delivery status | `skills/verify.md`, verify/reviewer tools | verify reports, review reports, delivery gate evidence | fail closed on missing evidence, stale artifacts, or hard-gate review failure |
| Dashboard / Workbench UI | review visible artifacts and draft user edits | `skills/dashboard.md`, dashboard/workbench servers and frontend smoke | dashboard state, workbench UI evidence, export artifacts | UI is a surface; backend/agent review owns canonical promotion |

## Skill Tool Contract

Every operational skill that owns tools should include one machine-readable
block:

```markdown
<!-- TOOL_CONTRACT_START -->
{
  "version": 1,
  "skill": "material-map",
  "stage_owner": "material_map",
  "triggers": ["user has footage", "material-first route"],
  "canonical_tools": [
    {
      "tool": "tools/material_first_boundary_acceptance.py",
      "when": "run a bounded material-first boundary acceptance without render",
      "inputs": ["source folder", "video_intent.json"],
      "outputs": ["material_first_boundary_acceptance_report.json"],
      "stop_if": ["report ok=false", "await_map_review"]
    }
  ],
  "supporting_tools": [],
  "forbidden_tools": ["contract-run", "final.mp4 render"]
}
<!-- TOOL_CONTRACT_END -->
```

Required fields for each tool entry:

- `tool`
- `when`
- `inputs`
- `outputs`
- `stop_if`

Use concise Chinese/English text for humans. The audit only requires structure,
not a perfect ontology.

## Tool Visibility Labels

| Label | Meaning |
|---|---|
| `canonical` | safe primary entry for a skill/stage |
| `supporting` | may be used after the canonical entry identifies the need |
| `internal` | implementation helper; not a semantic user entry |
| `diagnostic` | inspection, smoke, report, or debug helper |
| `legacy` | kept for compatibility; do not use as first route |
| `adapter` | external/provider/backend bridge |
| `draft-only` | may create previews or patches, not canonical truth |

## Audit Rules

Run:

```powershell
python tools/skill_tool_contract_audit.py --skills-dir skills --tools-dir tools --json
```

The audit fails when:

- a `TOOL_CONTRACT` block is invalid JSON;
- a contract is missing `skill`, `stage_owner`, `triggers`,
  `canonical_tools`, or `forbidden_tools`;
- a canonical/supporting/internal/diagnostic tool entry is missing `tool`,
  `when`, `inputs`, `outputs`, or `stop_if`;
- a `tools/*.py` script has no owning skill contract;
- two skills claim the same canonical script without an explicit shared design.

The first goal is coverage and clarity. Runtime enforcement can come later.

## Change Rule

When adding, renaming, or deleting a Python tool:

1. Update the owning skill's `Tool Contract`.
2. Run `python tools/skill_tool_contract_audit.py --skills-dir skills --tools-dir tools --json`.
3. Run `python -m unittest tests.test_skill_tool_contracts -q`.
4. If the tool is a real operator entry, also update `RUNBOOK.md` or the
   relevant stage route document.
