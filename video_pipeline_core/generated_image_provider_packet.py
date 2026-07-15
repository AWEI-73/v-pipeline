"""Provider handoff packet for real generated-image production.

This module does not call GPT image, Gemini, Antigravity, or any other model.
It turns verified generated-material jobs into a deterministic packet that a
model-driving agent can execute, then hands the resulting files back to the
existing generated-material import gate.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

from PIL import Image


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


def _image_files(root: Path) -> list[Path]:
    suffixes = {".png", ".jpg", ".jpeg", ".webp"}
    if not root.exists():
        return []
    if root.is_file():
        return [root] if root.suffix.lower() in suffixes else []
    return sorted(
        (path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in suffixes),
        key=lambda path: (path.stat().st_mtime, path.name),
    )


def _latest_generated_session(generated_root: Path, *, min_count: int = 1) -> tuple[Path | None, list[Path]]:
    if not generated_root.exists() or not generated_root.is_dir():
        return None, []
    sessions = [path for path in generated_root.iterdir() if path.is_dir()]
    candidates: list[tuple[float, Path, list[Path]]] = []
    for session in sessions:
        images = _image_files(session)
        if len(images) >= min_count:
            newest = max(path.stat().st_mtime for path in images)
            candidates.append((newest, session, images))
    if not candidates:
        return None, []
    _, session, images = max(candidates, key=lambda item: (item[0], len(item[2]), item[1].name))
    return session, images


def _readable_image(path: Path) -> bool:
    try:
        with Image.open(path) as image:
            image.verify()
        return True
    except Exception:
        return False


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


def _panel_variation(panel_index: int, panel_count: int) -> str:
    if panel_count <= 1:
        return ""
    roles = [
        (
            "establishing variation",
            "wider framing, show the environment and spatial context clearly",
        ),
        (
            "character/emotion variation",
            "closer framing, emphasize the subject expression and emotional state",
        ),
        (
            "action/detail variation",
            "show a different moment of the same story function with visible action or guiding detail",
        ),
        (
            "resolution/transition variation",
            "compose as a bridge to the next beat with changed pose, camera distance, or direction of movement",
        ),
    ]
    role, guidance = roles[(panel_index - 1) % len(roles)]
    return (
        f"Panel variation: panel {panel_index} of {panel_count}; {role}; {guidance}. "
        "Keep the same subject, style anchors, and story function, but do not duplicate the exact same composition."
    )


def _prompt(job: Mapping[str, Any], style: Mapping[str, Any],
            panel_index: int = 1, panel_count: int = 1) -> str:
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
    use_case = _text(job.get("use_case"), "illustration-story")

    lines = [
        f"Use case: {use_case}",
        "Asset type: generated material candidate for video pipeline",
        f"Primary request: {base_prompt or story or subject}",
        f"Story function: {story}",
        f"Subject: {subject}",
        f"Style/medium: {look}",
        f"Composition/framing: {angle} shot; visual family {visual_family}; action family {action}",
        f"Lighting/mood: {emotion}",
    ]
    variation = _panel_variation(panel_index, panel_count)
    if variation:
        lines.append(variation)
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


def _packet_item(job: Mapping[str, Any], panel_index: int, panel_count: int, out: Path,
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
        "use_case": _text(job.get("use_case"), "illustration-story"),
        "story_function": _text(job.get("story_function")),
        "panel_count": panel_count,
        "panel_variation": _panel_variation(panel_index, panel_count),
        "emotion": _text(job.get("emotion")),
        "visual_family": _text(job.get("visual_family")),
        "angle_scale": _text(job.get("angle_scale")),
        "action_family": _text(job.get("action_family")),
        "subject": _text(job.get("subject")),
        "prompt": _prompt(job, style, panel_index=panel_index, panel_count=panel_count),
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


def _provider_outputs_item(packet_item: Mapping[str, Any], source: Path, target: Path,
                           provider: str) -> dict:
    item = {
        "job_id": _text(packet_item.get("job_id")),
        "need_id": _text(packet_item.get("need_id")),
        "panel_index": packet_item.get("panel_index"),
        "file": _path_text(target),
        "provider": provider,
        "prompt": _text(packet_item.get("prompt")),
        "style_anchors": _as_list(packet_item.get("style_anchors")),
        "character_anchors": _as_list(packet_item.get("character_anchors")),
        "source_image": _path_text(source),
    }
    return {key: value for key, value in item.items() if value not in ("", None)}


def fill_provider_outputs_from_codex_images(
    packet_path: str | Path,
    *,
    image_files: Sequence[str | Path] | None = None,
    generated_root: str | Path | None = None,
    out_path: str | Path | None = None,
    provider: str = "codex_imagegen",
) -> dict:
    """Copy Codex imagegen outputs into a provider packet's target files.

    This helper does not call an image model. It only turns already-generated
    files into the standard `generated_provider_outputs.json` shape expected by
    `generated-material-import`.
    """
    packet_file = Path(packet_path)
    errors: list[str] = []
    source_session: Path | None = None
    packet: dict[str, Any] = {}
    items: list[Any] = []

    try:
        packet = json.loads(packet_file.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"cannot read provider packet: {exc}")
    if packet and packet.get("artifact_role") != "generated_image_provider_packet":
        errors.append("packet artifact_role must be generated_image_provider_packet")
    if packet:
        items = _as_list(packet.get("items"))
        if not items:
            errors.append("provider packet contains no items")
        if not all(isinstance(item, Mapping) for item in items):
            errors.append("provider packet items must be objects")

    if image_files is not None:
        sources = [Path(path) for path in image_files]
    else:
        root = Path(generated_root) if generated_root is not None else Path.home() / ".codex" / "generated_images"
        source_session, sources = _latest_generated_session(root, min_count=len(items) or 1)

    if len(sources) < len(items):
        errors.append(f"not enough image files: need {len(items)}, got {len(sources)}")
    unreadable = [str(path) for path in sources[:len(items)] if not path.exists() or not path.is_file() or not _readable_image(path)]
    if unreadable:
        errors.append("unreadable image file(s): " + ", ".join(unreadable))

    targets: list[Path] = []
    if not errors:
        for index, item in enumerate(items, start=1):
            target_text = _text(item.get("target_file"))
            if not target_text:
                errors.append(f"provider packet item #{index} requires target_file")
                continue
            targets.append(Path(target_text))

    if errors:
        return {
            "artifact_role": "codex_imagegen_provider_fill_result",
            "version": 1,
            "ok": False,
            "errors": errors,
            "summary": {
                "required_count": len(items),
                "source_count": len(sources),
                "copied_count": 0,
            },
        }

    output_items: list[dict] = []
    try:
        for item, source, target in zip(items, sources, targets):
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.resolve() != target.resolve():
                shutil.copy2(source, target)
            if not _readable_image(target):
                raise ValueError(f"copied image is unreadable: {target}")
            output_items.append(_provider_outputs_item(item, source, target, provider))
        provider_outputs = {
            "artifact_role": "generated_provider_outputs",
            "version": 1,
            "items": output_items,
        }
        output_file = Path(out_path) if out_path is not None else packet_file.parent / "generated_provider_outputs.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(provider_outputs, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        return {
            "artifact_role": "codex_imagegen_provider_fill_result",
            "version": 1,
            "ok": False,
            "errors": [f"failed to fill provider outputs: {exc}"],
            "summary": {
                "required_count": len(items),
                "source_count": len(sources),
                "copied_count": len(output_items),
            },
        }

    refs = {"provider_outputs": _path_text(output_file)}
    if source_session is not None:
        refs["source_session"] = _path_text(source_session)
    return {
        "artifact_role": "codex_imagegen_provider_fill_result",
        "version": 1,
        "ok": True,
        "errors": [],
        "refs": refs,
        "provider_outputs": provider_outputs,
        "summary": {
            "required_count": len(items),
            "source_count": len(sources),
            "copied_count": len(output_items),
        },
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


def _handoff_item(item: Mapping[str, Any], index: int) -> dict:
    target_file = _text(item.get("target_file"))
    prompt = _text(item.get("prompt"))
    job_id = _text(item.get("job_id"), f"job_{index:03d}")
    return {
        "job_id": job_id,
        "need_id": _text(item.get("need_id")),
        "panel_index": item.get("panel_index"),
        "target_file": target_file,
        "provider": _text(item.get("preferred_provider"), "codex_imagegen"),
        "tool_mode": "built_in_image_gen",
        "prompt": prompt,
        "negative_prompt": _text(item.get("negative_prompt")),
        "save_policy": (
            "Generate a real bitmap image with the image generation tool, then "
            "copy or move the selected output to target_file. Do not create a "
            "text card, placeholder, SVG stand-in, or test_pil image."
        ),
        "quality_check": _as_list(item.get("quality_check")) or [
            "image file exists at target_file and is readable",
            "matches story_function and subject",
            "contains no watermark, fake logo, or accidental text",
        ],
    }


def _image_agent_handoff_md(handoff: Mapping[str, Any]) -> str:
    lines = [
        "# Image Agent Handoff",
        "",
        "Use a real image generation tool for each item below.",
        "Do not make text cards, placeholder graphics, SVG mockups, or test_pil outputs.",
        "If image generation is unavailable, stop and report `provider_unavailable`; do not fabricate files.",
        "",
        "After every target file exists, run:",
        "",
        "```powershell",
        "python video_tools.py codex-imagegen-provider-fill generated_provider_packet.json "
        "--image-files <generated image files in packet order>",
        "python video_tools.py generated-material-import material_generation_fallback.json "
        "--needs material_needs.json --provider-outputs generated_provider_outputs.json "
        "--style-profile style_profile.json --out-dir generated_materials",
        "```",
        "",
    ]
    for item in handoff.get("items") or []:
        lines.extend([
            f"## {item.get('job_id')} / panel {item.get('panel_index')}",
            "",
            f"- Target file: `{item.get('target_file')}`",
            f"- Provider/tool mode: `{item.get('provider')}` / `{item.get('tool_mode')}`",
            "- Required behavior: generate a real bitmap image and save it to the target file.",
            "",
            "```text",
            str(item.get("prompt") or ""),
            "```",
            "",
        ])
    return "\n".join(lines)


def build_image_agent_prompt_handoff(
    packet_path: str | Path,
    out_dir: str | Path | None = None,
    *,
    max_items: int | None = None,
) -> dict:
    """Write an agent-executable prompt handoff for real image generation.

    This helper still does not call a model. It makes the provider packet
    directly actionable for an image-capable agent by preserving exact target
    filenames, prompts, and fail-closed instructions.
    """
    packet_file = Path(packet_path)
    errors: list[str] = []
    try:
        packet = json.loads(packet_file.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        packet = {}
        errors.append(f"cannot read provider packet: {exc}")
    if packet and packet.get("artifact_role") != "generated_image_provider_packet":
        errors.append("packet artifact_role must be generated_image_provider_packet")
    items = [item for item in _as_list(packet.get("items")) if isinstance(item, Mapping)]
    if packet and not items:
        errors.append("provider packet contains no items")
    if max_items is not None:
        if max_items < 1:
            errors.append("max_items must be >= 1")
        else:
            items = items[:max_items]
    for index, item in enumerate(items, start=1):
        if not _text(item.get("target_file")):
            errors.append(f"provider packet item #{index} requires target_file")
        prompt = _text(item.get("prompt"))
        if not prompt:
            errors.append(f"provider packet item #{index} requires prompt")
        lowered = prompt.casefold()
        forbidden = [
            token for token in ("test_pil", "placeholder", "text card", "文字卡")
            if token in lowered
        ]
        if forbidden:
            errors.append(
                f"provider packet item #{index} prompt contains forbidden placeholder token(s): "
                + ", ".join(forbidden)
            )
    if errors:
        return {
            "artifact_role": "image_agent_prompt_handoff_result",
            "version": 1,
            "ok": False,
            "errors": errors,
            "summary": {"item_count": 0},
        }

    out = Path(out_dir) if out_dir is not None else packet_file.parent / "image_agent_handoff"
    handoff_items = [_handoff_item(item, index) for index, item in enumerate(items, start=1)]
    provider_outputs = out / "generated_provider_outputs.json"
    handoff = {
        "artifact_role": "image_agent_prompt_handoff",
        "version": 1,
        "source_packet": _path_text(packet_file),
        "provider_outputs": _path_text(provider_outputs),
        "next_action": "call_image_generation_agent",
        "fail_closed": True,
        "forbidden_outputs": ["text_card", "placeholder", "test_pil", "svg_standin"],
        "items": handoff_items,
        "completion_contract": {
            "required": [
                "Every target_file exists and is a readable image.",
                "generated_provider_outputs.json is written or codex-imagegen-provider-fill is run.",
                "generated-material-import is run only after real images exist.",
            ],
            "if_unavailable": "Stop and report provider_unavailable; do not fabricate placeholder assets.",
        },
    }
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "image_agent_prompt_handoff.json"
    md_path = out / "image_agent_prompt.md"
    json_path.write_text(json.dumps(handoff, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_image_agent_handoff_md(handoff), encoding="utf-8")
    return {
        "artifact_role": "image_agent_prompt_handoff_result",
        "version": 1,
        "ok": True,
        "errors": [],
        "refs": {
            "image_agent_handoff": _path_text(json_path),
            "image_agent_prompt": _path_text(md_path),
            "provider_outputs": _path_text(provider_outputs),
        },
        "summary": {"item_count": len(handoff_items)},
    }


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
        panel_count = _panel_count(job)
        for panel_index in range(1, panel_count + 1):
            items.append(_packet_item(job, panel_index, panel_count, out, provider_list, style))
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
