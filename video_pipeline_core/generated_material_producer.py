"""Generated material production adapter.

This module is the deterministic, repo-testable side of generated material
fallback. It can render simple placeholder storyboard images for acceptance
tests, and it writes the same manifest/material-map artifacts that a real
provider adapter must produce after Gemini/Antigravity/imagegen completes.

The test renderer is not a final art provider. It exists so the end-to-end flow
can be validated without external model quota.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional

from PIL import Image, ImageDraw, ImageFont

from . import generated_assets, project_material_map


ALLOWED_RENDERERS = {"test_pil"}
DEFAULT_STYLE = {
    "palette": ["#1d3557", "#f1c27d", "#f7f3e3"],
    "look": "cohesive generated material",
    "aspect_ratio": "16:9",
}
CAMERA_TOKENS = {
    "wide", "medium", "close", "ecu", "macro", "35mm", "50mm", "85mm",
    "100mm", "lens", "shot", "angle", "dolly", "static", "over-shoulder",
}
STOPWORDS = {
    "the", "a", "an", "to", "into", "one", "of", "and", "or", "with", "without",
    "in", "on", "for", "before", "after", "hard", "beats",
}


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _slug(value: str) -> str:
    chars = []
    for ch in value.lower():
        if ch.isalnum():
            chars.append(ch)
        elif chars and chars[-1] != "_":
            chars.append("_")
    return "".join(chars).strip("_") or "generated"


def _font(size: int):
    candidates = [
        "C:/Windows/Fonts/msjh.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = str(text).replace(";", " ;").split()
    lines = []
    current = ""
    for word in words:
        probe = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), probe, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = probe
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _render_test_image(job: Mapping[str, Any], path: Path, style: Mapping[str, Any]) -> None:
    palette = list(style.get("palette") or DEFAULT_STYLE["palette"])
    while len(palette) < 3:
        palette.append(DEFAULT_STYLE["palette"][len(palette)])
    bg, accent, paper = palette[:3]
    width, height = 1280, 720
    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)

    # Simple deterministic storyboard composition: background bands + subject
    # frame + text labels. This is intentionally recognizable, not photoreal.
    draw.rectangle((0, 0, width, 120), fill=accent)
    draw.rectangle((70, 170, width - 70, height - 90), fill=paper)
    draw.rectangle((95, 195, width - 95, height - 115), outline=bg, width=5)
    for i in range(7):
        x = 120 + i * 155
        draw.line((x, 215, x + 90, height - 140), fill=accent, width=3)

    title_font = _font(42)
    body_font = _font(28)
    small_font = _font(22)
    draw.text((80, 34), _text(job.get("visual_family"), "generated material"),
              fill=bg, font=title_font)
    draw.text((90, 138),
              f"{_text(job.get('need_id'))} | {_text(job.get('angle_scale'), 'angle?')} | {_text(job.get('action_family'), 'action?')}",
              fill=paper, font=small_font)
    subject = _text(job.get("subject"), "generated subject")
    prompt = _text(job.get("prompt"))
    story = _text(job.get("story_function"))
    y = 250
    for label, value in (("Subject", subject), ("Story", story), ("Prompt", prompt)):
        draw.text((130, y), f"{label}:", fill=bg, font=body_font)
        for line in _wrap(draw, value, small_font, 850)[:3]:
            draw.text((280, y + 3), line, fill=bg, font=small_font)
            y += 32
        y += 22
    draw.text((980, 610), "SOURCE: GENERATED / CANDIDATE", fill=bg, font=small_font)

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def _job_quality(job: Mapping[str, Any], style: Mapping[str, Any]) -> dict:
    prompt = _text(job.get("prompt")).lower()
    story = _text(job.get("story_function")).lower()
    visual_family = _text(job.get("visual_family"))
    angle = _text(job.get("angle_scale"))
    findings = []
    score = 100

    story_tokens = {
        token.strip(".,;:()[]{}").replace("-", " ")
        for token in story.split()
        if len(token.strip(".,;:()[]{}")) >= 4
        and token.strip(".,;:()[]{}") not in STOPWORDS
    }
    story_hit = any(part and part in prompt for token in story_tokens
                    for part in token.split())
    if story and not story_hit:
        score -= 25
        findings.append("story_function_missing_from_prompt")
    if not visual_family:
        score -= 10
        findings.append("visual_family_missing")
    if not angle:
        score -= 10
        findings.append("angle_scale_missing")
    if not any(token in prompt for token in CAMERA_TOKENS):
        score -= 15
        findings.append("camera_language_weak")
    if job.get("source_type") != "generated":
        score -= 50
        findings.append("source_type_not_generated")
    if not (job.get("honesty") or {}).get("must_not_claim_real_event"):
        score -= 30
        findings.append("truth_boundary_missing")
    if (job.get("material_map_return") or {}).get("initial_satisfies_status") != "candidate":
        score -= 30
        findings.append("candidate_return_missing")
    if not _as_list(style.get("palette")):
        score -= 5
        findings.append("style_palette_missing")

    return {
        "job_id": job.get("job_id"),
        "need_id": job.get("need_id"),
        "score": max(0, score),
        "pass": score >= 80,
        "findings": findings,
    }


def _material_map_for(job: Mapping[str, Any], output: Mapping[str, Any],
                      quality: Mapping[str, Any]) -> dict:
    asset_id = f"generated_{_slug(_text(output.get('segment')))}"
    return {
        "artifact_role": "material_map",
        "version": 1,
        "asset_id": asset_id,
        "asset_type": "photo",
        "source": output["file"],
        "duration_sec": 4.0,
        "scenes": [
            {
                "start": 0.0,
                "end": 4.0,
                "caption": _text(job.get("story_function"), _text(job.get("prompt"))),
                "visual_family": _text(job.get("visual_family")),
                "angle_scale": _text(job.get("angle_scale")),
                "action_family": _text(job.get("action_family")),
                "subject": _text(job.get("subject")),
                "source_type": "generated",
                "quality_score": quality["score"],
                "satisfies": [
                    {
                        "need_id": _text(job.get("need_id")),
                        "status": "candidate",
                        "lineage": {
                            "reviewer": "generated-material-producer",
                            "note": "generated fallback candidate; requires human/agent acceptance",
                            "generated_job_id": _text(job.get("job_id")),
                            "generated_panel_index": output.get("panel_index"),
                        },
                    }
                ],
            }
        ],
        "speech": [],
    }


def produce_generated_materials(
    fallback_artifact: Mapping[str, Any],
    out_dir: str | Path,
    *,
    material_needs: Optional[Mapping[str, Any]] = None,
    style_profile: Optional[Mapping[str, Any]] = None,
    provider: str = "codex_imagegen",
    renderer: str = "test_pil",
) -> dict:
    out = Path(out_dir)
    style = dict(DEFAULT_STYLE)
    if isinstance(style_profile, Mapping):
        style.update(style_profile)
    if renderer not in ALLOWED_RENDERERS:
        return _error(out, f"unsupported renderer: {renderer}")
    if not isinstance(fallback_artifact, Mapping) or fallback_artifact.get("ok") is not True:
        return {
            "artifact_role": "generated_material_production",
            "version": 1,
            "ok": False,
            "errors": ["material_generation_fallback is not ok"],
            "outputs": [],
            "summary": {"image_count": 0, "map_count": 0},
        }
    if material_needs is None:
        return {
            "artifact_role": "generated_material_production",
            "version": 1,
            "ok": False,
            "errors": ["material_needs is required to write candidate satisfies edges"],
            "outputs": [],
            "summary": {"image_count": 0, "map_count": 0},
        }

    images_dir = out / "generated_images"
    maps_dir = out / "generated_material_maps"
    outputs = []
    material_maps = []
    quality_items = []
    request = {
        "artifact_role": "generated_asset_requests",
        "generated_asset_requests_version": 1,
        "provider_priority": [provider],
        "items": [],
    }
    for job in fallback_artifact.get("generation_jobs") or []:
        if not isinstance(job, Mapping):
            continue
        panel_count = job.get("panel_count", 1)
        if not isinstance(panel_count, int) or isinstance(panel_count, bool) or panel_count < 1:
            panel_count = 1
        for panel_index in range(1, panel_count + 1):
            segment_id = f"{_text(job.get('job_id'))}_p{panel_index:02d}"
            filename = (
                f"{_slug(_text(job.get('need_id')))}_"
                f"{_slug(_text(job.get('job_id')))}_p{panel_index:02d}.png"
            )
            file_path = images_dir / filename
            panel_job = dict(job)
            panel_job["job_id"] = segment_id
            _render_test_image(panel_job, file_path, style)
            quality = _job_quality(job, style)
            quality["job_id"] = segment_id
            output = {
                "segment": segment_id,
                "job_id": _text(job.get("job_id")),
                "need_id": _text(job.get("need_id")),
                "panel_index": panel_index,
                "provider": provider,
                "file": str(file_path),
                "prompt": _text(job.get("prompt")),
                "reason": _text(job.get("story_function")),
                "source": "generated",
                "forbidden_as_truth": True,
                "quality_score": quality["score"],
            }
            request["items"].append({
                "segment": output["segment"],
                "provider": provider,
                "prompt": output["prompt"],
                "reason": output["reason"],
                "forbidden_as_truth": True,
                "source": "generated",
            })
            outputs.append(output)
            material_map = _material_map_for(job, output, quality)
            material_maps.append(material_map)
            map_path = maps_dir / f"{material_map['asset_id']}.map.json"
            map_path.parent.mkdir(parents=True, exist_ok=True)
            map_path.write_text(json.dumps(material_map, ensure_ascii=False, indent=2),
                                encoding="utf-8")
            quality_items.append(quality)

    out.mkdir(parents=True, exist_ok=True)
    request_path = out / "generated_asset_requests.json"
    outputs_path = out / "generated_asset_outputs.json"
    manifest_path = out / "generated_asset_manifest.json"
    request_path.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
    outputs_path.write_text(json.dumps({"items": outputs}, ensure_ascii=False, indent=2),
                            encoding="utf-8")
    generated_assets.write_generated_asset_manifest(request, outputs, manifest_path)
    project_map = project_material_map.build_project_material_map(
        material_maps, needs=material_needs)
    project_map_path = out / "project_material_map.json"
    project_map_path.write_text(json.dumps(project_map, ensure_ascii=False, indent=2),
                                encoding="utf-8")

    quality_review = {
        "artifact_role": "generated_material_quality_review",
        "version": 1,
        "pass": all(item["pass"] for item in quality_items),
        "style_profile": style,
        "items": quality_items,
        "summary": {
            "item_count": len(quality_items),
            "min_score": min([item["score"] for item in quality_items], default=0),
            "avg_score": round(
                sum(item["score"] for item in quality_items) / len(quality_items), 2)
                if quality_items else 0,
        },
    }
    quality_path = out / "generated_material_quality_review.json"
    quality_path.write_text(json.dumps(quality_review, ensure_ascii=False, indent=2),
                            encoding="utf-8")

    report = {
        "artifact_role": "generated_material_production",
        "version": 1,
        "ok": True,
        "errors": [],
        "renderer": renderer,
        "provider": provider,
        "outputs": outputs,
        "refs": {
            "generated_asset_requests": str(request_path),
            "generated_asset_outputs": str(outputs_path),
            "generated_asset_manifest": str(manifest_path),
            "generated_material_maps_dir": str(maps_dir),
            "project_material_map": str(project_map_path),
            "quality_review": str(quality_path),
        },
        "quality_gate": {
            "pass": quality_review["pass"],
            "min_score": quality_review["summary"]["min_score"],
            "avg_score": quality_review["summary"]["avg_score"],
        },
        "summary": {
            "image_count": len(outputs),
            "map_count": len(material_maps),
        },
    }
    (out / "generated_material_production.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _error(out: Path, message: str) -> dict:
    return {
        "artifact_role": "generated_material_production",
        "version": 1,
        "ok": False,
        "errors": [message],
        "outputs": [],
        "summary": {"image_count": 0, "map_count": 0},
    }
