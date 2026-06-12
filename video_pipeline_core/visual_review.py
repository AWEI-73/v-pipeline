"""Artifact contracts for the agent-as-visual-judge wait gate."""
import json
from pathlib import Path


def build_request(clips):
    clips = list(clips or [])
    template = []
    for clip in clips:
        template.append({
            "segment": clip.get("segment"),
            "action": None,
            "accept": None,
            "picked_windows": [],
            "patch": None,
            "reject_reason": None,
            "notes": None,
        })
    return {
        "artifact_role": "visual_review_request",
        "visual_review_request_version": 1,
        "next_action": "await_visual_review",
        "clips": clips,
        "verdict_template": {"clips": template},
    }


def write_request(clips, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_request(clips)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def verdict_by_segment(verdict):
    if not isinstance(verdict, dict) or not isinstance(verdict.get("clips"), list):
        raise ValueError("visual review verdict must contain clips list")
    indexed = {}
    for clip in verdict["clips"]:
        segment = clip.get("segment")
        if not isinstance(segment, int):
            raise ValueError("visual review verdict clip requires integer segment")
        action = clip.get("action")
        if action is None:
            accept = clip.get("accept")
            if not isinstance(accept, bool):
                raise ValueError(f"visual review verdict seg{segment} requires action or boolean accept")
            action = "accept" if accept else "reject"
        if action not in ("accept", "reject", "needs_patch"):
            raise ValueError(f"visual review verdict seg{segment} has invalid action")
        normalized = dict(clip)
        normalized["action"] = action
        normalized["accept"] = action in ("accept", "needs_patch")
        patch = normalized.get("patch")
        if action == "needs_patch":
            if not isinstance(patch, dict) or patch.get("type") not in ("window", "crop", "treatment"):
                raise ValueError(f"visual review verdict seg{segment} has invalid patch")
            if not isinstance(patch.get("hint"), dict):
                raise ValueError(f"visual review verdict seg{segment} patch requires hint")
        windows = normalized.get("picked_windows") or []
        if action == "needs_patch" and patch["type"] == "window" and not windows:
            hint = patch["hint"]
            windows = [{"start": hint.get("start"), "end": hint.get("end")}]
            normalized["picked_windows"] = windows
        if normalized["accept"] and not windows:
            raise ValueError(f"visual review verdict seg{segment} accepted without picked_windows")
        for window in windows:
            start = window.get("start")
            end = window.get("end")
            if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or end <= start:
                raise ValueError(f"visual review verdict seg{segment} has invalid picked window")
        indexed[segment] = normalized
    return indexed


def load_verdict(path):
    path = Path(path)
    if not path.exists():
        return {}
    return verdict_by_segment(json.loads(path.read_text(encoding="utf-8")))
