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
import re
import shutil
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

    story_tokens = {
        token.strip(".,;:()[]{}").replace("-", " ")
        for token in story.split()
        if len(token.strip(".,;:()[]{}")) >= 4
        and token.strip(".,;:()[]{}") not in STOPWORDS
    }
    story_hit = any(part and part in prompt for token in story_tokens
                    for part in token.split())

    style_anchors = _as_list(style.get("style_anchors"))
    missing_style = [
        str(anchor).strip().lower() for anchor in style_anchors
        if str(anchor).strip() and not _anchor_matches(str(anchor), prompt)
    ]
    character_anchors = _as_list(style.get("character_anchors"))
    character_text = " ".join([
        prompt,
        _text(job.get("subject")).lower(),
    ])
    missing_characters = [
        str(anchor).strip().lower() for anchor in character_anchors
        if str(anchor).strip() and not _anchor_matches(str(anchor), character_text)
    ]

    story_findings = []
    if story and not story_hit:
        story_findings.append("story_function_missing_from_prompt")
    if not visual_family:
        story_findings.append("visual_family_missing")
    if not angle:
        story_findings.append("angle_scale_missing")

    camera_findings = []
    if not any(token in prompt for token in CAMERA_TOKENS):
        camera_findings.append("camera_language_weak")

    truth_findings = []
    if job.get("source_type") != "generated":
        truth_findings.append("source_type_not_generated")
    if not (job.get("honesty") or {}).get("must_not_claim_real_event"):
        truth_findings.append("truth_boundary_missing")

    coverage_findings = []
    if not _text(job.get("need_id")):
        coverage_findings.append("need_id_missing")
    if (job.get("material_map_return") or {}).get("initial_satisfies_status") != "candidate":
        coverage_findings.append("candidate_return_missing")

    style_findings = []
    if missing_style:
        style_findings.append("style_anchor_missing_from_prompt:" + ",".join(missing_style))
    if not _as_list(style.get("palette")):
        style_findings.append("style_palette_missing")

    character_findings = []
    if missing_characters:
        character_findings.append(
            "character_anchor_missing_from_prompt:" + ",".join(missing_characters))

    rubric = {
        "story_fit": _dimension(100 if not story_findings else 60, story_findings),
        "style_consistency": _dimension(100 if not style_findings else 60, style_findings),
        "character_continuity": _dimension(
            100 if not character_findings else 60, character_findings),
        "camera_language": _dimension(100 if not camera_findings else 40, camera_findings),
        "truth_boundary": _dimension(100 if not truth_findings else 40, truth_findings),
        "need_coverage": _dimension(100 if not coverage_findings else 40, coverage_findings),
    }

    return _finalize_quality(job.get("job_id"), job.get("need_id"), rubric)


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


def _output_items(payload: Any) -> list:
    if isinstance(payload, Mapping):
        return _as_list(payload.get("items"))
    if isinstance(payload, list):
        return payload
    return []


def _provider_outputs_by_job(payload: Any) -> dict[str, list[Mapping[str, Any]]]:
    indexed: dict[str, list[Mapping[str, Any]]] = {}
    for item in _output_items(payload):
        if not isinstance(item, Mapping):
            continue
        job_id = _text(item.get("job_id"))
        if job_id:
            indexed.setdefault(job_id, []).append(item)
    return indexed


def _required_panel_count(job: Mapping[str, Any]) -> int:
    panel_count = job.get("panel_count", 1)
    if isinstance(panel_count, bool) or not isinstance(panel_count, int) or panel_count < 1:
        return 1
    return panel_count


def _resolve_provider_file(item: Mapping[str, Any], base_dir: Path) -> Path:
    raw = _text(item.get("file"))
    if not raw:
        raise ValueError("provider output requires file")
    path = Path(raw)
    if not path.is_absolute():
        path = base_dir / path
    return path


def _ensure_readable_image(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(str(path))
    with Image.open(path) as im:
        im.verify()


def _copy_provider_image(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    _ensure_readable_image(destination)


def _lower_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item).strip().lower() for item in value if str(item).strip()}


def _anchor_matches(anchor: str, text: str) -> bool:
    anchor = str(anchor or "").strip().lower()
    text = str(text or "").strip().lower()
    if not anchor:
        return True
    if anchor in text:
        return True
    terms = [
        token for token in re.findall(r"[\w\u4e00-\u9fff]+", anchor)
        if len(token) > 1
    ]
    return bool(terms) and all(term in text for term in terms)


def _dimension(score: int, findings: list[str] | None = None) -> dict:
    score = max(0, min(100, int(score)))
    findings = list(findings or [])
    return {"score": score, "pass": score >= 80, "findings": findings}


def _finalize_quality(job_id: Any, need_id: Any, rubric: Mapping[str, Mapping[str, Any]]) -> dict:
    findings = []
    scores = []
    passes = []
    for dim in rubric.values():
        scores.append(int(dim.get("score", 0)))
        passes.append(bool(dim.get("pass")))
        findings.extend(dim.get("findings") or [])
    score = min(scores) if scores else 0
    return {
        "job_id": job_id,
        "need_id": need_id,
        "score": max(0, score),
        "pass": all(passes) if passes else False,
        "findings": findings,
        "rubric": rubric,
    }


def _provider_quality(job: Mapping[str, Any], output_item: Mapping[str, Any],
                      style: Mapping[str, Any], segment_id: str) -> dict:
    quality = _job_quality(job, style)
    required_style = _lower_set(style.get("style_anchors"))
    required_characters = _lower_set(style.get("character_anchors"))
    actual_style = _lower_set(output_item.get("style_anchors") or output_item.get("style_tags"))
    actual_characters = _lower_set(output_item.get("character_anchors"))

    missing_style = sorted(required_style - actual_style)
    missing_characters = sorted(required_characters - actual_characters)
    rubric = dict(quality["rubric"])
    if missing_style:
        rubric["style_consistency"] = _dimension(
            60, ["style_anchor_mismatch:" + ",".join(missing_style)])
    else:
        rubric["style_consistency"] = _dimension(100)
    if missing_characters:
        rubric["character_continuity"] = _dimension(
            60, ["character_anchor_mismatch:" + ",".join(missing_characters)])
    else:
        rubric["character_continuity"] = _dimension(100)

    return _finalize_quality(segment_id, job.get("need_id"), rubric)


def _write_provider_error(out: Path, errors: list[str], *, quality_items: Optional[list] = None) -> dict:
    report = {
        "artifact_role": "generated_material_production",
        "version": 1,
        "ok": False,
        "errors": errors,
        "outputs": [],
        "summary": {"image_count": 0, "map_count": 0},
    }
    if quality_items is not None:
        report["quality_gate"] = {
            "pass": all(item.get("pass") for item in quality_items),
            "min_score": min([item.get("score", 0) for item in quality_items], default=0),
            "avg_score": round(
                sum(item.get("score", 0) for item in quality_items) / len(quality_items), 2)
                if quality_items else 0,
        }
    if quality_items:
        out.mkdir(parents=True, exist_ok=True)
        (out / "generated_material_quality_review.json").write_text(
            json.dumps({
                "artifact_role": "generated_material_quality_review",
                "version": 1,
                "pass": report["quality_gate"]["pass"],
                "items": quality_items,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return report


def produce_generated_materials_from_provider_outputs(
    fallback_artifact: Mapping[str, Any],
    provider_outputs: Mapping[str, Any] | list,
    out_dir: str | Path,
    *,
    material_needs: Optional[Mapping[str, Any]] = None,
    style_profile: Optional[Mapping[str, Any]] = None,
) -> dict:
    """Import externally generated image files into GMP1 artifacts.

    The provider has already produced files. This function verifies that every
    planned job has enough readable image outputs, copies them under the GMP
    output directory, checks declared style/character anchors, then writes the
    same manifest + candidate material-map artifacts as the offline renderer.
    """
    out = Path(out_dir)
    style = dict(DEFAULT_STYLE)
    if isinstance(style_profile, Mapping):
        style.update(style_profile)
    if not isinstance(fallback_artifact, Mapping) or fallback_artifact.get("ok") is not True:
        return _write_provider_error(out, ["material_generation_fallback is not ok"])
    if material_needs is None:
        return _write_provider_error(
            out, ["material_needs is required to write candidate satisfies edges"])

    base_dir = Path(".")
    if isinstance(provider_outputs, Mapping) and _text(provider_outputs.get("_path")):
        base_dir = Path(str(provider_outputs["_path"])).parent
    indexed = _provider_outputs_by_job(provider_outputs)
    errors: list[str] = []
    quality_items = []
    staged: list[tuple[Mapping[str, Any], Mapping[str, Any], Path, str, int, dict]] = []

    for job in fallback_artifact.get("generation_jobs") or []:
        if not isinstance(job, Mapping):
            continue
        job_id = _text(job.get("job_id"))
        supplied = indexed.get(job_id, [])
        required = _required_panel_count(job)
        if len(supplied) < required:
            errors.append(f"missing provider output for {job_id}: required {required}, got {len(supplied)}")
            continue
        for panel_index, item in enumerate(supplied[:required], start=1):
            try:
                source = _resolve_provider_file(item, base_dir)
                _ensure_readable_image(source)
            except (OSError, ValueError) as exc:
                errors.append(f"unreadable provider output for {job_id}: {exc}")
                continue
            segment_id = f"{job_id}_p{panel_index:02d}"
            quality = _provider_quality(job, item, style, segment_id)
            quality_items.append(quality)
            staged.append((job, item, source, segment_id, panel_index, quality))

    if errors:
        return _write_provider_error(out, errors, quality_items=quality_items)
    if quality_items and not all(item["pass"] for item in quality_items):
        return _write_provider_error(out, ["generated provider quality gate failed"],
                                     quality_items=quality_items)

    images_dir = out / "generated_images"
    maps_dir = out / "generated_material_maps"
    request = {
        "artifact_role": "generated_asset_requests",
        "generated_asset_requests_version": 1,
        "provider_priority": [],
        "items": [],
    }
    outputs = []
    material_maps = []
    for job, item, source, segment_id, panel_index, quality in staged:
        provider = _text(item.get("provider"), "codex_imagegen")
        if provider not in request["provider_priority"]:
            request["provider_priority"].append(provider)
        extension = source.suffix.lower() if source.suffix else ".png"
        dest = images_dir / f"{_slug(_text(job.get('need_id')))}_{_slug(segment_id)}{extension}"
        _copy_provider_image(source, dest)
        output = {
            "segment": segment_id,
            "job_id": _text(job.get("job_id")),
            "need_id": _text(job.get("need_id")),
            "panel_index": panel_index,
            "provider": provider,
            "file": str(dest),
            "prompt": _text(item.get("prompt"), _text(job.get("prompt"))),
            "reason": _text(job.get("story_function")),
            "source": "generated",
            "forbidden_as_truth": True,
            "quality_score": quality["score"],
            "metadata": {
                "style_anchors": item.get("style_anchors") or item.get("style_tags") or [],
                "character_anchors": item.get("character_anchors") or [],
            },
        }
        request["items"].append({
            "segment": segment_id,
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
        "renderer": "provider_outputs",
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


def produce_generated_materials(
    fallback_artifact: Mapping[str, Any],
    out_dir: str | Path,
    *,
    material_needs: Optional[Mapping[str, Any]] = None,
    style_profile: Optional[Mapping[str, Any]] = None,
    provider: str = "codex_imagegen",
    renderer: str = "test_pil",
    allow_test_renderer: bool = False,
) -> dict:
    out = Path(out_dir)
    style = dict(DEFAULT_STYLE)
    if isinstance(style_profile, Mapping):
        style.update(style_profile)
    if renderer not in ALLOWED_RENDERERS:
        return _error(out, f"unsupported renderer: {renderer}")
    if renderer == "test_pil" and not allow_test_renderer:
        return _error(
            out,
            (
                "test_pil renderer is test-only and cannot create delivery "
                "generated material; use generated-image-provider-packet plus "
                "generated-material-import, or pass --allow-test-renderer for "
                "bounded acceptance tests"
            ),
        )
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
