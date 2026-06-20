#!/usr/bin/env python
"""Static acceptance check for the canonical Hermes route.

This harness verifies that the route spec, operator skill, roadmap, docs index,
and CLI surface still agree on the stable pipeline route. It does not run a
video render; E2E renders remain covered by the dedicated acceptance harnesses.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ARTIFACT_ROLE = "canonical_route_acceptance"
VERSION = 1

REQUIRED_STAGES = [
    "Intake",
    "Story Soul",
    "Director Shot Plan",
    "Material Truth",
    "Coverage / Decision Gate",
    "BUILD Planning",
    "Official Render",
    "Verify",
    "Workbench Draft Review",
    "Brownfield Edit / Finishing",
    "Delivery",
]

REQUIRED_SKILLS = [
    "video-pipeline-route.md",
    "story-soul-blueprint.md",
    "material-map.md",
    "material-generation-fallback.md",
    "generated-material-producer.md",
    "brownfield-edit.md",
    "verify.md",
]

REQUIRED_TOOLS = [
    "story-soul-blueprint",
    "validate-needs",
    "project-material-map",
    "material-map-lifecycle",
    "material-generation-fallback",
    "generated-image-provider-packet",
    "generated-material-import",
    "generated-material-review",
    "material-delta",
    "material-revision",
    "contract-run",
    "verify",
    "workbench-handoff-validate",
    "effect-revision-request",
    "remotion-prompt-pack",
    "reviewer-policy",
    "reviewer-flow-acceptance",
]

REQUIRED_ARTIFACTS = [
    "segment_contract.json",
    "material_needs.json",
    "project_material_map.json",
    "material_generation_fallback.json",
    "generated_provider_packet.json",
    "generated_material_review.json",
    "material_delta.json",
    "revision_decisions.json",
    "revised_segment_contract.json",
    "generated_mv_script.json",
    "timeline_build.json",
    "final.mp4",
    "subtitles.srt",
    "verify_result.json",
    "preview_timeline.json",
    "timeline_patch.json",
    "patched_draft_timeline.json",
    "workbench_contract_patch.json",
    "effect_intent_plan.json",
    "remotion_prompt_pack.json",
    "remotion_effect_review.json",
    "reviewer_policy_packet.json",
]


def _read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


def _contains(text: str, needle: str) -> bool:
    return needle in text


def run_check(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    route_path = root / "docs" / "canonical-video-pipeline-route.md"
    start_here_path = root / "docs" / "START_HERE_VIDEO_PIPELINE.md"
    upstream_path = root / "docs" / "upstream-story-route.md"
    operating_map_path = root / "docs" / "video-pipeline-operating-map.md"
    reviewer_map_path = root / "docs" / "artifact-reviewer-map.md"
    skill_path = root / "skills" / "video-pipeline-route.md"
    roadmap_path = root / "roadmap.md"
    index_path = root / "docs" / "INDEX.md"
    video_tools_path = root / "video_tools.py"

    for path in [
        start_here_path,
        route_path,
        upstream_path,
        operating_map_path,
        reviewer_map_path,
        skill_path,
        roadmap_path,
        index_path,
        video_tools_path,
    ]:
        if not path.is_file():
            errors.append(f"missing required file: {path.relative_to(root)}")

    if errors:
        return _result(errors, warnings)

    route = route_path.read_text(encoding="utf-8")
    start_here = start_here_path.read_text(encoding="utf-8")
    upstream = upstream_path.read_text(encoding="utf-8")
    operating_map = operating_map_path.read_text(encoding="utf-8")
    reviewer_map = reviewer_map_path.read_text(encoding="utf-8")
    skill = skill_path.read_text(encoding="utf-8")
    roadmap = roadmap_path.read_text(encoding="utf-8")
    index = index_path.read_text(encoding="utf-8")
    video_tools = video_tools_path.read_text(encoding="utf-8")

    last_pos = -1
    for stage in REQUIRED_STAGES:
        pos = route.find(f"| {stage} |")
        if pos < 0:
            errors.append(f"route spec missing stage: {stage}")
        elif pos <= last_pos:
            errors.append(f"route stage out of order: {stage}")
        last_pos = max(last_pos, pos)
        if stage not in skill:
            errors.append(f"operator skill missing stage: {stage}")

    for skill_name in REQUIRED_SKILLS:
        if not (root / "skills" / skill_name).is_file():
            errors.append(f"missing skill file: skills/{skill_name}")
        if skill_name not in route and skill_name != "video-pipeline-route.md":
            errors.append(f"route spec does not reference skill: {skill_name}")

    for tool in REQUIRED_TOOLS:
        if f'"{tool}"' not in video_tools and f"sub.add_parser(\"{tool}\")" not in video_tools:
            errors.append(f"video_tools.py missing parser for tool: {tool}")
        if tool not in route and tool not in skill:
            errors.append(f"route docs do not reference tool: {tool}")

    for artifact in REQUIRED_ARTIFACTS:
        if artifact not in route:
            errors.append(f"route spec missing artifact: {artifact}")

    for doc_text, label in [(roadmap, "roadmap.md"), (index, "docs/INDEX.md")]:
        if "docs/canonical-video-pipeline-route.md" not in doc_text:
            errors.append(f"{label} does not link canonical route doc")
        if "docs/START_HERE_VIDEO_PIPELINE.md" not in doc_text:
            errors.append(f"{label} does not link start-here doc")
        if "docs/upstream-story-route.md" not in doc_text:
            errors.append(f"{label} does not link upstream story route")
        if "docs/video-pipeline-operating-map.md" not in doc_text:
            errors.append(f"{label} does not link operating map")
        if "docs/artifact-reviewer-map.md" not in doc_text:
            errors.append(f"{label} does not link reviewer map")

    for expected in [
        "docs/video-pipeline-operating-map.md",
        "docs/canonical-video-pipeline-route.md",
        "docs/upstream-story-route.md",
        "docs/artifact-reviewer-map.md",
        "review_policy",
    ]:
        if expected not in start_here:
            errors.append(f"start-here doc missing reference: {expected}")

    for expected in [
        "docs/upstream-story-route.md",
        "docs/artifact-reviewer-map.md",
        "Reviewer Policy",
        "Technical `VERIFY` remains deterministic",
    ]:
        if expected not in operating_map:
            errors.append(f"operating map missing reviewer policy reference: {expected}")

    for expected in [
        "Role / Literary Lens",
        "Blueprint Interview",
        "Story Soul Package",
        "Director Shot Plan",
        "Contract Compile",
        "Material-Ready Handoff",
        "blueprint.md",
        "blueprint.json",
        "story_soul_blueprint.json",
        "segment_contract.json",
        "material_needs.json",
        "generation_manifest.json",
        "generated material review rubric",
        "initial missing material_delta",
    ]:
        if expected not in upstream:
            errors.append(f"upstream story route missing term: {expected}")

    for expected in [
        "light",
        "normal",
        "deep",
        "literary_editor",
        "technical_verify",
    ]:
        if expected not in reviewer_map:
            errors.append(f"reviewer map missing policy term: {expected}")

    for alias in ["M6", "SRP", "FX", "Node14", "Brownfield Edit"]:
        if alias not in route:
            warnings.append(f"legacy alias not mentioned in route spec: {alias}")

    return _result(errors, warnings)


def _result(errors: list[str], warnings: list[str]) -> dict[str, Any]:
    return {
        "artifact_role": ARTIFACT_ROLE,
        "version": VERSION,
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "stage_count": len(REQUIRED_STAGES),
            "skill_count": len(REQUIRED_SKILLS),
            "tool_count": len(REQUIRED_TOOLS),
            "artifact_count": len(REQUIRED_ARTIFACTS),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--out", help="optional JSON report path")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    result = run_check(root)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    print(text)
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
