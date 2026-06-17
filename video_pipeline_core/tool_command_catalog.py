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
    "light-effects-plan": "contract",
    "blueprint-coverage": "contract",
    "blueprint-compile": "contract",
    "blueprint-to-contract": "contract",
    "creator-profile": "contract",

    # Material-map lifecycle and material selection.
    "ingest-meta": "material",
    "caption-meta": "material",
    "material-map": "material",
    "match-mv": "material",
    "rank-local": "material",
    "validate-needs": "material",
    "lineage-link": "material",
    "material-delta": "material",
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


def unclassified_commands(dispatch: Mapping[str, object]) -> list:
    return sorted(name for name in dispatch if name not in COMMAND_GROUPS)
