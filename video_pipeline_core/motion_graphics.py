"""motion_graphics.py — Node 14 effects contract scaffold.

The core edit flow should not require a heavy motion graphics stack. This module
keeps title/lower-third/name-list effects as explicit artifacts that can be
rendered by a safe ffmpeg/libass backend first, then upgraded to Remotion,
HTML/Playwright, Blender, or external compositors when the route allows it.
"""
import html
import json
import subprocess
from pathlib import Path


ALLOWED_BACKENDS = {
    "ffmpeg_libass",
    "html_playwright",
    "remotion",
    "mlt",
    "blender",
    "external_ae",
}

HEAVY_BACKENDS = {"blender", "external_ae"}

ALLOWED_EFFECT_TYPES = {
    "title_sequence",
    "name_list",
    "lower_third",
    "chapter_card",
    "info_card",
    "logo_intro",
}

TEXT_RECIPES = {
    "title_sequence": {
        "template": "title_fade",
        "motion": "fade_scale",
        "safe_area": "title_safe",
    },
    "chapter_card": {
        "template": "section_label",
        "motion": "pop",
        "safe_area": "title_safe",
    },
    "lower_third": {
        "template": "lower_third_clean",
        "motion": "slide_up",
        "safe_area": "lower_third",
    },
}


def contract_from_timeline(canonical_contract, timeline, *, backend="ffmpeg_libass", contract_hash=None):
    """Build a timed Node 14 contract from canonical text layers and Node 10 clips."""
    clips_by_segment = {}
    for clip in (timeline or {}).get("clips", []):
        clips_by_segment.setdefault(clip.get("segment"), []).append(clip)
    items = []
    for idx, segment in enumerate((canonical_contract or {}).get("segments", []), start=1):
        segment_id = segment.get("segment", idx)
        clips = clips_by_segment.get(segment_id) or []
        text_layer = segment.get("text_layer")
        if not clips or not isinstance(text_layer, dict):
            continue
        starts = [float(clip.get("timeline_in_sec") or 0) for clip in clips]
        ends = [float(clip.get("timeline_out_sec") or 0) for clip in clips]
        start = min(starts)
        end = max(ends)
        if end <= start:
            continue
        name_super = text_layer.get("name_super")
        if name_super:
            effect_type = "lower_third"
            if isinstance(name_super, dict):
                text = {"main": name_super.get("text"), "subtitle": name_super.get("title")}
            else:
                text = {"main": name_super}
        else:
            main = text_layer.get("label") or text_layer.get("narrative")
            if not main:
                continue
            runtime_lower_third = any(
                isinstance(clip.get("text_overlay"), dict)
                and clip["text_overlay"].get("placement") == "lower_third"
                for clip in clips
            )
            if text_layer.get("label"):
                effect_type = "chapter_card"
            elif runtime_lower_third:
                effect_type = "lower_third"
            else:
                effect_type = "title_sequence"
            text = {"main": main, "subtitle": text_layer.get("subtitle")}
        recipe = TEXT_RECIPES[effect_type]
        items.append({
            "id": f"seg{segment_id}_{effect_type}",
            "segment": segment_id,
            "effect_type": effect_type,
            "backend": backend,
            "template": recipe["template"],
            "timing": {"start_sec": start, "duration_sec": round(end - start, 3)},
            "text": text,
            "style": {"motion": recipe["motion"], "safe_area": recipe["safe_area"]},
            "reason": text_layer.get("reason") or "canonical text layer",
        })
    return {
        "motion_graphics_version": 1,
        "contract_hash": contract_hash,
        "items": items,
    }


def _finding(level, field, message):
    return {"level": level, "field": field, "message": message}


def validate_motion_graphics_contract(contract):
    errors = []
    warnings = []
    if not isinstance(contract, dict):
        return {"ok": False, "errors": [_finding("error", "$", "contract must be object")], "warnings": []}
    if contract.get("motion_graphics_version") != 1:
        errors.append(_finding("error", "motion_graphics_version", "must be 1"))
    items = contract.get("items")
    if not isinstance(items, list) or not items:
        errors.append(_finding("error", "items", "must be non-empty list"))
        return {"ok": False, "errors": errors, "warnings": warnings}
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(_finding("error", f"items[{i}]", "item must be object"))
            continue
        if not item.get("id"):
            errors.append(_finding("error", f"items[{i}].id", "required"))
        effect_type = item.get("effect_type")
        if effect_type not in ALLOWED_EFFECT_TYPES:
            errors.append(_finding("error", f"items[{i}].effect_type", "unknown effect type"))
        backend = item.get("backend")
        if backend and backend not in ALLOWED_BACKENDS:
            errors.append(_finding("error", f"items[{i}].backend", "unknown backend"))
        timing = item.get("timing") or {}
        if not isinstance(timing, dict):
            errors.append(_finding("error", f"items[{i}].timing", "must be object"))
            continue
        if not isinstance(timing.get("start_sec"), (int, float)):
            errors.append(_finding("error", f"items[{i}].timing.start_sec", "required number"))
        duration = timing.get("duration_sec")
        if not isinstance(duration, (int, float)) or duration <= 0:
            errors.append(_finding("error", f"items[{i}].timing.duration_sec", "required positive number"))
        text = item.get("text") or {}
        if not isinstance(text, dict) or not any(text.get(k) for k in ("main", "subtitle", "names")):
            warnings.append(_finding("warn", f"items[{i}].text", "no visible text payload"))
        if not item.get("reason"):
            warnings.append(_finding("warn", f"items[{i}].reason", "missing effect reason"))
    return {"ok": not errors, "errors": errors, "warnings": warnings}


def _backend_for(item, policy):
    backend = item.get("backend") or policy.get("default_backend") or "ffmpeg_libass"
    if backend not in ALLOWED_BACKENDS:
        raise ValueError(f"unknown motion graphics backend: {backend}")
    if backend in HEAVY_BACKENDS and not policy.get("allow_heavy_backend"):
        raise ValueError(f"heavy backend requires allow_heavy_backend=true: {backend}")
    return backend


def build_motion_graphics_render_plan(contract, backend_policy=None):
    v = validate_motion_graphics_contract(contract)
    if not v["ok"]:
        raise ValueError(f"invalid motion graphics contract: {v['errors']}")
    policy = {
        "default_backend": "ffmpeg_libass",
        "fallback_backend": "ffmpeg_libass",
        "allow_heavy_backend": False,
        **(backend_policy or {}),
    }
    items = []
    for item in contract["items"]:
        timing = item["timing"]
        style = item.get("style") or {}
        backend = _backend_for(item, policy)
        output_mode = item.get("output_mode") or "overlay"
        items.append({
            "id": item["id"],
            "segment": item.get("segment"),
            "effect_type": item["effect_type"],
            "backend": backend,
            "fallback_backend": policy["fallback_backend"],
            "template": item.get("template"),
            "start_sec": float(timing["start_sec"]),
            "duration_sec": float(timing["duration_sec"]),
            "end_sec": float(timing["start_sec"]) + float(timing["duration_sec"]),
            "output_mode": output_mode,
            "text": item.get("text") or {},
            "style": {
                "motion": style.get("motion", "fade"),
                "safe_area": style.get("safe_area", "title_safe"),
                "font_role": style.get("font_role", "bold_cjk"),
                "color_role": style.get("color_role", "utility_clean"),
            },
            "reason": item.get("reason"),
        })
    return {
        "artifact_role": "motion_graphics_render_plan",
        "motion_graphics_render_plan_version": 1,
        "contract_hash": contract.get("contract_hash"),
        "backend_policy": policy,
        "items": items,
    }


def _write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return str(path)


def _ass_time(seconds):
    total = max(0.0, float(seconds or 0))
    hours = int(total // 3600)
    minutes = int((total % 3600) // 60)
    secs = total % 60
    return f"{hours}:{minutes:02d}:{secs:05.2f}"


def _ass_escape(value):
    return str(value or "").replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\n", r"\N")


def _ass_text(item):
    text = item.get("text") or {}
    parts = []
    if text.get("main"):
        parts.append(str(text["main"]))
    if text.get("subtitle"):
        parts.append(str(text["subtitle"]))
    names = text.get("names")
    if isinstance(names, list):
        parts.extend(str(name) for name in names if name)
    elif names:
        parts.append(str(names))
    return r"\N".join(_ass_escape(part) for part in parts)


def _write_ass_overlay(item, path):
    style = item.get("style") or {}
    safe_area = style.get("safe_area")
    effect_type = item.get("effect_type")
    alignment = 2 if effect_type == "lower_third" or safe_area == "lower_third" else 5
    margin_v = 90 if alignment == 2 else 60
    motion = style.get("motion", "fade")
    motion_tags = {
        "fade": r"{\fad(250,250)}",
        "fade_scale": r"{\an5\pos(960,540)\fscx92\fscy92\t(0,320,\fscx100\fscy100)\fad(220,260)}",
        "pop": r"{\an5\pos(960,540)\fscx72\fscy72\t(0,260,\fscx100\fscy100)\fad(100,200)}",
        "slide_up": r"{\an2\move(960,1160,960,930,0,320)\fad(120,220)}",
    }
    motion_tag = motion_tags.get(motion, "")
    content = (
        "\ufeff[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1920\n"
        "PlayResY: 1080\n"
        "WrapStyle: 2\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,Arial,64,&H00FFFFFF,&H000000FF,&H00101010,&H80000000,"
        f"-1,0,0,0,100,100,0,0,1,3,1,{alignment},100,100,{margin_v},1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        f"Dialogue: 0,{_ass_time(item['start_sec'])},{_ass_time(item['end_sec'])},"
        f"Default,,0,0,0,,{motion_tag}{_ass_text(item)}\n"
    )
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path)


def _write_html_overlay(item, path):
    """Write a deterministic transparent info-card animation."""
    text = item.get("text") or {}
    main = html.escape(str(text.get("main") or ""))
    subtitle = html.escape(str(text.get("subtitle") or ""))
    content = f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
html,body{{margin:0;width:1920px;height:1080px;overflow:hidden;background:transparent}}
.card{{position:absolute;left:140px;bottom:150px;min-width:620px;padding:45px 55px;
background:rgba(12,18,28,.86);border-left:8px solid #f0b44d;border-radius:12px;
color:white;font-family:Arial,sans-serif;opacity:0;transform:translateY(30px) scale(.96)}}
.main{{font-size:150px;font-weight:800;line-height:1}} .sub{{font-size:40px;margin-top:16px;opacity:.82}}
</style></head><body><div class="card" id="card"><div class="main">{main}</div>
<div class="sub">{subtitle}</div></div><script>
window.setProgress=(p)=>{{const q=Math.max(0,Math.min(1,p));const edge=Math.min(1,q*5,(1-q)*5);
const c=document.getElementById('card');c.style.opacity=edge;c.style.transform=`translateY(${{30*(1-edge)}}px) scale(${{.96+.04*edge}})`;}};
window.setProgress(0);
</script></body></html>"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path)


def _browser_executable():
    candidates = (
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    )
    return next((str(path) for path in candidates if path.exists()), None)


def _render_html_playwright_overlay(item, out_dir, fps=30):
    """Render deterministic HTML frames and encode an alpha overlay MOV."""
    item_dir = Path(out_dir)
    html_path = Path(_write_html_overlay(item, item_dir / f"{item['id']}.html"))
    frames_dir = item_dir / f"{item['id']}.frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    duration = float(item.get("duration_sec") or 0)
    frame_count = max(1, round(duration * fps))
    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    with sync_playwright() as playwright:
        launch_options = {"headless": True}
        executable = _browser_executable()
        if executable:
            launch_options["executable_path"] = executable
        browser = playwright.chromium.launch(**launch_options)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(html_path.resolve().as_uri())
        for index in range(frame_count):
            progress = index / max(1, frame_count - 1)
            page.evaluate("(p) => window.setProgress(p)", progress)
            page.screenshot(
                path=str(frames_dir / f"{index:06d}.png"),
                omit_background=True,
            )
        browser.close()

    from .platform_tools import resolve_ffmpeg  # noqa: PLC0415
    overlay_path = item_dir / f"{item['id']}.overlay.mov"
    command = [
        resolve_ffmpeg(), "-y", "-framerate", str(fps),
        "-i", str(frames_dir / "%06d.png"),
        "-c:v", "qtrle", "-pix_fmt", "argb", str(overlay_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0 or not overlay_path.exists():
        raise RuntimeError(f"html_playwright overlay encode failed: {result.stderr[-1200:]}")
    return {
        "path": str(overlay_path),
        "html_path": str(html_path),
        "frames_dir": str(frames_dir),
        "frame_count": frame_count,
        "fps": fps,
    }


def run_motion_graphics_render_plan(plan, out_dir):
    """Compile supported motion-graphics plan items into backend assets."""
    out_dir = Path(out_dir) / "motion_graphics"
    outputs = []
    for item in plan.get("items", []):
        backend = item.get("backend")
        if backend == "ffmpeg_libass":
            output_path = _write_ass_overlay(item, out_dir / f"{item['id']}.ass")
            status = "asset_ready"
            extra = {}
        elif backend == "html_playwright":
            try:
                rendered = _render_html_playwright_overlay(item, out_dir)
                output_path = rendered["path"]
                status = "asset_ready"
                extra = {key: value for key, value in rendered.items() if key != "path"}
            except Exception as exc:
                output_path = None
                status = "failed"
                extra = {"error": str(exc)}
        else:
            output_path = None
            status = "pending"
            extra = {}
        outputs.append({
            "effect_id": item.get("id"),
            "segment": item.get("segment"),
            "effect_type": item.get("effect_type"),
            "backend": backend,
            "status": status,
            "path": output_path,
            "start_sec": item.get("start_sec"),
            "duration_sec": item.get("duration_sec"),
            "motion": (item.get("style") or {}).get("motion"),
            **extra,
        })
    return outputs


def _subtitles_filter(path):
    escaped = str(Path(path).resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    return f"subtitles='{escaped}'"


def composite_ffmpeg_libass_outputs(video_path, render_outputs, output_path=None):
    """Composite ready ASS assets into a video and mark only successful outputs."""
    video_path = Path(video_path)
    ready = [
        output for output in (render_outputs or [])
        if output.get("backend") == "ffmpeg_libass"
        and output.get("status") == "asset_ready"
        and output.get("path")
    ]
    if not ready:
        return {"ok": True, "status": "skipped", "command": None, "outputs": render_outputs}
    if not video_path.exists():
        return {"ok": False, "status": "missing_input", "command": None, "outputs": render_outputs}
    final_path = Path(output_path) if output_path else video_path
    temp_path = final_path.with_name(f"{final_path.stem}.effects-tmp{final_path.suffix}")
    from .platform_tools import resolve_ffmpeg  # noqa: PLC0415
    command = [
        resolve_ffmpeg(),
        "-y",
        "-i", str(video_path),
        "-vf", ",".join(_subtitles_filter(output["path"]) for output in ready),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        str(temp_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0 or not temp_path.exists():
        return {
            "ok": False,
            "status": "failed",
            "command": command,
            "stderr": result.stderr,
            "outputs": render_outputs,
        }
    if final_path.exists() and final_path != video_path:
        final_path.unlink()
    temp_path.replace(final_path)
    for output in ready:
        output["status"] = "composited"
        output["composited_video"] = str(final_path)
    return {
        "ok": True,
        "status": "composited",
        "command": command,
        "output": str(final_path),
        "outputs": render_outputs,
    }


def composite_html_playwright_outputs(video_path, render_outputs, output_path=None):
    """Composite ready alpha overlay videos at their declared start times."""
    video_path = Path(video_path)
    ready = [
        output for output in (render_outputs or [])
        if output.get("backend") == "html_playwright"
        and output.get("status") == "asset_ready"
        and output.get("path")
        and Path(output["path"]).exists()
    ]
    if not ready:
        return {"ok": True, "status": "skipped", "command": None, "outputs": render_outputs}
    if not video_path.exists():
        return {"ok": False, "status": "missing_input", "command": None, "outputs": render_outputs}
    final_path = Path(output_path) if output_path else video_path
    temp_path = final_path.with_name(f"{final_path.stem}.html-effects-tmp{final_path.suffix}")
    from .platform_tools import resolve_ffmpeg  # noqa: PLC0415
    command = [resolve_ffmpeg(), "-y", "-i", str(video_path)]
    for output in ready:
        command += ["-i", str(output["path"])]
    filters = []
    current = "[0:v]"
    for index, output in enumerate(ready, start=1):
        overlay_label = f"[ov{index}]"
        result_label = f"[v{index}]"
        filters.append(f"[{index}:v]setpts=PTS+{float(output.get('start_sec') or 0):.3f}/TB{overlay_label}")
        filters.append(f"{current}{overlay_label}overlay=eof_action=pass{result_label}")
        current = result_label
    command += [
        "-filter_complex", ";".join(filters),
        "-map", current, "-map", "0:a?", "-c:v", "libx264", "-preset", "medium",
        "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "copy", str(temp_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0 or not temp_path.exists():
        return {
            "ok": False, "status": "failed", "command": command,
            "stderr": result.stderr, "outputs": render_outputs,
        }
    if final_path.exists() and final_path != video_path:
        final_path.unlink()
    temp_path.replace(final_path)
    for output in ready:
        output["status"] = "composited"
        output["composited_video"] = str(final_path)
    return {
        "ok": True, "status": "composited", "command": command,
        "output": str(final_path), "outputs": render_outputs,
    }


def composite_motion_graphics_outputs(video_path, render_outputs, output_path=None):
    """Composite all supported safe backends in deterministic backend order."""
    libass = composite_ffmpeg_libass_outputs(video_path, render_outputs, output_path=output_path)
    if not libass.get("ok"):
        return {"ok": False, "status": "failed", "steps": [libass], "outputs": render_outputs}
    html_result = composite_html_playwright_outputs(video_path, render_outputs, output_path=output_path)
    steps = [libass, html_result]
    ok = all(step.get("ok") for step in steps)
    status = "composited" if any(step.get("status") == "composited" for step in steps) else "skipped"
    return {"ok": ok, "status": status if ok else "failed", "steps": steps, "outputs": render_outputs}


def write_motion_graphics_artifacts(contract, out_dir, backend_policy=None):
    out_dir = Path(out_dir)
    v = validate_motion_graphics_contract(contract)
    if not v["ok"]:
        return {"ok": False, "errors": v["errors"], "warnings": v["warnings"]}
    plan = build_motion_graphics_render_plan(contract, backend_policy=backend_policy)
    contract_path = _write_json(out_dir / "motion_graphics_contract.json", contract)
    plan_path = _write_json(out_dir / "motion_graphics_render_plan.json", plan)
    render_outputs = run_motion_graphics_render_plan(plan, out_dir)
    manifest = {
        "artifact_role": "motion_graphics_manifest",
        "motion_graphics_manifest_version": 1,
        "contract_hash": contract.get("contract_hash"),
        "motion_graphics_contract": contract_path,
        "motion_graphics_render_plan": plan_path,
        "render_outputs": render_outputs,
    }
    manifest_path = _write_json(out_dir / "motion_graphics_manifest.json", manifest)
    return {
        "ok": True,
        "errors": [],
        "warnings": v["warnings"],
        "contract": contract_path,
        "render_plan": plan_path,
        "manifest": manifest_path,
    }
