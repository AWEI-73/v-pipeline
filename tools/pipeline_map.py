#!/usr/bin/env python
"""Generate the Hermes pipeline map and Graphify MVP corpus.

This is an operator aid, not a runtime gate. It keeps the architecture map,
active documentation set, and Graphify corpus in sync so agents do not have to
guess which files represent the current MVP route.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "docs" / "generated"
DEFAULT_CORPUS_DIR = ROOT / ".graphify-corpus" / "mvp"


ACTIVE_DOCS = [
    "README.md",
    "roadmap.md",
    "RUNBOOK.md",
    "docs/START_HERE_VIDEO_PIPELINE.md",
    "docs/canonical-video-pipeline-route.md",
    "docs/video-pipeline-operating-map.md",
    "docs/video-pipeline-end-to-end-line.md",
    "docs/repository-consolidation-map.md",
    "docs/material-map-lifecycle.md",
    "docs/effect-factory-route.md",
    "docs/soundtrack-arranger-route.md",
    "docs/stage-boundary-matrix.md",
    "docs/construction-guides/stage0-10-route-alignment-plan.md",
    "docs/upstream-story-route.md",
    "docs/artifact-reviewer-map.md",
    "docs/route-orchestrator-harness.md",
    "docs/route-agent-runner-protocol.md",
    "docs/workbench-dashboard-integration.md",
    "dashboard/workbench_native/API_CONTRACT.md",
    "docs/remotion_prompt_parameter_contract.md",
    "docs/INDEX.md",
]

ACTIVE_SKILLS = [
    "skills/video-pipeline-route.md",
    "skills/video-intent-planner.md",
    "skills/story-soul-blueprint.md",
    "skills/director.md",
    "skills/effects-director.md",
    "skills/curator.md",
    "skills/material-map.md",
    "skills/shooting-brief.md",
    "skills/material-generation-fallback.md",
    "skills/generated-material-producer.md",
    "skills/gap-analyzer.md",
    "skills/video-effect-factory.md",
    "skills/remotion-effect-worker.md",
    "skills/editor.md",
    "skills/audio-director.md",
    "skills/soundtrack-arranger.md",
    "skills/subtitle-director.md",
    "skills/brownfield-edit.md",
    "skills/verify.md",
    "skills/dashboard.md",
]

CORE_TOOLS = [
    "video_tools.py",
    "runtime.py",
    "tools/pipeline_home.py",
    "tools/canonical_route_acceptance.py",
    "tools/material_first_boundary_acceptance.py",
    "tools/material_gap_brief.py",
    "tools/visual_technique_plan.py",
    "tools/effect_factory_boundary_acceptance.py",
    "tools/remotion_material_first_memory_acceptance.py",
    "tools/soundtrack_flow_acceptance.py",
    "tools/audio_mix_plan_execute.py",
    "tools/subtitle_voiceover_handoff_accept.py",
    "tools/validate_pipeline_run_folder.py",
    "tools/dashboard_server.py",
    "tools/workbench_server.py",
    "tools/pipeline_map.py",
    "tools/orphan_audit.py",
]

SUPPORT_TOOLS = {
    "acceptance": [
        "tools/material_first_stage2_3_smoke.py",
        "tools/operator_flow_acceptance.py",
        "tools/remotion_transition_acceptance.py",
        "tools/route_orchestrator_acceptance.py",
        "tools/stage4_build_smoke.py",
        "tools/stage5_final_review_smoke.py",
        "tools/video_intent_acceptance.py",
        "tools/test_tiers.py",
    ],
    "workbench": [
        "tools/audio_cue_patch.py",
        "tools/effect_patch.py",
        "tools/subtitle_patch.py",
        "tools/workbench_draft_rerender.py",
        "tools/workbench_frontend_smoke.py",
        "tools/workbench_handoff.py",
        "tools/workbench_review_report.py",
        "tools/workbench_browser_layout_smoke.mjs",
        "tools/workbench_thumbs.py",
    ],
}


STAGES = [
    {
        "id": "stage0",
        "name": "Video Intent Planner",
        "skills": ["skills/video-intent-planner.md", "skills/video-pipeline-route.md"],
        "docs": ["docs/START_HERE_VIDEO_PIPELINE.md"],
        "tools": ["video_tools.py:video-intent-plan", "tools/pipeline_home.py"],
        "artifacts": ["project_brief.json", "video_intent.json"],
        "gate": "Ask focused questions when route-changing inputs are missing.",
        "returns_to": ["user_brief"],
    },
    {
        "id": "stage1",
        "name": "Story / Structure",
        "skills": ["skills/story-soul-blueprint.md", "skills/director.md"],
        "docs": ["docs/upstream-story-route.md"],
        "tools": ["video_tools.py:story-soul-blueprint", "video_tools.py:story-soul-to-contract", "video_tools.py:blueprint-to-contract"],
        "artifacts": ["story_soul_blueprint.json", "director_shot_plan.json", "material_needs.json", "segment_contract.json"],
        "gate": "Stop if the structure lacks narrative device, beat purpose, or material-ready handoff.",
        "returns_to": ["stage0"],
    },
    {
        "id": "stage2",
        "name": "Director Shot Plan",
        "skills": ["skills/director.md", "skills/effects-director.md", "skills/video-effect-factory.md"],
        "docs": ["docs/effect-factory-route.md"],
        "tools": ["video_tools.py:validate-needs", "video_tools.py:effect-intent-plan"],
        "artifacts": ["segment_contract.json", "material_needs.json", "effect_intent_plan.json"],
        "gate": "Stop if must-have material or required effects are vague or untestable.",
        "returns_to": ["stage1"],
    },
    {
        "id": "stage3",
        "name": "Material Truth",
        "branch": "material-map",
        "skills": ["skills/material-map.md", "skills/curator.md", "skills/material-generation-fallback.md", "skills/generated-material-producer.md"],
        "docs": ["docs/material-map-lifecycle.md"],
        "tools": [
            "video_tools.py:project-material-map",
            "video_tools.py:material-map-lifecycle",
            "tools/material_gap_brief.py",
            "video_tools.py:generated-material-review",
        ],
        "artifacts": [
            "project_material_map.json",
            "material_wall_review_verdict.json",
            "visual_diversity_review.json",
            "material_gap_brief.json",
            "shooting_brief.md",
            "generated_material_review.json",
        ],
        "gate": "Generated assets and reviewed material must enter material map before they satisfy needs.",
        "returns_to": ["stage2"],
    },
    {
        "id": "stage4",
        "name": "Coverage / Decision Gate",
        "skills": ["skills/gap-analyzer.md", "skills/material-map.md", "skills/shooting-brief.md"],
        "docs": ["docs/material-map-lifecycle.md"],
        "tools": ["video_tools.py:material-delta", "video_tools.py:material-revision"],
        "artifacts": ["material_delta.json", "material_gap_brief.json", "material_map_lifecycle.json", "revision_decisions.json"],
        "gate": "BUILD only when delta is ready or accepted revision/waiver re-gates cleanly.",
        "returns_to": ["stage3", "stage2"],
    },
    {
        "id": "stage5",
        "name": "BUILD Planning",
        "skills": ["skills/editor.md", "skills/audio-director.md", "skills/subtitle-director.md", "skills/video-effect-factory.md"],
        "docs": ["docs/build-capability-alignment.md"],
        "tools": ["video_tools.py:contract-dry-build", "video_tools.py:contract-adapt"],
        "artifacts": [
            "build_profile.json",
            "assembly_plan.json",
            "rough_cut_plan.json",
            "timeline_build.json",
            "audio_build_handoff.json",
            "effect_handoff.json",
            "remotion_effect_handoff.json",
            "subtitles.srt",
        ],
        "gate": "Stop on GAP clips, invalid source windows, contract/runtime mismatch, or missing accepted branch handoff.",
        "returns_to": ["stage4", "stage3", "soundtrack-arranger", "effect-factory", "subtitle-voiceover"],
    },
    {
        "id": "stage6",
        "name": "Official Render",
        "skills": ["skills/editor.md"],
        "docs": ["RUNBOOK.md"],
        "tools": ["video_tools.py:contract-run"],
        "artifacts": ["final.mp4", "subtitles.srt", "artifact_manifest.json"],
        "gate": "final.mp4 is only current when written by the active run after gates pass.",
        "returns_to": ["stage5"],
    },
    {
        "id": "stage7",
        "name": "Verify / Review",
        "skills": ["skills/verify.md"],
        "docs": ["docs/artifact-reviewer-map.md"],
        "tools": ["video_tools.py:verify", "video_tools.py:keyframe-grid", "video_tools.py:visual-audit"],
        "artifacts": ["verify_result.json", "keyframe_grid.jpg", "visual_audit.json", "caption_audit.json"],
        "gate": "Failures route back by owner: material, effects, subtitle/audio, or build.",
        "returns_to": ["stage3", "effect-factory", "workbench"],
    },
    {
        "id": "stage8",
        "name": "Workbench Draft Review",
        "skills": ["skills/brownfield-edit.md", "skills/dashboard.md"],
        "docs": ["docs/workbench-dashboard-integration.md"],
        "tools": [
            "tools/test_tiers.py --tier workbench",
            "tools/workbench_server.py",
            "tools/workbench_frontend_smoke.py",
            "tools/workbench_browser_layout_smoke.mjs",
            "video_tools.py:workbench-handoff-validate",
        ],
        "artifacts": ["preview_timeline.json", "timeline_patch.json", "workbench_contract_patch.json"],
        "gate": "Draft artifacts must not overwrite canonical truth.",
        "returns_to": ["stage5", "stage7"],
    },
    {
        "id": "stage9",
        "name": "Brownfield / Finishing",
        "skills": ["skills/brownfield-edit.md", "skills/video-effect-factory.md", "skills/remotion-effect-worker.md", "skills/audio-director.md", "skills/subtitle-director.md"],
        "docs": ["docs/workbench-dashboard-integration.md", "docs/effect-factory-route.md", "docs/soundtrack-arranger-route.md"],
        "tools": [
            "tools/subtitle_patch.py",
            "tools/audio_cue_patch.py",
            "tools/effect_patch.py",
            "video_tools.py:workbench-handoff-validate",
            "video_tools.py:workbench-draft-rerender",
        ],
        "artifacts": ["subtitle_patch.json", "audio_cue_patch.json", "effect_patch.json", "workbench_handoff.json"],
        "gate": "Finishing-only fixes return to owning branch or BUILD; material-truth changes return to Material Map.",
        "returns_to": ["stage3", "stage5", "stage7", "effect-factory", "soundtrack-arranger", "subtitle-voiceover"],
    },
    {
        "id": "stage10",
        "name": "Delivery",
        "skills": ["skills/verify.md", "skills/video-pipeline-route.md"],
        "docs": ["RUNBOOK.md"],
        "tools": ["tools/validate_pipeline_run_folder.py --complete-video"],
        "artifacts": [
            "final.mp4",
            "delivery_requirements.json",
            "verify_result.json",
            "audio_mix_report.json",
            "subtitles.srt",
            "effect_render_verification.json",
            "review_report.md",
            "run_layout.json",
        ],
        "gate": "Delivery must pass technical verify plus material/audio/subtitle/effect semantic evidence; warnings are blocked.",
        "returns_to": ["stage7", "stage8", "stage9"],
    },
]


BRANCHES = [
    {
        "id": "material-map",
        "name": "Material Map Branch",
        "purpose": "Material truth, satisfies edges, coverage, generated candidate review.",
        "docs": ["docs/material-map-lifecycle.md"],
        "skills": ["skills/material-map.md", "skills/curator.md", "skills/material-generation-fallback.md", "skills/generated-material-producer.md"],
        "artifacts": ["project_material_map.json", "material_delta.json", "generated_material_review.json"],
    },
    {
        "id": "effect-factory",
        "name": "Effect Factory Branch",
        "purpose": "Designed effect contracts, worker build, effect review, bounded handoff.",
        "docs": ["docs/effect-factory-route.md", "docs/remotion_prompt_parameter_contract.md"],
        "skills": ["skills/video-effect-factory.md", "skills/remotion-effect-worker.md"],
        "tools": [
            "tools/visual_technique_plan.py",
            "tools/effect_factory_boundary_acceptance.py",
            "tools/remotion_material_first_memory_acceptance.py",
        ],
        "artifacts": [
            "visual_technique_plan.json",
            "visual_technique_review.json",
            "visual_technique_plan.confirmed.json",
            "effect_design_map.json",
            "effect_contract.json",
            "effect_factory_boundary_acceptance_report.json",
            "effect_review.json",
            "effect_handoff.json",
            "remotion_effect_handoff.json",
            "effect_render_verification.json",
        ],
    },
    {
        "id": "soundtrack-arranger",
        "name": "Soundtrack Arranger Branch",
        "purpose": "Music/song/BGM section planning, provider/source/license review, and Audio Director handoff.",
        "docs": ["docs/soundtrack-arranger-route.md", "RUNBOOK.md"],
        "skills": ["skills/soundtrack-arranger.md", "skills/audio-director.md"],
        "tools": [
            "video_tools.py:soundtrack-arrange",
            "video_tools.py:soundtrack-provider-search",
            "video_tools.py:soundtrack-provider-download",
            "video_tools.py:soundtrack-import-url",
            "video_tools.py:soundtrack-audio-handoff-accept",
            "tools/soundtrack_flow_acceptance.py",
            "tools/audio_mix_plan_execute.py",
        ],
        "artifacts": [
            "soundtrack_plan.json",
            "music_source_candidates.json",
            "sound_license_manifest.json",
            "audio_director_handoff.json",
            "audio_handoff_acceptance.json",
            "audio_mix_plan.json",
            "final_audio.wav",
            "audio_mix_report.json",
            "audio_build_handoff.json",
        ],
    },
    {
        "id": "subtitle-voiceover",
        "name": "Subtitle / Voiceover Branch",
        "purpose": "Whole-video language, subtitle readability, narration/voiceover manifests, and repair handoff.",
        "docs": ["RUNBOOK.md", "docs/stage-boundary-matrix.md"],
        "skills": ["skills/audio-director.md", "skills/subtitle-director.md"],
        "tools": [
            "video_tools.py:subtitle",
            "video_tools.py:srt",
            "video_tools.py:caption-audit",
            "tools/subtitle_voiceover_handoff_accept.py",
            "tools/subtitle_patch.py",
        ],
        "artifacts": [
            "subtitle_voiceover_contract",
            "narration_manifest.json",
            "subtitles.srt",
            "caption_audit.json",
            "subtitle_voiceover_handoff_acceptance.json",
            "subtitle_voiceover_build_handoff.json",
            "subtitle_patch.json",
        ],
    },
    {
        "id": "orchestration",
        "name": "Multi-Agent Orchestration Branch",
        "purpose": "Bounded route task packets and runner-neutral handoffs.",
        "docs": ["docs/route-orchestrator-harness.md", "docs/route-agent-runner-protocol.md"],
        "skills": ["skills/video-pipeline-route.md"],
        "artifacts": ["route_subagent_task.json", "route_subagent_result.json", "route_orchestrator_state.json"],
    },
]


RUN_FOLDERS = {
    "run_root": [
        "video_intent.json",
        "segment_contract.json",
        "material_needs.json",
        "project_material_map.json",
        "material_delta.json",
        "timeline_build.json",
        "final.mp4",
        "verify_result.json",
        "run_layout.json",
    ],
    "brief": ["project_brief.json", "project_brief.md"],
    "materials": ["raw/", "selected/", "generated/", "stock/"],
    "maps": ["*.map.json"],
    "build": ["build_profile.json", "assembly_plan.json", "generated_mv_script.json"],
    "verify": ["keyframe_grid.jpg", "visual_audit.json", "caption_audit.json"],
    "workbench": ["preview_timeline.json", "timeline_patch.json", "workbench_contract_patch.json"],
    "effects": [
        "visual_technique_plan.json",
        "visual_technique_review.json",
        "visual_technique_plan.confirmed.json",
        "effect_design_map.json",
        "effect_contract.json",
        "effect_factory_boundary_acceptance_report.json",
        "remotion_prompt_pack.json",
        "remotion_effect_review.json",
    ],
}


def _rel(path: Path) -> str:
    return path.as_posix()


def build_map() -> dict[str, Any]:
    return {
        "artifact_role": "pipeline_architecture_map",
        "version": 1,
        "status": "mvp_current",
        "root": str(ROOT),
        "main_route": "Video Pipeline Route",
        "active_docs": ACTIVE_DOCS,
        "active_skills": ACTIVE_SKILLS,
        "core_tools": CORE_TOOLS,
        "support_tools": SUPPORT_TOOLS,
        "stages": STAGES,
        "branches": BRANCHES,
        "run_folder_structure": RUN_FOLDERS,
        "graphify_profile": {
            "name": "mvp",
            "corpus_dir": str(DEFAULT_CORPUS_DIR.relative_to(ROOT)),
            "include": ACTIVE_DOCS + ACTIVE_SKILLS + CORE_TOOLS + [
                tool
                for tools in SUPPORT_TOOLS.values()
                for tool in tools
            ],
            "exclude": ["runs/", ".tmp/", "reference repo/", "docs/archive/", "docs/construction-guides/", "dashboard/"],
        },
    }


def write_json(data: dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "pipeline_map.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_markdown(data: dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Hermes Pipeline Map",
        "",
        "Generated by `tools/pipeline_map.py`.",
        "",
        "## Main Shape",
        "",
        "```text",
        "Main route: Video Pipeline Route",
        "  -> Material Map Branch",
        "  -> Effect Factory Branch",
        "  -> Audio / Subtitle Branch",
        "  -> Multi-Agent Orchestration Branch",
        "```",
        "",
        "## Stages",
        "",
        "| Stage | Skills | Tools | Artifacts | Gate |",
        "|---|---|---|---|---|",
    ]
    for stage in data["stages"]:
        skills = "<br>".join(stage.get("skills", []))
        tools = "<br>".join(stage.get("tools", []))
        artifacts = "<br>".join(stage.get("artifacts", []))
        lines.append(f"| {stage['name']} | {skills} | {tools} | {artifacts} | {stage['gate']} |")
    lines.extend(["", "## Side Branches", ""])
    for branch in data["branches"]:
        lines.extend([
            f"### {branch['name']}",
            "",
            branch["purpose"],
            "",
            f"- Docs: {', '.join(branch['docs'])}",
            f"- Skills: {', '.join(branch['skills'])}",
            f"- Artifacts: {', '.join(branch['artifacts'])}",
            "",
        ])
    lines.extend(["## Run Folder Structure", ""])
    for folder, artifacts in data["run_folder_structure"].items():
        lines.append(f"- `{folder}`: {', '.join(artifacts)}")
    lines.extend(["", "## Support Tools", ""])
    for family, tools in data["support_tools"].items():
        lines.append(f"### {family}")
        lines.append("")
        for tool in tools:
            lines.append(f"- `{tool}`")
        lines.append("")
    lines.extend(["", "## Graphify MVP Corpus", ""])
    for item in data["graphify_profile"]["include"]:
        lines.append(f"- `{item}`")
    path = out_dir / "pipeline_map.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_mermaid(data: dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "flowchart TD",
        '  intent["Video Intent Planner"] --> story["Story / Structure"]',
        '  story --> director["Director Shot Plan"]',
        '  director --> material["Material Map Branch"]',
        '  material --> coverage["Coverage / Decision Gate"]',
        '  coverage --> build["BUILD Planning"]',
        '  build --> fxq{"Designed effects needed?"}',
        '  fxq -->|yes| effects["Effect Factory Branch"]',
        '  effects --> build',
        '  fxq -->|no| render["Official Render"]',
        '  build --> render',
        '  render --> verify["Verify / Review"]',
        '  verify --> workbench["Workbench / Brownfield"]',
        '  workbench --> build',
        '  verify --> delivery["Delivery"]',
        '  material --> generated["Generated Material Fallback"]',
        '  generated --> material',
        '  effects --> worker["Remotion Effect Worker"]',
        '  worker --> effects',
        '  verify --> material',
        '  verify --> effects',
    ]
    path = out_dir / "pipeline_map.mmd"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_corpus(data: dict[str, Any], corpus_dir: Path) -> Path:
    if corpus_dir.exists():
        shutil.rmtree(corpus_dir)
    corpus_dir.mkdir(parents=True, exist_ok=True)
    for rel in data["graphify_profile"]["include"]:
        src = ROOT / rel
        if not src.is_file():
            continue
        dst = corpus_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    return corpus_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--corpus-dir", default=str(DEFAULT_CORPUS_DIR))
    parser.add_argument("--build-corpus", action="store_true")
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args(argv)

    data = build_map()
    out_dir = Path(args.out_dir)
    outputs = [write_json(data, out_dir)]
    if not args.json_only:
        outputs.append(write_markdown(data, out_dir))
        outputs.append(write_mermaid(data, out_dir))
    if args.build_corpus:
        outputs.append(build_corpus(data, Path(args.corpus_dir)))

    for output in outputs:
        print(_rel(output.relative_to(ROOT) if output.is_relative_to(ROOT) else output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
