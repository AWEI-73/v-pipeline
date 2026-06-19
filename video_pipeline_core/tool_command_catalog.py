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
    "state": "workspace",
    "commands-manifest": "workspace",
    "workflow-manifest": "workspace",
    "test-tiers": "verify",
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
    "contract-dry-build": "contract",
    "contract-run": "contract",
    "generated-manifest": "contract",
    "generated-material-import": "material",
    "generated-image-provider-packet": "material",
    "codex-imagegen-provider-fill": "material",
    "generated-material-produce": "material",
    "generated-material-review": "material",
    "light-effects-plan": "contract",
    "effect-intent-plan": "contract",
    "effect-revision-request": "contract",
    "effect-revision-draft": "contract",
    "effect-revision-apply": "contract",
    "blueprint-coverage": "contract",
    "blueprint-compile": "contract",
    "blueprint-to-contract": "contract",
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
    "project-material-map": "material",
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

    # Replay / acceptance proof commands.
    "replay-acceptance": "acceptance",
    "operator-flow-acceptance": "acceptance",
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
    "effects_contract": {
        "description": "Compile neutral effect intent before selecting an effects backend.",
        "steps": [
            {
                "id": "compile_effect_intent",
                "command": "effect-intent-plan",
                "purpose": "compile director-shot-plan effect_intent into neutral effect_intent_plan/effect_asset_spec artifacts",
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
                "id": "effect_revision_apply",
                "command": "effect-revision-apply",
                "purpose": "explicitly review/apply a draft into a separate reviewed artifact for a second contract-run",
                "requires": ["effect-revision-draft:reviewed"],
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
