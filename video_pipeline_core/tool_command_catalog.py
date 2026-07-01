"""Machine-readable grouping for the large ``video_tools.py`` CLI surface."""

from __future__ import annotations

from typing import Dict, Iterable, Mapping


COMMAND_GROUPS: Dict[str, str] = {
    # Legacy media utilities.
    "search": "legacy_media",
    "meta": "legacy_media",
    "download": "legacy_media",
    "probe": "legacy_media",
    "cut": "legacy_media",
    "concat": "legacy_media",
    "subtitle": "legacy_media",
    "mksrt": "legacy_media",
    "burnsub": "legacy_media",
    "script-run": "legacy_media",
    "title": "legacy_media",
    "tts": "legacy_media",
    "mix-audio": "legacy_media",
    "sfx-mix": "legacy_media",
    "srt": "legacy_media",
    "assemble": "legacy_media",
    "merge-final": "legacy_media",
    "analyze": "legacy_media",
    "curate": "legacy_media",
    "kenburns": "legacy_media",
    "grade": "legacy_media",
    "title-card": "legacy_media",
    "title-sequence": "legacy_media",
    "gen-bgm": "legacy_media",
    "music-fetch": "legacy_media",
    "collage": "legacy_media",
    "montage": "legacy_media",

    # External/provider optional commands.
    "pexels-search": "provider_optional",
    "pexels-download": "provider_optional",
    "capcut-draft": "provider_optional",
    "capcut-finalize": "provider_optional",

    # Project workspace and introspection.
    "project-init": "workspace",
    "project-new-run": "workspace",
    "video-intent-plan": "workspace",
    "state": "workspace",
    "commands-manifest": "workspace",
    "workflow-manifest": "workspace",
    "test-tiers": "verify",
    "reviewer-policy": "verify",
    "reviewer-role-review": "verify",
    "reviewer-aggregate": "verify",
    "run-layout-validate": "workspace",
    "workbench-handoff-validate": "workspace",
    "workbench-draft-rerender": "render",

    # Frontend/review surfaces.
    "serve": "frontend",
    "dashboard": "frontend",
    "story-map": "frontend",

    # Contract and SPEC/build entry commands.
    "validate": "contract",
    "contract-adapt": "contract",
    "spec-review": "contract",
    "capability-manifest": "contract",
    "supply-review": "contract",
    "director-supply-revise": "contract",
    "contract-dry-build": "contract",
    "contract-run": "contract",
    "generated-manifest": "contract",
    "generated-material-import": "material",
    "generated-image-provider-packet": "material",
    "image-agent-prompt-handoff": "material",
    "codex-imagegen-provider-fill": "material",
    "generated-material-produce": "material",
    "generated-material-review": "material",
    "light-effects-plan": "contract",
    "visual-technique-plan": "contract",
    "visual-technique-review-apply": "contract",
    "soundtrack-arrange": "contract",
    "soundtrack-provider-search": "provider_optional",
    "soundtrack-provider-download": "provider_optional",
    "soundtrack-import-url": "provider_optional",
    "soundtrack-audio-handoff-accept": "contract",
    "voiceover-provider-plan": "contract",
    "effect-intent-plan": "contract",
    "effect-revision-request": "contract",
    "effect-revision-draft": "contract",
    "effect-revision-apply": "contract",
    "effect-collage-refs": "contract",
    "remotion-template-manifest": "contract",
    "remotion-prompt-pack": "contract",
    "remotion-worker-outputs": "contract",
    "effect-render-verification": "verify",
    "remotion-worker-smoke": "provider_optional",
    "remotion-composite-draft": "render",
    "blueprint-coverage": "contract",
    "blueprint-compile": "contract",
    "blueprint-to-contract": "contract",
    "story-soul-to-contract": "contract",
    "creator-profile": "contract",
    "story-soul-blueprint": "contract",

    # Material-map lifecycle and material selection.
    "ingest-meta": "material",
    "caption-meta": "material",
    "material-map": "material",
    "match-mv": "material",
    "rank-local": "material",
    "validate-needs": "material",
    "lineage-link": "material",
    "material-delta": "material",
    "material-generation-fallback": "material",
    "material-revision": "material",
    "material-map-lifecycle": "material",
    "material-map-review-apply": "material",
    "material-wall-build": "material",
    "material-wall-review-apply": "material",
    "material-db-slice-from-wall": "material",
    "project-material-map": "material",
    "source-highlight-plan": "material",
    "source-material-matrix": "material",
    "source-section-map": "material",
    "source-motion-profile": "material",
    "source-dialogue-script": "material",
    "visual-diversity-coverage": "material",
    "visual-diversity-review": "material",
    "visual-family-normalize": "material",
    "jumpcut-plan": "material",
    "jumpcut-apply": "material",
    "jumpcut-review": "material",

    # BUILD helper commands.
    "action-progression-audit": "build",

    # Verification/audit commands.
    "verify": "verify",
    "timeline-audit": "verify",
    "broll-audit": "verify",
    "new-visual-audit": "verify",
    "black-frame-audit": "verify",
    "semantic-novelty-audit": "verify",
    "caption-audit": "verify",
    "keyframe-grid": "verify",
    "visual-audit": "verify",
    "verify-evidence": "verify",
    "final-product-verify": "verify",

    # Replay / acceptance proof commands.
    "replay-acceptance": "acceptance",
    "operator-flow-acceptance": "acceptance",
    "video-intent-acceptance": "acceptance",
    "reviewer-flow-acceptance": "acceptance",
    "route-task-next": "acceptance",
    "route-task-accept": "acceptance",
    "route-orchestrator-report": "acceptance",
    "route-orchestrator-acceptance": "acceptance",
}


GROUP_DESCRIPTIONS = {
    "workspace": "project/run workspace setup, state, and command discovery",
    "contract": "SPEC, contract, dry-build, and canonical contract-run entrypoints",
    "material": "material ingest, material-map lifecycle, and selection evidence",
    "build": "BUILD planning helpers that are not standalone delivery entrypoints",
    "verify": "post-build verification and audit commands",
    "frontend": "review/dashboard/story-map surfaces",
    "acceptance": "replay acceptance and evidence harnesses",
    "legacy_media": "older low-level media utilities kept for compatibility",
    "provider_optional": "optional external/provider-specific integrations",
}


WORKFLOWS = {
    "run_setup": {
        "description": "Create and validate a project run workspace.",
        "steps": [
            {
                "id": "project_init",
                "command": "project-init",
                "purpose": "create or confirm the project workspace",
            },
            {
                "id": "project_new_run",
                "command": "project-new-run",
                "purpose": "create a run folder with run_layout.json",
                "requires": ["project-init"],
            },
            {
                "id": "validate_run_layout",
                "command": "run-layout-validate",
                "purpose": "fail closed on invalid run artifact ownership",
                "requires": ["project-new-run"],
            },
        ],
    },
    "video_intent_planner": {
        "description": "Produce the Stage 0 video_intent.json route decision artifact before story, material, or BUILD work.",
        "steps": [
            {
                "id": "video_intent_plan",
                "command": "video-intent-plan",
                "purpose": "classify video type, input state, entry path, follow-up questions, and next handoff",
            },
        ],
    },
    "material_map_lifecycle": {
        "description": "Resolve requirements, actual material maps, delta, and build handoff.",
        "steps": [
            {
                "id": "validate_needs",
                "command": "validate-needs",
                "purpose": "validate canonical material_needs.json when present",
            },
            {
                "id": "material_map_lifecycle",
                "command": "material-map-lifecycle",
                "purpose": "compute the material-map lifecycle stage and build handoff",
                "requires": ["validate-needs:ok_or_absent"],
            },
            {
                "id": "material_wall_build",
                "command": "material-wall-build",
                "purpose": "build photo walls and video strip walls for coarse material screening",
                "requires": ["ingest-meta:ok"],
            },
            {
                "id": "material_db_slice_from_wall",
                "command": "material-db-slice-from-wall",
                "purpose": "create a bounded materials_db scoped to assets shown in a material wall request",
                "requires": ["material-wall-build:ok"],
            },
            {
                "id": "material_wall_review_apply",
                "command": "material-wall-review-apply",
                "purpose": "apply keep/maybe/reject/duplicate coarse wall decisions to materials_db",
                "requires": ["material-db-slice-from-wall:ok", "material-wall-build:reviewed"],
            },
            {
                "id": "material_map_review_apply",
                "command": "material-map-review-apply",
                "purpose": "apply bounded reviewer decisions as scene-level satisfies edges",
                "requires": ["material-map-lifecycle:await_map_review"],
            },
        ],
    },
    "source_understanding": {
        "description": "Analyze one long source video before highlight selection: section map, motion/edit-point profile, source material matrix, then rough highlight plan.",
        "steps": [
            {
                "id": "source_section_map",
                "command": "source-section-map",
                "purpose": "derive big sections from visual shot boundaries, audio energy changes, and target spacing",
            },
            {
                "id": "source_motion_profile",
                "command": "source-motion-profile",
                "purpose": "derive local edit-point and transition candidates from visual motion/change signals",
                "requires": ["source-section-map:ok"],
            },
            {
                "id": "source_material_matrix",
                "command": "source-material-matrix",
                "purpose": "write source_material_matrix.json, contact sheet, and source audio probe before semantic review",
                "requires": ["source-motion-profile:ok_or_scoped"],
            },
            {
                "id": "source_dialogue_script",
                "command": "source-dialogue-script",
                "purpose": "convert correct subtitle/ASR cues into source_transcript.json and sentence-safe dialogue_edit_script.json",
                "requires": ["source-material-matrix:ok", "subtitle_or_asr:available"],
            },
            {
                "id": "source_highlight_plan",
                "command": "source-highlight-plan",
                "purpose": "create highlight_selection_plan.json and rough_cut_plan.json from reviewed source evidence when the route is not dialogue-script driven",
                "requires": ["source-material-matrix:reviewed_or_explicitly_deferred"],
            },
        ],
    },
    "generated_material_provider_handoff": {
        "description": "Turn generated-material fallback jobs into real image-provider prompts, image-agent execution packets, and importable provider outputs.",
        "steps": [
            {
                "id": "generated_image_provider_packet",
                "command": "generated-image-provider-packet",
                "purpose": "write target filenames, prompts, and generated_provider_outputs template for real image providers",
                "requires": ["material-generation-fallback:ok"],
            },
            {
                "id": "image_agent_prompt_handoff",
                "command": "image-agent-prompt-handoff",
                "purpose": "write an image-agent executable prompt packet; fail closed if only placeholder/text-card output is possible",
                "requires": ["generated-image-provider-packet:ok"],
            },
            {
                "id": "codex_imagegen_provider_fill",
                "command": "codex-imagegen-provider-fill",
                "purpose": "copy already-generated image files into packet target paths and write generated_provider_outputs.json",
                "requires": ["image-agent-prompt-handoff:generated_files_ready"],
            },
            {
                "id": "generated_material_import",
                "command": "generated-material-import",
                "purpose": "import real generated images back into generated material production artifacts for review",
                "requires": ["generated_provider_outputs:ok"],
            },
        ],
    },
    "canonical_build": {
        "description": "Run canonical backend build and verification gates.",
        "steps": [
            {
                "id": "spec_review",
                "command": "spec-review",
                "purpose": "validate contract readiness before build",
            },
            {
                "id": "director_supply_revise",
                "command": "director-supply-revise",
                "purpose": "revise overlong segment durations from objective supply_review evidence",
                "requires": ["supply-review:script_overreach"],
            },
            {
                "id": "contract_run",
                "command": "contract-run",
                "purpose": "run canonical ffmpeg build with fresh material gates",
                "requires": ["spec-review:ok"],
            },
            {
                "id": "verify",
                "command": "verify",
                "purpose": "run delivery verification on the rendered output",
                "requires": ["contract-run:ok"],
            },
        ],
    },
    "voiceover_provider_handoff": {
        "description": "Plan or execute provider-backed narration before BUILD consumes subtitle/voiceover evidence.",
        "steps": [
            {
                "id": "voiceover_provider_plan",
                "command": "voiceover-provider-plan",
                "purpose": "write voiceover_provider_plan.json, narration_manifest.json, and subtitle_voiceover_build_handoff.json; optionally execute VoxCPM or explicit legacy fallback",
                "requires": ["segment_contract:has_narration_or_script_text"],
            },
        ],
    },
    "effects_contract": {
        "description": "Compile neutral effect intent before selecting an effects backend.",
        "steps": [
            {
                "id": "visual_technique_plan",
                "command": "visual-technique-plan",
                "purpose": "translate fuzzy effect language into reviewable candidate primitives, controls, and options before worker handoff",
            },
            {
                "id": "visual_technique_review_apply",
                "command": "visual-technique-review-apply",
                "purpose": "apply user/reviewer option and control overrides to produce a confirmed visual technique plan",
                "requires": ["visual-technique-plan:reviewed"],
            },
            {
                "id": "compile_effect_intent",
                "command": "effect-intent-plan",
                "purpose": "compile director-shot-plan effect_intent into neutral effect_intent_plan/effect_asset_spec artifacts",
                "requires": ["visual-technique-review-apply:confirmed_or_not_needed"],
            },
            {
                "id": "light_effects_plan",
                "command": "light-effects-plan",
                "purpose": "compile ffmpeg-safe light effects plan when the build profile enables effects",
                "requires": ["effect-intent-plan:ok"],
            },
            {
                "id": "effect_revision_request",
                "command": "effect-revision-request",
                "purpose": "convert light-effects render gaps into a Node14 revision request artifact",
                "requires": ["light-effects-plan:ok"],
            },
            {
                "id": "effect_revision_draft",
                "command": "effect-revision-draft",
                "purpose": "convert Node14 effect revision requests into draft patch artifacts",
                "requires": ["effect-revision-request:ok"],
            },
            {
                "id": "effect_revision_apply",
                "command": "effect-revision-apply",
                "purpose": "explicitly review/apply a revised effect intent draft into a separate effect_intent_plan for a second contract-run",
                "requires": ["effect-revision-draft:reviewed"],
            },
        ],
    },
    "brownfield_edit_route": {
        "description": "local patch / review route for existing builds: Workbench draft edits, effect gaps, effect assets, and sfx/overlay additions. story evidence material must go back through material-map review before it can affect BUILD.",
        "steps": [
            {
                "id": "validate_workbench_handoff",
                "command": "workbench-handoff-validate",
                "purpose": "validate draft patch references and canonical write boundaries when a Workbench patch is present",
            },
            {
                "id": "rerender_workbench_draft",
                "command": "workbench-draft-rerender",
                "purpose": "optionally render a non-canonical preview candidate from the validated draft",
                "requires": ["workbench-handoff-validate:ok_or_absent"],
            },
            {
                "id": "effect_revision_request",
                "command": "effect-revision-request",
                "purpose": "convert effect gaps from VERIFY/review into a Brownfield request without mutating canonical inputs",
                "requires": ["contract-run:baseline_review"],
            },
            {
                "id": "effect_revision_draft",
                "command": "effect-revision-draft",
                "purpose": "convert Brownfield effect requests into draft patch artifacts for review",
                "requires": ["effect-revision-request:ok"],
            },
            {
                "id": "effect_collage_refs",
                "command": "effect-collage-refs",
                "purpose": "convert reviewed material-map, material-wall keyframes, or Workbench still evidence into Remotion collage_media_refs",
                "requires": ["material-map-review:reviewed_or_material_wall_or_workbench_thumbnails"],
            },
            {
                "id": "remotion_prompt_pack",
                "command": "remotion-prompt-pack",
                "purpose": "prepare prompt-driven Remotion jobs for adapter-route effect gaps",
                "requires": ["effect-revision-request:adapter_route"],
            },
            {
                "id": "remotion_worker_outputs",
                "command": "remotion-worker-outputs",
                "purpose": "validate Remotion worker outputs before Workbench/Brownfield review",
                "requires": ["remotion-prompt-pack:ok"],
            },
            {
                "id": "effect_render_verification",
                "command": "effect-render-verification",
                "purpose": "convert accepted Remotion review evidence into delivery-gate effect_render_verification.json",
                "requires": ["remotion-worker-outputs:accepted_review"],
            },
            {
                "id": "remotion_composite_draft",
                "command": "remotion-composite-draft",
                "purpose": "composite accepted Remotion outputs into a non-canonical draft video",
                "requires": ["remotion-worker-outputs:accepted_review"],
            },
            {
                "id": "effect_revision_apply",
                "command": "effect-revision-apply",
                "purpose": "explicitly review/apply a draft into a separate reviewed artifact for a second contract-run",
                "requires": ["effect-revision-draft:reviewed"],
            },
        ],
    },
    "remotion_effect_adapter": {
        "description": "Prompt-driven Remotion effect backend inside Brownfield Edit; produces reviewable assets, not canonical final renders.",
        "steps": [
            {
                "id": "effect_revision_request",
                "command": "effect-revision-request",
                "purpose": "identify adapter-route effect gaps from the light-effects baseline review",
            },
            {
                "id": "effect_collage_refs",
                "command": "effect-collage-refs",
                "purpose": "prepare reviewed collage_media_refs for Remotion templates and effect_build_spec material refs",
                "requires": ["reviewed_material_stills_or_thumbnails"],
            },
            {
                "id": "remotion_prompt_pack",
                "command": "remotion-prompt-pack",
                "purpose": "convert adapter-route gaps plus neutral effect intent into Remotion worker prompt jobs",
                "requires": ["effect-revision-request:adapter_route"],
            },
            {
                "id": "remotion_worker_outputs",
                "command": "remotion-worker-outputs",
                "purpose": "validate worker-produced preview/rendered files and create remotion_effect_review.json",
                "requires": ["remotion-prompt-pack:ok"],
            },
            {
                "id": "effect_render_verification",
                "command": "effect-render-verification",
                "purpose": "write effect_render_verification.json for delivery gate after effect review is accepted",
                "requires": ["remotion-worker-outputs:accepted_review"],
            },
            {
                "id": "remotion_composite_draft",
                "command": "remotion-composite-draft",
                "purpose": "composite accepted Remotion outputs into a non-canonical draft for review",
                "requires": ["remotion-worker-outputs:accepted_review"],
            },
        ],
    },
    "workbench_review_rerender": {
        "description": "Consume Workbench draft edits and render a non-canonical preview candidate.",
        "steps": [
            {
                "id": "validate_workbench_handoff",
                "command": "workbench-handoff-validate",
                "purpose": "validate draft artifact references, hashes, and canonical write boundary",
            },
            {
                "id": "rerender_workbench_draft",
                "command": "workbench-draft-rerender",
                "purpose": "render a non-canonical candidate from the validated draft",
                "requires": ["workbench-handoff-validate:ok"],
            },
        ],
    },
    "operator_flow_acceptance": {
        "description": "Run a bounded black-box acceptance over a complete operator artifact root.",
        "steps": [
            {
                "id": "operator_flow_acceptance",
                "command": "operator-flow-acceptance",
                "purpose": "validate package completeness, material lifecycle, Workbench handoff, and non-canonical rerender",
            },
        ],
    },
    "route_orchestrator_packet": {
        "description": "Issue and accept runner-neutral subagent task packets with fail-closed artifact boundaries.",
        "steps": [
            {
                "id": "issue_task",
                "command": "route-task-next",
                "purpose": "write the next route_subagent_task packet and snapshot protected artifacts",
            },
            {
                "id": "accept_task",
                "command": "route-task-accept",
                "purpose": "validate subagent outputs, freshness, and must_not_touch snapshots before advancing",
                "requires": ["route-task-next:issued"],
            },
            {
                "id": "report_state",
                "command": "route-orchestrator-report",
                "purpose": "inspect current route state without mutating artifacts",
                "requires": ["route-task-accept:ok_or_blocked"],
            },
            {
                "id": "acceptance_replay",
                "command": "route-orchestrator-acceptance",
                "purpose": "prove the packet/state-machine route with deterministic fake-worker happy and fail-closed paths",
                "requires": ["route-task-next:implemented", "route-task-accept:implemented"],
            },
        ],
    },
    "video_intent_acceptance": {
        "description": "Prove VIP0 route decisions and follow-up behavior for Stage 0 video_intent.json.",
        "steps": [
            {
                "id": "video_intent_acceptance",
                "command": "video-intent-acceptance",
                "purpose": "run deterministic VIP0 route cases without starting type templates or BUILD",
                "requires": ["video-intent-plan:implemented"],
            },
        ],
    },
}


def build_command_manifest(commands: Iterable[str]) -> dict:
    names = sorted(str(c) for c in commands)
    command_entries = {}
    groups: Dict[str, list] = {}
    unclassified = []
    for name in names:
        group = COMMAND_GROUPS.get(name)
        if group is None:
            unclassified.append(name)
            group = "unclassified"
        command_entries[name] = {"group": group}
        groups.setdefault(group, []).append(name)

    return {
        "artifact_role": "video_tools_command_manifest",
        "version": 1,
        "command_count": len(names),
        "group_count": len(groups),
        "groups": {
            group: {
                "description": GROUP_DESCRIPTIONS.get(group, ""),
                "commands": groups[group],
            }
            for group in sorted(groups)
        },
        "commands": command_entries,
        "unclassified_commands": unclassified,
    }


def build_workflow_manifest(commands: Iterable[str]) -> dict:
    available = set(str(c) for c in commands)
    workflows = {}
    missing = []
    for name, workflow in WORKFLOWS.items():
        steps = []
        for step in workflow["steps"]:
            item = dict(step)
            item.setdefault("requires", [])
            if item["command"] not in available:
                missing.append({"workflow": name, "step": item["id"], "command": item["command"]})
            steps.append(item)
        workflows[name] = {
            "description": workflow["description"],
            "steps": steps,
        }
    return {
        "artifact_role": "video_tools_workflow_manifest",
        "version": 1,
        "workflow_count": len(workflows),
        "workflows": workflows,
        "missing_commands": missing,
    }


def unclassified_commands(dispatch: Mapping[str, object]) -> list:
    return sorted(name for name in dispatch if name not in COMMAND_GROUPS)
