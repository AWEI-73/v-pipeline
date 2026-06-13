"""Reviewable jump-cut planning from mapped speech and silence runs."""
from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path


def build_jumpcut_plan(material_map, *, min_remove_silence_sec=1.0):
    segments = []
    for index, run in enumerate(material_map.get("speech") or []):
        start = float(run.get("start") or 0)
        end = float(run.get("end") or 0)
        duration = max(0.0, end - start)
        remove = run.get("kind") == "silence" and duration >= float(min_remove_silence_sec)
        segments.append({
            "index": index,
            "start": start,
            "end": end,
            "duration": duration,
            "kind": run.get("kind"),
            "text": run.get("text"),
            "action": "remove" if remove else "keep",
            "reason": "long_silence" if remove else "speech_or_short_pause",
        })
    return {
        "artifact_role": "jumpcut_plan",
        "version": 1,
        "asset_id": material_map.get("asset_id"),
        "source": material_map.get("source"),
        "segments": segments,
        "requires_review": any(item["action"] == "remove" for item in segments),
        "approved": False,
    }


def apply_jumpcut_verdict(plan, verdict):
    result = copy.deepcopy(plan)
    for patch in verdict.get("patches") or []:
        index = patch.get("index")
        if isinstance(index, int) and 0 <= index < len(result.get("segments") or []):
            if patch.get("action") in ("keep", "remove"):
                result["segments"][index]["action"] = patch["action"]
                result["segments"][index]["reason"] = "agent_patch"
    decision = verdict.get("decision")
    result["approved"] = decision == "accept"
    result["review_lineage"] = {
        "decision": decision,
        "reviewer": verdict.get("reviewer") or "agent",
        "notes": verdict.get("notes"),
    }
    return result


def write_jumpcut_plan(material_map, out_path, **kwargs):
    result = build_jumpcut_plan(material_map, **kwargs)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def apply_jumpcut(plan, output_path, *, runner=None):
    """Apply an approved jump-cut plan and return processed-material lineage."""
    if not plan.get("approved"):
        raise ValueError("jumpcut plan must be approved before apply")
    kept = [
        [float(item.get("start") or 0), float(item.get("end") or 0)]
        for item in plan.get("segments") or [] if item.get("action") == "keep"
    ]
    if not kept:
        raise ValueError("jumpcut plan has no kept ranges")
    source = plan.get("source")
    filters = []
    concat_inputs = []
    for index, (start, end) in enumerate(kept):
        filters.extend([
            f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{index}]",
            f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{index}]",
        ])
        concat_inputs.append(f"[v{index}][a{index}]")
    filters.append("".join(concat_inputs) + f"concat=n={len(kept)}:v=1:a=1[v][a]")
    command = [
        "ffmpeg", "-y", "-i", str(source), "-filter_complex", ";".join(filters),
        "-map", "[v]", "-map", "[a]", str(output_path),
    ]
    if runner:
        runner(command)
    else:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(command, check=True)
    return {
        "ok": True,
        "output": str(output_path),
        "lineage": {
            "source": source,
            "operation": "jumpcut_apply",
            "kept_ranges": kept,
            "review": plan.get("review_lineage"),
        },
    }
