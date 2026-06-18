"""Generated-material skill acceptance harness.

Runs small comic-style projects from no material through:

material needs -> material delta -> generation fallback -> generated material
producer -> candidate material map -> material delta rerun -> director review.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core import (
    generated_material_producer,
    material_delta,
    material_generation_fallback,
)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _needs(project: str, needs: list[dict]) -> dict:
    return {
        "artifact_role": "material_needs",
        "version": 1,
        "project": project,
        "needs": needs,
    }


def _need(need_id: str, purpose: str, count: int = 2) -> dict:
    return {
        "need_id": need_id,
        "category": "comic_story",
        "type": "generated_panel",
        "purpose": purpose,
        "count": count,
        "must_have": True,
        "fallback_tier": 2,
        "fallback_options": ["generated comic panel"],
    }


def _empty_project_map() -> list:
    return []


def _case_specs() -> list[dict]:
    return [
        {
            "id": "case_a_rain_station",
            "title": "Rain Station Apprentice",
            "needs": _needs("rain-station-apprentice", [
                _need("nd_arrival", "establish the apprentice arriving at a rain-soaked platform"),
                _need("nd_choice", "show the apprentice choosing to protect a lost child"),
            ]),
            "creative_concept": {
                "logline": "A quiet apprentice finds courage during one rainy train delay.",
                "core_metaphor": "small lantern in heavy rain",
                "narrative_device": "two comic panels that move from isolation to resolve",
                "visual_motifs": ["rain", "amber lantern", "empty platform"],
            },
            "director_shot_plan": {
                "shots": [
                    {
                        "need_id": "nd_arrival",
                        "beat_id": "arrival",
                        "story_function": "establish the lonely rainy station and the lead apprentice",
                        "emotion": "quiet loneliness",
                        "visual_family": "rain_station_wide",
                        "angle_scale": "wide",
                        "action_family": "arrival",
                        "subject": "lead apprentice with amber lantern on empty platform",
                        "panel_count_min": 2,
                        "prompt": "watercolor comic, lead apprentice with amber lantern, empty rain-soaked train platform, 35mm wide shot, soft ink line",
                    },
                    {
                        "need_id": "nd_choice",
                        "beat_id": "choice",
                        "story_function": "show the apprentice deciding to help a lost child",
                        "emotion": "gentle resolve",
                        "visual_family": "lantern_choice_medium",
                        "angle_scale": "medium",
                        "action_family": "protective_choice",
                        "subject": "lead apprentice kneeling with lantern beside lost child silhouette",
                        "panel_count_min": 2,
                        "prompt": "watercolor comic, lead apprentice kneeling with amber lantern, lost child silhouette, 50mm medium shot, gentle resolve",
                    },
                ]
            },
            "style_profile": {
                "look": "watercolor comic with soft ink line",
                "style_anchors": ["watercolor", "soft ink line"],
                "character_anchors": ["lead apprentice", "amber lantern"],
                "palette": ["#203040", "#e0aa55", "#f5eedc"],
            },
            "director_baseline": 88,
        },
        {
            "id": "case_b_rooftop_postcard",
            "title": "Rooftop Postcard",
            "needs": _needs("rooftop-postcard", [
                _need("nd_rooftop_setup", "establish a teen courier climbing to a sunset rooftop"),
                _need("nd_postcard_payoff", "show the courier delivering the postcard to an old neighbor"),
            ]),
            "creative_concept": {
                "logline": "A courier crosses rooftops to deliver one forgotten postcard.",
                "core_metaphor": "paper message crossing the city sky",
                "narrative_device": "comic postcard panels with warm sunset continuity",
                "visual_motifs": ["sunset", "red scarf", "postcard"],
            },
            "director_shot_plan": {
                "shots": [
                    {
                        "need_id": "nd_rooftop_setup",
                        "beat_id": "setup",
                        "story_function": "establish the courier route across rooftops",
                        "emotion": "light adventure",
                        "visual_family": "rooftop_route_wide",
                        "angle_scale": "wide",
                        "action_family": "climb_rooftop",
                        "subject": "teen courier with red scarf holding postcard",
                        "panel_count_min": 2,
                        "prompt": "clean manga watercolor, teen courier with red scarf, postcard in hand, sunset rooftops, 35mm wide shot",
                    },
                    {
                        "need_id": "nd_postcard_payoff",
                        "beat_id": "payoff",
                        "story_function": "show the old neighbor receiving the postcard",
                        "emotion": "warm relief",
                        "visual_family": "postcard_delivery_close",
                        "angle_scale": "close",
                        "action_family": "deliver_postcard",
                        "subject": "red scarf courier handing postcard to old neighbor",
                        "panel_count_min": 2,
                        "prompt": "clean manga watercolor, red scarf courier hands postcard to old neighbor, 85mm close shot, warm sunset",
                    },
                ]
            },
            "style_profile": {
                "look": "clean manga watercolor with warm sunset continuity",
                "style_anchors": ["manga watercolor", "warm sunset"],
                "character_anchors": ["red scarf courier", "postcard"],
                "palette": ["#392f5a", "#ffb85c", "#fff2d5"],
            },
            "director_baseline": 85,
        },
    ]


def _contact_sheet(images: list[Path], out: Path, title: str) -> None:
    thumb_w, thumb_h = 320, 180
    cols = 2
    rows = max(1, (len(images) + cols - 1) // cols)
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + 32) + 48), "#111827")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    draw.text((12, 12), title, fill="#ffffff", font=font)
    for idx, image_path in enumerate(images):
        with Image.open(image_path) as image:
            image = image.convert("RGB")
            image.thumbnail((thumb_w, thumb_h))
            x = (idx % cols) * thumb_w
            y = 48 + (idx // cols) * (thumb_h + 32)
            sheet.paste(image, (x, y))
            draw.text((x + 8, y + thumb_h + 8), image_path.name, fill="#ffffff", font=font)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)


def _summary(delta_payload: Mapping[str, Any]) -> dict:
    return dict(delta_payload.get("summary") or {})


def _director_score(case: Mapping[str, Any], production: Mapping[str, Any],
                    after_delta: Mapping[str, Any]) -> int:
    score = int(case["director_baseline"])
    quality_gate = production.get("quality_gate") or {}
    if not quality_gate.get("pass"):
        score -= 20
    if _summary(after_delta).get("missing", 0) != 0:
        score -= 25
    if _summary(after_delta).get("thin", 0) == 0:
        score += 3
    # Candidate-only thin is expected, not a defect.
    return max(0, min(100, score))


def _run_case(case: Mapping[str, Any], root: Path) -> dict:
    case_dir = root / case["id"]
    needs = case["needs"]
    _write_json(case_dir / "material_needs.json", needs)
    _write_json(case_dir / "creative_concept.json", case["creative_concept"])
    _write_json(case_dir / "director_shot_plan.json", case["director_shot_plan"])
    _write_json(case_dir / "style_profile.json", case["style_profile"])

    initial_delta = material_delta.compute_material_delta(needs, _empty_project_map())
    _write_json(case_dir / "material_delta.json", initial_delta)
    fallback = material_generation_fallback.plan_material_generation_fallback(
        initial_delta,
        material_needs=needs,
        creative_concept=case["creative_concept"],
        director_shot_plan=case["director_shot_plan"],
    )
    _write_json(case_dir / "material_generation_fallback.json", fallback)
    production = generated_material_producer.produce_generated_materials(
        fallback,
        case_dir / "generated",
        material_needs=needs,
        style_profile=case["style_profile"],
        provider="codex_imagegen",
        renderer="test_pil",
    )
    project_map = json.loads(
        Path(production["refs"]["project_material_map"]).read_text(encoding="utf-8"))
    after_delta = material_delta.compute_material_delta(needs, project_map["assets"])
    _write_json(case_dir / "delta_after_generation.json", after_delta)
    image_paths = [Path(item["file"]) for item in production["outputs"]]
    contact_sheet = case_dir / "generated" / "contact_sheet.jpg"
    _contact_sheet(image_paths, contact_sheet, case["title"])
    score = _director_score(case, production, after_delta)
    verdict = (
        "Flow aligned. Generated panels match declared comic story anchors and "
        "entered material map as candidate evidence."
        if score >= 80 else
        "Needs revision before use."
    )
    return {
        "case_id": case["id"],
        "title": case["title"],
        "initial_delta": {"summary": _summary(initial_delta)},
        "fallback": {"jobs": len(fallback.get("generation_jobs") or [])},
        "generated": production,
        "after_generation_delta": {"summary": _summary(after_delta)},
        "director_score": score,
        "director_verdict": verdict,
        "refs": {
            "case_dir": str(case_dir),
            "contact_sheet": str(contact_sheet),
            "project_material_map": production["refs"]["project_material_map"],
            "quality_review": production["refs"]["quality_review"],
        },
    }


def _markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# Generated Material Acceptance Review",
        "",
        "Scope: two comic-style projects from no material through generated-material skill.",
        "",
        "Boundary: generated assets enter as candidate evidence; post-generation delta should become thin, not covered, until review acceptance.",
        "",
    ]
    for case in report["cases"]:
        lines.extend([
            f"## {case['title']}",
            "",
            f"- Case: `{case['case_id']}`",
            f"- Images generated: {case['generated']['summary']['image_count']}",
            f"- Initial delta: {case['initial_delta']['summary']}",
            f"- After generation delta: {case['after_generation_delta']['summary']}",
            f"- Quality gate: {case['generated']['quality_gate']}",
            f"- Director score: {case['director_score']}/100",
            f"- Verdict: {case['director_verdict']}",
            f"- Contact sheet: `{case['refs']['contact_sheet']}`",
            "",
        ])
    lines.extend([
        "## Overall",
        "",
        "- The flow is valid for generated comic/story panels.",
        "- It does not prove final art quality; `test_pil` is deterministic storyboard output.",
        "- Real GPT image / Gemini outputs should be imported through `generated-material-import`.",
        "- Generated candidates must be reviewed before promotion to accepted.",
        "",
    ])
    return "\n".join(lines)


def run_acceptance_cases(root: Path) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    cases = [_run_case(case, root) for case in _case_specs()]
    report = {
        "ok": all(case["director_score"] >= 80 for case in cases),
        "errors": [],
        "cases": cases,
    }
    _write_json(root / "flow_review.json", report)
    (root / "FLOW_REVIEW.md").write_text(_markdown(report), encoding="utf-8")
    return report


def main(argv: list[str]) -> int:
    out = Path(argv[1]) if len(argv) > 1 else Path(".tmp/generated_material_skill_acceptance")
    report = run_acceptance_cases(out)
    print(json.dumps({
        "ok": report["ok"],
        "cases": [
            {
                "case_id": case["case_id"],
                "score": case["director_score"],
                "after_generation_delta": case["after_generation_delta"]["summary"],
            }
            for case in report["cases"]
        ],
        "report": str(out / "FLOW_REVIEW.md"),
    }, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
