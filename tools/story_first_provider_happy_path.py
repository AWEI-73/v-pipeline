"""Run story-first no-material happy path to a real image-provider packet."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from video_pipeline_core import material_delta, material_generation_fallback, story_soul_blueprint  # noqa: E402
from video_pipeline_core.generated_image_provider_packet import build_generated_image_provider_packet  # noqa: E402
from video_pipeline_core.material_rough_cut import write_json  # noqa: E402


def _brief(title: str, style: str, target_duration: float) -> dict[str, Any]:
    return {
        "project_type": "generated_comic_story",
        "audience": "children and family viewers",
        "duration_sec": float(target_duration),
        "goal": f"Tell a short story: {title}",
        "facts": {
            "protagonist": title,
            "place": "moonlit forest",
        },
        "known_material_categories": [],
        "desired_style": style,
        "seed_device": "gentle moonlight guiding the way home",
        "story_seed": {
            "protagonists": [title],
            "setting": "moonlit forest",
            "moral": "kindness helps people find the way home",
        },
        "required_inclusions": ["safe ending", "warm emotion", "clear picture-book continuity"],
    }


def run_story_first_provider_happy_path(
    run_dir,
    *,
    title: str,
    style: str,
    target_duration_sec: float = 60.0,
    providers: str = "codex_imagegen,gemini,antigravity",
) -> dict:
    root = Path(run_dir).resolve()
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)

    brief = _brief(title, style, target_duration_sec)
    write_json(root / "project_brief.json", brief)
    write_json(root / "video_intent.json", {
        "artifact_role": "video_intent",
        "version": 1,
        "input_state": "no_material",
        "entry_path": "structure-first",
        "route": "structure-first",
        "video_type": "storybook",
        "audience": brief["audience"],
        "goal": brief["goal"],
        "target_length": f"{int(target_duration_sec)} seconds",
        "generation_allowed": True,
        "handoff_to": "story_soul_blueprint_then_generated_image_provider",
        "required_followup_questions": [],
    })

    blueprint = story_soul_blueprint.write_story_soul_blueprint(brief, root / "story_blueprint")
    if not blueprint.get("ok"):
        raise RuntimeError("; ".join(blueprint.get("errors") or ["story blueprint failed"]))
    needs = blueprint["material_needs"]
    initial_delta = material_delta.compute_material_delta(needs, [])
    write_json(root / "material_delta.json", initial_delta)
    fallback = material_generation_fallback.plan_material_generation_fallback(
        initial_delta,
        material_needs=needs,
        creative_concept=blueprint["creative_concept"],
        director_shot_plan=blueprint["director_shot_plan"],
    )
    write_json(root / "material_generation_fallback.json", fallback)
    style_profile = {
        "look": style,
        "style_anchors": [style, "picture book continuity", "warm safe mood"],
        "character_anchors": [title],
        "palette": ["soft moonlight", "warm amber", "gentle forest green"],
        "aspect_ratio": "16:9",
    }
    write_json(root / "style_profile.json", style_profile)
    packet_result = build_generated_image_provider_packet(
        fallback,
        root / "provider_packet",
        style_profile=style_profile,
        providers=providers,
    )
    if not packet_result.get("ok"):
        raise RuntimeError("; ".join(packet_result.get("errors") or ["provider packet failed"]))

    report = {
        "artifact_role": "story_first_provider_happy_path_report",
        "version": 1,
        "ok": True,
        "run_dir": str(root),
        "video_intent": str(root / "video_intent.json"),
        "story_blueprint": str(root / "story_blueprint"),
        "material_generation_fallback": str(root / "material_generation_fallback.json"),
        "provider_packet": packet_result["refs"]["provider_packet"],
        "provider_prompts": packet_result["refs"]["provider_prompts"],
        "provider_outputs_template": packet_result["refs"]["provider_outputs_template"],
        "image_count": packet_result["summary"]["image_count"],
        "next_action": "wait_for_generated_provider",
        "rendered": (root / "final.mp4").exists(),
        "limitations": [
            "This wrapper does not use test_pil or placeholder text-card generation.",
            "Generated images must be produced by a real provider and imported through generated-material-import.",
            "Generated candidates still require review before material truth/build promotion.",
        ],
    }
    write_json(root / "story_first_provider_happy_path_report.json", report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="run folder to create")
    parser.add_argument("--title", required=True, help="story title or subject")
    parser.add_argument("--style", required=True, help="visual style")
    parser.add_argument("--target-duration", type=float, default=60.0)
    parser.add_argument("--providers", default="codex_imagegen,gemini,antigravity")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = run_story_first_provider_happy_path(
        args.out,
        title=args.title,
        style=args.style,
        target_duration_sec=args.target_duration,
        providers=args.providers,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']} images={result['image_count']} next={result['next_action']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
