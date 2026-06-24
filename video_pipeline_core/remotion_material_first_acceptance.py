"""Material-first MemoryPhotoWall boundary acceptance.

This harness verifies the narrow Brownfield bridge:

material wall reviewed keyframes -> effect collage refs -> MemoryPhotoWall
effect_build_spec -> prompt pack -> worker review -> effect render verification.

It never writes final.mp4 and does not composite a video.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping
from html import escape

from .effect_collage_refs import write_collage_media_refs
from .effect_render_verification import write_effect_render_verification
from .effect_revision import ADAPTER_ROUTE
from .remotion_acceptance import accept_all_review_items
from .remotion_effects import (
    build_remotion_prompt_pack,
    run_remotion_worker_smoke,
    validate_remotion_worker_outputs,
)


def _write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _load_json(path: str | Path) -> Any:
    with Path(path).open(encoding="utf-8-sig") as f:
        return json.load(f)


def _media_href(ref: Mapping[str, Any]) -> str:
    raw = str(ref.get("path") or ref.get("src") or "")
    return raw


def _write_visual_probe(run_dir: Path, refs: list[dict[str, Any]],
                        effect: Mapping[str, Any]) -> dict[str, str]:
    """Write review-only visual evidence for the MemoryPhotoWall contract.

    This is not a Remotion render. It is a small deterministic probe that lets
    humans verify whether the structured parameters and reviewed refs would form
    a slow one-by-one memory wall before promoting the route to a real renderer.
    """
    spec = ((effect.get("prompt_parameters") or {}).get("effect_build_spec") or {})
    duration = float(spec.get("duration_sec") or effect.get("duration_sec") or 8.0)
    reveal_interval = float(spec.get("reveal_interval_sec") or 1.2)
    frame_count = min(4, max(1, len(refs)))
    frame_width = 420
    frame_height = 236
    gap = 22
    sheet_width = frame_count * frame_width + (frame_count + 1) * gap
    sheet_height = 360

    def _card_svg(ref: Mapping[str, Any], x: int, y: int, w: int, h: int) -> str:
        label = escape(str(ref.get("label") or ref.get("ref_id") or "reviewed ref"))
        href = escape(_media_href(ref), quote=True)
        image = (
            f'<image href="{href}" x="{x}" y="{y}" width="{w}" height="{h}" '
            'preserveAspectRatio="xMidYMid slice" />'
        ) if href else ""
        return "\n".join([
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#20242c" stroke="#f8f2df" stroke-width="2"/>',
            image,
            f'<rect x="{x}" y="{y + h - 32}" width="{w}" height="32" fill="rgba(0,0,0,.56)"/>',
            f'<text x="{x + 12}" y="{y + h - 11}" fill="#fff8dc" font-size="14" font-family="Arial">{label}</text>',
        ])

    frames = []
    for idx in range(frame_count):
        x0 = gap + idx * (frame_width + gap)
        visible = refs[:idx + 1]
        cards = []
        for card_idx, ref in enumerate(visible[:3]):
            cx = x0 + 18 + card_idx * 112
            cy = 74 + (card_idx % 2) * 28
            cards.append(_card_svg(ref, cx, cy, 138, 82))
        frames.append("\n".join([
            f'<g id="frame-{idx + 1}">',
            f'<rect x="{x0}" y="44" width="{frame_width}" height="{frame_height}" rx="10" fill="#111318" stroke="#3b4252"/>',
            f'<text x="{x0 + 18}" y="78" fill="#ffd36a" font-size="22" font-weight="700" font-family="Arial">Frame {idx + 1}</text>',
            f'<text x="{x0 + 18}" y="104" fill="#cdd3df" font-size="14" font-family="Arial">t={round(idx * reveal_interval, 2)}s / reveal={escape(str(spec.get("reveal_mode") or "one_by_one"))}</text>',
            *cards,
            "</g>",
        ]))

    contact_sheet = run_dir / "remotion_contact_sheet.svg"
    contact_sheet.write_text("\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{sheet_width}" height="{sheet_height}" viewBox="0 0 {sheet_width} {sheet_height}">',
        '<rect width="100%" height="100%" fill="#090b10"/>',
        '<text x="24" y="28" fill="#ffffff" font-size="22" font-weight="800" font-family="Arial">MemoryPhotoWall contact sheet</text>',
        f'<text x="340" y="28" fill="#9aa4b5" font-size="14" font-family="Arial">duration={duration}s pacing={escape(str(spec.get("pacing") or ""))} density={escape(str(spec.get("density") or ""))}</text>',
        *frames,
        '</svg>',
    ]), encoding="utf-8")

    cards_html = "\n".join([
        f'<figure><img src="{escape(_media_href(ref), quote=True)}" alt="{escape(str(ref.get("ref_id") or ""))}"><figcaption>{escape(str(ref.get("label") or ref.get("ref_id") or ""))}</figcaption></figure>'
        for ref in refs[:6]
    ])
    preview = run_dir / "remotion_visual_probe.html"
    preview.write_text(f"""<!doctype html>
<html lang="zh-Hant">
<meta charset="utf-8">
<title>MemoryPhotoWall visual probe</title>
<style>
body {{ margin: 0; background: #090b10; color: #fff; font-family: "Microsoft JhengHei", Arial, sans-serif; }}
.stage {{ width: 1280px; height: 720px; position: relative; overflow: hidden; background: radial-gradient(circle at 32% 22%, rgba(255,211,106,.18), transparent 36%), linear-gradient(135deg,#11151d,#252a33 52%,#090b10); }}
.title {{ position: absolute; left: 48px; bottom: 44px; color: #ffd36a; font-size: 34px; font-weight: 900; }}
.wall {{ position: absolute; inset: 80px 80px 110px; transform: scale(1.02); }}
figure {{ position: relative; display: inline-block; width: 310px; height: 180px; margin: 12px; border: 2px solid rgba(255,255,255,.82); box-shadow: 0 22px 52px rgba(0,0,0,.55); overflow: hidden; background: #1d222c; animation: reveal {duration / max(1, len(refs)):.2f}s ease-out both; }}
figure:nth-child(2) {{ animation-delay: {reveal_interval:.2f}s; transform: rotate(1.5deg); }}
figure:nth-child(3) {{ animation-delay: {reveal_interval * 2:.2f}s; transform: rotate(-1deg); }}
figure:nth-child(4) {{ animation-delay: {reveal_interval * 3:.2f}s; }}
img {{ width: 100%; height: 100%; object-fit: cover; filter: saturate(1.03) contrast(1.04) brightness(1.08); }}
figcaption {{ position: absolute; left: 8px; bottom: 8px; padding: 4px 8px; background: rgba(0,0,0,.52); border-radius: 4px; font-size: 13px; }}
@keyframes reveal {{ from {{ opacity: 0; transform: translateY(26px) scale(.94); }} to {{ opacity: 1; transform: translateY(0) scale(1); }} }}
</style>
<main class="stage">
  <section class="wall">{cards_html}</section>
  <div class="title">MemoryPhotoWall / {escape(str(spec.get("story_function") or "emotional_setup"))}</div>
</main>
</html>
""", encoding="utf-8")
    return {
        "preview": str(preview),
        "contact_sheet": str(contact_sheet),
    }


def _memory_effect(collage_refs: list[dict[str, Any]], *, duration_sec: float) -> dict[str, Any]:
    return {
        "effect_id": "fx_material_memory_wall_01",
        "role": "title_card",
        "intent": "open the material-first training recap with a slow emotional reviewed-material wall",
        "intensity": "medium",
        "target": {"beat_id": "beat_opening_memory", "segment_id": "opening_memory"},
        "visual_language": ["memory photo wall", "slow emotional reveal", "reviewed material refs"],
        "required_for_story": True,
        "must_preserve_proof": True,
        "allowed_backends": ["remotion_preview", "remotion_render"],
        "fallback": "static contact sheet hold",
        "duration_sec": duration_sec,
        "template_id": "memory_photo_wall",
        "display_text": "Training recap",
        "subtitle_text": "Reviewed material memory wall",
        "prompt_parameters": {
            "effect_build_spec": {
                "component": "MemoryPhotoWall",
                "duration_sec": duration_sec,
                "story_function": "emotional_setup",
                "pacing": "slow",
                "density": "low",
                "reveal_mode": "one_by_one",
                "reveal_interval_sec": 1.2,
                "hold_after_full_wall_sec": 2.0,
                "camera_motion": "slow_push_in",
                "caption_mode": "minimal",
                "accent_light": "soft_warm",
                "material_refs": collage_refs,
            },
        },
    }


def _write_report(run_dir: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    report = dict(payload)
    _write_json(run_dir / "remotion_material_first_memory_acceptance_report.json", report)
    return report


def run_material_first_memory_acceptance(run_dir: str | Path, *,
                                         project_map: str | Path,
                                         wall_verdict: str | Path,
                                         wall_request: str | Path,
                                         max_refs: int = 6,
                                         duration_sec: float = 8.0) -> dict[str, Any]:
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    artifacts: dict[str, str] = {}

    try:
        collage_refs_path = run_dir / "effect_collage_media_refs.json"
        collage_refs = write_collage_media_refs(
            project_map,
            collage_refs_path,
            material_wall_review_verdict_path=wall_verdict,
            material_wall_request_path=wall_request,
            max_refs=max_refs,
        )
        artifacts["effect_collage_media_refs"] = str(collage_refs_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _write_report(run_dir, {
            "artifact_role": "remotion_material_first_memory_acceptance_report",
            "version": 1,
            "ok": False,
            "failed_stage": "effect_collage_refs",
            "errors": [str(exc)],
            "next_action": "repair_reviewed_material_refs",
            "artifacts": artifacts,
        })

    refs = list(collage_refs.get("collage_media_refs") or [])
    if not refs:
        return _write_report(run_dir, {
            "artifact_role": "remotion_material_first_memory_acceptance_report",
            "version": 1,
            "ok": False,
            "failed_stage": "effect_collage_refs",
            "errors": ["no reviewed material refs available for MemoryPhotoWall"],
            "next_action": "provide_material_wall_keyframes_or_reviewed_stills",
            "artifacts": artifacts,
        })

    memory_effect = _memory_effect(refs, duration_sec=duration_sec)
    effect_intent_plan = {
        "artifact_role": "effect_intent_plan",
        "version": 1,
        "effects": [memory_effect],
    }
    effect_revision_request = {
        "artifact_role": "effect_revision_request",
        "version": 1,
        "status": "pending",
        "summary": {"request_count": 1},
        "requests": [{
            "request_id": "fxrev_material_memory_wall_01",
            "effect_id": "fx_material_memory_wall_01_gap",
            "source_effect_id": "fx_material_memory_wall_01",
            "segment": "opening_memory",
            "operation": "external_effect",
            "route": ADAPTER_ROUTE,
            "reason": "material-first memory wall requires reviewable Remotion preview from reviewed material refs",
            "status": "pending",
        }],
    }
    timeline_build = {
        "artifact_role": "timeline_build",
        "version": 1,
        "duration_sec": max(duration_sec, 12.0),
        "clips": [{"segment": "opening_memory", "timeline_in_sec": 0.0, "timeline_out_sec": duration_sec}],
    }
    effect_intent_path = _write_json(run_dir / "effect_intent_plan.json", effect_intent_plan)
    revision_path = _write_json(run_dir / "effect_revision_request.json", effect_revision_request)
    timeline_path = _write_json(run_dir / "timeline_build.json", timeline_build)
    artifacts.update({
        "effect_intent_plan": str(effect_intent_path),
        "effect_revision_request": str(revision_path),
        "timeline_build": str(timeline_path),
    })

    pack = build_remotion_prompt_pack(
        effect_revision_request,
        effect_intent_plan,
        timeline=timeline_build,
        output_dir=str(run_dir / "remotion_effects"),
        collage_media_refs=collage_refs,
    )
    prompt_pack_path = _write_json(run_dir / "remotion_prompt_pack.json", pack)
    artifacts["remotion_prompt_pack"] = str(prompt_pack_path)

    worker_outputs = run_remotion_worker_smoke(pack, run_dir / "remotion_effects")
    visual_probe = _write_visual_probe(run_dir, refs, memory_effect)
    artifacts["remotion_visual_probe"] = visual_probe["preview"]
    artifacts["remotion_contact_sheet"] = visual_probe["contact_sheet"]
    for job in worker_outputs.get("jobs") or []:
        evidence_refs = list(job.get("evidence_refs") or [])
        evidence_refs.extend([visual_probe["contact_sheet"], visual_probe["preview"]])
        job["evidence_refs"] = evidence_refs
    worker_outputs_path = _write_json(run_dir / "remotion_worker_outputs.json", worker_outputs)
    artifacts["remotion_worker_outputs"] = str(worker_outputs_path)

    validation = validate_remotion_worker_outputs(worker_outputs, pack)
    if not validation.get("ok"):
        return _write_report(run_dir, {
            "artifact_role": "remotion_material_first_memory_acceptance_report",
            "version": 1,
            "ok": False,
            "failed_stage": "remotion_worker_outputs",
            "errors": validation.get("errors") or [],
            "next_action": "repair_remotion_worker_outputs",
            "artifacts": artifacts,
        })

    pending_review_path = _write_json(run_dir / "remotion_effect_review.pending.json", validation["review_artifact"])
    artifacts["remotion_effect_review_pending"] = str(pending_review_path)
    review = accept_all_review_items(
        validation["review_artifact"],
        reviewer="remotion-material-first-memory-acceptance",
        reason="bounded dry-run artifact chain passed and review evidence exists",
    )
    review_path = _write_json(run_dir / "remotion_effect_review.json", review)
    artifacts["remotion_effect_review"] = str(review_path)

    verification = write_effect_render_verification(
        effect_intent_path,
        review_path,
        run_dir / "effect_render_verification.json",
        root=run_dir,
    )
    artifacts["effect_render_verification"] = str(run_dir / "effect_render_verification.json")

    report = {
        "artifact_role": "remotion_material_first_memory_acceptance_report",
        "version": 1,
        "ok": verification.get("pass") is True,
        "failed_stage": None if verification.get("pass") is True else "effect_render_verification",
        "next_action": "ready_for_human_effect_review_or_pipeline_promotion"
        if verification.get("pass") is True else "repair_effect_render_verification",
        "summary": {
            "selected_ref_count": len(refs),
            "evidence_kinds": sorted({str(ref.get("evidence_kind") or "") for ref in refs if ref.get("evidence_kind")}),
            "build_component": "MemoryPhotoWall",
            "prompt_pack_job_count": pack.get("summary", {}).get("job_count", 0),
            "rendered_count": worker_outputs.get("summary", {}).get("rendered_count", 0),
            "verification": verification.get("summary", {}),
            "canonical_final_exists": (run_dir / "final.mp4").exists(),
            "visual_probe": {
                "preview": Path(visual_probe["preview"]).name,
                "contact_sheet": Path(visual_probe["contact_sheet"]).name,
            },
        },
        "artifacts": artifacts,
        "review_notes": [
            "dry-run worker only; no visual quality render is claimed",
            "no final.mp4 or canonical renderer output is written",
        ],
    }
    return _write_report(run_dir, report)
