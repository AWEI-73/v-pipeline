"""Provider handoff packet for real generated-image production.

This module does not call GPT image, Gemini, Antigravity, or any other model.
It turns verified generated-material jobs into a deterministic packet that a
model-driving agent can execute, then hands the resulting files back to the
existing generated-material import gate.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence


DEFAULT_PROVIDERS = ["codex_imagegen", "gemini", "antigravity", "assistant_imagegen"]
TEST_ONLY_PROVIDERS = {"test_pil", "placeholder", "mock", "dummy"}
DEFAULT_STYLE = {
    "look": "cohesive generated material",
    "style_anchors": [],
    "character_anchors": [],
    "palette": [],
    "aspect_ratio": "16:9",
}


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _slug(value: str) -> str:
    chars: list[str] = []
    for ch in value.lower():
        if ch.isalnum():
            chars.append(ch)
        elif chars and chars[-1] != "_":
            chars.append("_")
    return "".join(chars).strip("_") or "generated"


def _providers(value: Sequence[str] | str | None) -> list[str]:
    if value is None:
        items = DEFAULT_PROVIDERS
    elif isinstance(value, str):
        items = [part.strip() for part in value.split(",")]
    else:
        items = [str(part).strip() for part in value]
    seen = []
    for item in items:
        if item and item not in seen:
            seen.append(item)
    return seen


def _panel_count(job: Mapping[str, Any]) -> int:
    count = job.get("panel_count", 1)
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        return 1
    return count


def _job_id(job: Mapping[str, Any]) -> str:
    return _text(job.get("job_id"))


def _target_file(out: Path, job: Mapping[str, Any], panel_index: int) -> Path:
    need_id = _slug(_text(job.get("need_id"), "need"))
    job_id = _slug(_job_id(job))
    return out / "provider_outputs" / f"{need_id}_{job_id}_p{panel_index:02d}.png"


def _path_text(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def _style_profile(style_profile: Mapping[str, Any] | None) -> dict:
    style = dict(DEFAULT_STYLE)
    if isinstance(style_profile, Mapping):
        style.update(style_profile)
    return style


def _merge_anchors(job_value: Any, style_value: Any) -> list[str]:
    merged = []
    for value in list(_as_list(style_value)) + list(_as_list(job_value)):
        item = str(value).strip()
        if item and item not in merged:
            merged.append(item)
    return merged


def _prompt(job: Mapping[str, Any], style: Mapping[str, Any]) -> str:
    story = _text(job.get("story_function"))
    subject = _text(job.get("subject"))
    angle = _text(job.get("angle_scale"), "medium")
    visual_family = _text(job.get("visual_family"))
    action = _text(job.get("action_family"))
    emotion = _text(job.get("emotion"))
    base_prompt = _text(job.get("prompt"))
    look = _text(style.get("look"), DEFAULT_STYLE["look"])
    palette = ", ".join(_as_list(style.get("palette")))
    style_anchors = ", ".join(_merge_anchors(job.get("style_anchors"), style.get("style_anchors")))
    character_anchors = ", ".join(_merge_anchors(
        job.get("character_anchors"), style.get("character_anchors")))

    lines = [
        "Use case: illustration-story",
        "Asset type: generated material candidate for video pipeline",
        f"Primary request: {base_prompt or story or subject}",
        f"Story function: {story}",
        f"Subject: {subject}",
        f"Style/medium: {look}",
        f"Composition/framing: {angle} shot; visual family {visual_family}; action family {action}",
        f"Lighting/mood: {emotion}",
    ]
    if palette:
        lines.append(f"Color palette: {palette}")
    if style_anchors:
        lines.append(f"Style anchors: {style_anchors}")
    if character_anchors:
        lines.append(f"Character anchors: {character_anchors}")
    lines.extend([
        "Constraints: no readable logo, no fake official proof, no watermark, no generated text unless explicitly requested; keep visual continuity with the style and character anchors.",
        f"Avoid: {_text(job.get('negative_prompt'), 'text, logo, watermark, malformed hands, unrelated subject')}",
    ])
    return "\n".join(line for line in lines if line.split(":", 1)[-1].strip())


def _packet_item(job: Mapping[str, Any], panel_index: int, out: Path,
                 providers: list[str], style: Mapping[str, Any]) -> dict:
    target = _target_file(out, job, panel_index)
    return {
        "job_id": _job_id(job),
        "need_id": _text(job.get("need_id")),
        "panel_index": panel_index,
        "target_file": _path_text(target),
        "provider_candidates": providers,
        "preferred_provider": providers[0],
        "media_type": _text(job.get("media_type"), "generated_image"),
        "story_function": _text(job.get("story_function")),
        "emotion": _text(job.get("emotion")),
        "visual_family": _text(job.get("visual_family")),
        "angle_scale": _text(job.get("angle_scale")),
        "action_family": _text(job.get("action_family")),
        "subject": _text(job.get("subject")),
        "prompt": _prompt(job, style),
        "negative_prompt": _text(job.get("negative_prompt")),
        "style_anchors": _merge_anchors(job.get("style_anchors"), style.get("style_anchors")),
        "character_anchors": _merge_anchors(
            job.get("character_anchors"), style.get("character_anchors")),
        "forbidden_as_truth": True,
        "quality_check": [
            "image file exists at target_file and is readable",
            "matches story_function and subject",
            "keeps style_anchors and character_anchors visible",
            "does not look like real documentary proof",
            "contains no watermark, fake logo, or accidental text",
        ],
    }


def _outputs_template(items: list[dict]) -> dict:
    return {
        "artifact_role": "generated_provider_outputs",
        "version": 1,
        "instructions": (
            "After generating each image, save it exactly to file and run "
            "video_tools.py generated-material-import with this JSON."
        ),
        "items": [
            {
                "job_id": item["job_id"],
                "file": item["target_file"],
                "provider": item["preferred_provider"],
                "prompt": item["prompt"],
                "style_anchors": item["style_anchors"],
                "character_anchors": item["character_anchors"],
            }
            for item in items
        ],
    }


def _prompts_md(packet: Mapping[str, Any]) -> str:
    lines = [
        "# Generated Image Provider Packet",
        "",
        "Use an actual image-generation provider for every item. Do not use `test_pil` for final art.",
        "",
        "After files are saved, import them:",
        "",
        "```powershell",
        "python video_tools.py generated-material-import material_generation_fallback.json `",
        "  --needs material_needs.json `",
        "  --provider-outputs generated_provider_outputs.json `",
        "  --style-profile style_profile.json `",
        "  --out-dir generated_materials",
        "```",
        "",
    ]
    for item in packet["items"]:
        lines.extend([
            f"## {item['job_id']} / panel {item['panel_index']}",
            "",
            f"- Target file: `{item['target_file']}`",
            f"- Preferred provider: `{item['preferred_provider']}`",
            f"- Provider candidates: {', '.join(item['provider_candidates'])}",
            "",
            "```text",
            item["prompt"],
            "```",
            "",
        ])
    return "\n".join(lines)


def build_generated_image_provider_packet(
    fallback_artifact: Mapping[str, Any],
    out_dir: str | Path,
    *,
    style_profile: Mapping[str, Any] | None = None,
    providers: Sequence[str] | str | None = None,
) -> dict:
    out = Path(out_dir)
    provider_list = _providers(providers)
    errors: list[str] = []
    if not isinstance(fallback_artifact, Mapping) or fallback_artifact.get("ok") is not True:
        errors.append("material_generation_fallback is not ok")
    if not any(provider not in TEST_ONLY_PROVIDERS for provider in provider_list):
        errors.append("provider list must include a real image provider")
    if not provider_list:
        errors.append("provider list must not be empty")
    jobs = [job for job in _as_list(fallback_artifact.get("generation_jobs"))
            if isinstance(job, Mapping)]
    if not jobs and not errors:
        errors.append("material_generation_fallback contains no generation_jobs")
    for index, job in enumerate(jobs, start=1):
        if not _job_id(job):
            errors.append(f"generation job #{index} requires job_id")
        if _text(job.get("source_type")) != "generated":
            errors.append(f"generation job #{index} source_type must be generated")
        if _text(job.get("media_type"), "generated_image") != "generated_image":
            errors.append(f"generation job #{index} media_type must be generated_image")
    if errors:
        return {
            "artifact_role": "generated_image_provider_packet_result",
            "version": 1,
            "ok": False,
            "errors": errors,
            "summary": {"job_count": 0, "image_count": 0},
        }

    style = _style_profile(style_profile)
    items = []
    for job in jobs:
        for panel_index in range(1, _panel_count(job) + 1):
            items.append(_packet_item(job, panel_index, out, provider_list, style))
    packet = {
        "artifact_role": "generated_image_provider_packet",
        "version": 1,
        "provider_priority": provider_list,
        "renderer_contract": "external_provider_files",
        "test_renderer_forbidden_for_final_art": True,
        "style_profile": style,
        "items": items,
        "import_template": "generated_provider_outputs.template.json",
    }
    template = _outputs_template(items)

    out.mkdir(parents=True, exist_ok=True)
    (out / "provider_outputs").mkdir(parents=True, exist_ok=True)
    (out / "generated_provider_packet.json").write_text(
        json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "generated_provider_outputs.template.json").write_text(
        json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "generated_provider_prompts.md").write_text(
        _prompts_md(packet), encoding="utf-8")

    return {
        "artifact_role": "generated_image_provider_packet_result",
        "version": 1,
        "ok": True,
        "errors": [],
        "refs": {
            "provider_packet": _path_text(out / "generated_provider_packet.json"),
            "provider_prompts": _path_text(out / "generated_provider_prompts.md"),
            "provider_outputs_template": _path_text(out / "generated_provider_outputs.template.json"),
            "provider_outputs_dir": _path_text(out / "provider_outputs"),
        },
        "summary": {
            "job_count": len(jobs),
            "image_count": len(items),
        },
    }
