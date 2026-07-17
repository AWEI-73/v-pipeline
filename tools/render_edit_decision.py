"""Public Stage 6 adapter for the repo-owned edit-decision renderer."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.edit_decision_renderer import render_edit_decision  # noqa: E402


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path, label: str) -> Any:
    if not path.is_file():
        raise ValueError(f"{label} does not exist: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid UTF-8 JSON: {path}") from exc


def _resolve_source(raw: Any, accepted_json: Path) -> Path:
    source = Path(str(raw or ""))
    if not source.is_absolute():
        source = accepted_json.parent / source
    return source.resolve()


def _accepted_inputs(payload: Any, accepted_json: Path) -> tuple[list[dict[str, Any]], dict[str, str]]:
    if isinstance(payload, Mapping):
        payload = payload.get("accepted_inputs")
    if not isinstance(payload, list):
        raise ValueError("accepted inputs JSON must be a list or an object with accepted_inputs")

    inputs: list[dict[str, Any]] = []
    source_hashes: dict[str, str] = {}
    for index, raw in enumerate(payload):
        if not isinstance(raw, Mapping):
            raise ValueError(f"accepted input {index} is not an object")
        item = dict(raw)
        if item.get("accepted") is not True:
            raise ValueError(f"accepted input {index} is not accepted")
        asset_id = str(item.get("asset_id") or "").strip()
        source = _resolve_source(item.get("source_path"), accepted_json)
        if not asset_id or not source.is_file():
            raise ValueError(f"accepted input {index} lacks asset_id or usable source_path")
        source_hash = _sha256(source)
        declared_hash = item.get("source_sha256")
        if declared_hash is not None:
            declared_hash = str(declared_hash).lower()
            if len(declared_hash) != 64 or any(char not in "0123456789abcdef" for char in declared_hash):
                raise ValueError(f"accepted input {index} source_sha256 is not a SHA-256 digest")
            if declared_hash != source_hash:
                raise ValueError(f"accepted input {index} source_sha256 does not match source_path")
        item["source_path"] = str(source)
        item["source_sha256"] = source_hash
        inputs.append(item)
        source_hashes[asset_id] = source_hash
    return inputs, source_hashes


def _timeline_from_decision(decision: Mapping[str, Any], asset_kinds: Mapping[str, str]) -> dict[str, Any]:
    settings = decision.get("settings")
    cuts = decision.get("cuts")
    if not isinstance(settings, Mapping) or not isinstance(cuts, list) or not cuts:
        raise ValueError("decision must contain settings and a non-empty cuts list")

    clips: list[dict[str, Any]] = []
    cursor = 0.0
    for index, raw in enumerate(cuts):
        if not isinstance(raw, Mapping):
            raise ValueError(f"decision cut {index} is not an object")
        clip = dict(raw)
        clip.setdefault("id", f"clip_{index + 1:03d}")
        asset_id = str(clip.get("asset_id") or "")
        if not clip.get("source_type") and asset_id in asset_kinds:
            clip["source_type"] = asset_kinds[asset_id]
        timeline_in = clip.get("timeline_in_sec", cursor)
        duration = clip.get("target_duration_sec")
        if duration is None:
            duration = float(clip.get("out_seconds", 0) or 0) - float(clip.get("in_seconds", 0) or 0)
        timeline_out = clip.get("timeline_out_sec", float(timeline_in) + float(duration or 0))
        clip["timeline_in_sec"] = timeline_in
        clip["timeline_out_sec"] = timeline_out
        clips.append(clip)
        cursor = float(timeline_out)

    return {
        "artifact_role": "timeline_view",
        "settings": dict(settings),
        "clips": clips,
        "overlays": [dict(item) for item in (decision.get("overlays") or [])],
        "transitions": [dict(item) for item in (decision.get("transitions") or [])],
    }


def _write_source_hashes(run_dir: Path, source_hashes: Mapping[str, str]) -> None:
    manifest_path = run_dir / "render_input_manifest.json"
    payload = _load_json(manifest_path, "renderer input manifest")
    if not isinstance(payload, Mapping):
        raise ValueError("renderer input manifest must be an object")
    updated = dict(payload)
    accepted = []
    for raw in payload.get("accepted_inputs") or []:
        if not isinstance(raw, Mapping):
            raise ValueError("renderer input manifest contains an invalid accepted input")
        item = dict(raw)
        asset_id = str(item.get("asset_id") or "")
        if asset_id in source_hashes:
            item["source_sha256"] = source_hashes[asset_id]
        accepted.append(item)
    updated["accepted_inputs"] = accepted
    manifest_path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a canonical edit-decision plan through the repo-owned renderer.")
    parser.add_argument("--decision", required=True, help="Path to edit_decision_plan.json.")
    parser.add_argument("--accepted-inputs", required=True, help="Path to accepted inputs JSON.")
    parser.add_argument("--run", required=True, help="Output run directory.")
    parser.add_argument("--json", action="store_true", help="Print a JSON summary.")
    args = parser.parse_args(argv)

    run_dir = Path(args.run).resolve()
    try:
        decision_payload = _load_json(Path(args.decision).resolve(), "edit decision")
        if not isinstance(decision_payload, Mapping):
            raise ValueError("edit decision JSON must be an object")
        accepted_path = Path(args.accepted_inputs).resolve()
        accepted_payload = _load_json(accepted_path, "accepted inputs")
        accepted_inputs, source_hashes = _accepted_inputs(accepted_payload, accepted_path)
        asset_kinds = {str(item["asset_id"]): str(item.get("kind") or "") for item in accepted_inputs}
        timeline = _timeline_from_decision(decision_payload, asset_kinds)
        result = render_edit_decision(
            decision_payload,
            timeline,
            run_dir=run_dir,
            accepted_inputs=accepted_inputs,
        )
        _write_source_hashes(run_dir, source_hashes)
        summary = {
            "ok": True,
            "rendered": True,
            "run_dir": str(run_dir),
            "final_mp4": str(run_dir / "final.mp4"),
            "outputs": result.get("outputs", {}),
        }
    except Exception as exc:
        summary = {
            "ok": False,
            "rendered": False,
            "failed_stage": "render_edit_decision",
            "error": str(exc),
        }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            "render_edit_decision "
            f"ok={str(summary.get('ok')).lower()} "
            f"rendered={str(summary.get('rendered')).lower()}"
        )
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
