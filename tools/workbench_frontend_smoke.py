#!/usr/bin/env python
"""Smoke-test the Workbench frontend/API contract.

This is intentionally lighter than a visual browser test. It exercises the same
HTTP surface the browser uses and verifies that draft edits do not mutate
canonical artifacts.

CLI::

    python tools/workbench_frontend_smoke.py --artifact-root .tmp/srp_real67_fuller_replay
"""
from __future__ import annotations

import argparse
import hashlib
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

try:  # script and package modes
    from tools.workbench_server import WorkbenchHandler
except ImportError:  # pragma: no cover
    from workbench_server import WorkbenchHandler


CANONICAL_CANDIDATES = (
    "timeline.json",
    "project_material_map.json",
    "material_needs.json",
    "final.mp4",
    "segment_contract.json",
)


class SmokeError(RuntimeError):
    """Raised when the Workbench smoke flow fails."""


def _read_json_url(url: str) -> Any:
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SmokeError(f"GET {url} failed: {exc.code} {body}") from exc
    except (OSError, ValueError) as exc:
        raise SmokeError(f"GET {url} failed: {exc}") from exc


def _read_text_url(url: str) -> str:
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SmokeError(f"GET {url} failed: {exc.code} {body}") from exc
    except OSError as exc:
        raise SmokeError(f"GET {url} failed: {exc}") from exc


def _post_json_url(url: str, payload: Any) -> Any:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SmokeError(f"POST {url} failed: {exc.code} {body}") from exc
    except (OSError, ValueError) as exc:
        raise SmokeError(f"POST {url} failed: {exc}") from exc


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_hashes(root: Path, names: Iterable[str] = CANONICAL_CANDIDATES) -> Dict[str, str]:
    """Return hashes for canonical artifacts present under ``root``."""
    hashes: Dict[str, str] = {}
    for name in names:
        path = root / name
        if path.is_file():
            hashes[name] = _sha256(path)
    return hashes


def build_duration_patch(preview: Dict[str, Any]) -> Dict[str, Any]:
    """Build a minimal valid timeline patch for the first real preview clip."""
    clips = preview.get("clips")
    if not isinstance(clips, list):
        raise SmokeError("preview_timeline has no clips list")
    clip = next((c for c in clips if isinstance(c, dict) and c.get("status") != "gap"), None)
    if clip is None:
        raise SmokeError("preview_timeline has no editable clip")
    slot_index = clip.get("slot_index")
    duration = clip.get("duration_sec", clip.get("slot_dur"))
    if not isinstance(slot_index, int):
        raise SmokeError("first editable clip has no integer slot_index")
    if not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration <= 0:
        raise SmokeError("first editable clip has no positive duration")
    # Keep the duration unchanged. The smoke is about endpoint integrity and
    # canonical write protection, not about changing editorial timing.
    duration = round(float(duration), 3)
    return {
        "artifact_role": "timeline_patch",
        "version": 1,
        "base_timeline_ref": "timeline.json",
        "patches": [{
            "op": "set_duration",
            "slot_index": slot_index,
            "after": {"duration_sec": duration},
        }],
        "diagnostics": [],
    }


def build_replacement_patch(preview: Dict[str, Any]) -> Dict[str, Any]:
    """Build a replace_clip patch using preview material_assets.

    This verifies the material-browser handoff path without requiring browser
    drag/drop automation. The patch remains draft-only and is resolved again by
    the Python server from project_material_map.
    """
    clips = preview.get("clips")
    assets = preview.get("material_assets")
    if not isinstance(clips, list) or not isinstance(assets, list):
        raise SmokeError("preview_timeline missing clips or material_assets")
    clip = next((c for c in clips if isinstance(c, dict) and c.get("status") != "gap"), None)
    if clip is None or not isinstance(clip.get("slot_index"), int):
        raise SmokeError("preview_timeline has no editable clip")
    current_asset = clip.get("asset_id")
    current_source = clip.get("source_path")
    candidates = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        scenes = asset.get("scenes")
        if not asset.get("asset_id") or not isinstance(scenes, list) or not scenes:
            continue
        if current_asset is not None and asset.get("asset_id") == current_asset:
            continue
        if current_source and asset.get("source_path") == current_source:
            continue
        candidates.append(asset)
    if not candidates:
        raise SmokeError("preview_timeline has no replacement material candidate")
    asset = candidates[0]
    scene = asset["scenes"][0]
    scene_index = scene.get("scene_index", 0) if isinstance(scene, dict) else 0
    return {
        "artifact_role": "timeline_patch",
        "version": 1,
        "base_timeline_ref": "timeline.json",
        "patches": [{
            "op": "replace_clip",
            "slot_index": clip["slot_index"],
            "after": {
                "asset_id": asset["asset_id"],
                "scene_index": scene_index,
            },
        }],
        "diagnostics": [],
    }


def run_smoke(artifact_root: str | Path, base_url: str, *, exercise_replace: bool = False) -> Dict[str, Any]:
    """Run the Workbench smoke flow against a running server."""
    root = Path(artifact_root)
    before = canonical_hashes(root)

    html = _read_text_url(f"{base_url}/workbench")
    required_markers = ("Hermes Native Preview Workbench", "btn-save-all", "lane-video")
    missing = [m for m in required_markers if m not in html]
    if missing:
        raise SmokeError(f"workbench HTML missing markers: {missing}")

    preview = _read_json_url(f"{base_url}/api/workbench/preview-timeline")
    if preview.get("artifact_role") != "preview_timeline":
        raise SmokeError("preview endpoint did not return preview_timeline")

    patch = build_replacement_patch(preview) if exercise_replace else build_duration_patch(preview)
    save = _post_json_url(f"{base_url}/api/workbench/save-all", {"timeline_patch": patch})
    if not save.get("ok"):
        raise SmokeError(f"save-all failed: {save}")

    report = _post_json_url(f"{base_url}/api/workbench/review-report", {})
    if not report.get("ok"):
        raise SmokeError(f"review-report failed: {report}")

    expected = {
        "timeline_patch.json",
        "patched_draft_timeline.json",
        "workbench_handoff.json",
        "workbench_review_report.json",
        "workbench_review_report.md",
    }
    missing_artifacts = sorted(name for name in expected if not (root / name).is_file())
    if missing_artifacts:
        raise SmokeError(f"missing draft artifacts: {missing_artifacts}")

    after = canonical_hashes(root)
    changed = sorted(name for name, digest in before.items() if after.get(name) != digest)
    if changed:
        raise SmokeError(f"canonical artifacts changed: {changed}")

    return {
        "ok": True,
        "base_url": base_url,
        "clips": len(preview.get("clips") or []),
        "canonical_checked": sorted(before),
        "draft_artifacts": sorted(expected),
        "exercised": "replace_clip" if exercise_replace else "set_duration",
        "save_written": save.get("written", []),
        "review_summary": report.get("summary", {}),
    }


def start_threaded_server(root: Path, port: int = 0) -> Tuple[ThreadingHTTPServer, threading.Thread, str]:
    """Start WorkbenchHandler in-process for tests and CLI smoke."""
    class BoundHandler(WorkbenchHandler):
        artifact_root = root.resolve()
        base_url = "http://127.0.0.1:0"

    server = ThreadingHTTPServer(("127.0.0.1", port), BoundHandler)
    BoundHandler.base_url = f"http://127.0.0.1:{server.server_port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, BoundHandler.base_url


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run a Workbench frontend/API smoke test")
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--base-url", help="Use an already running Workbench server")
    parser.add_argument("--exercise-replace", action="store_true",
                        help="Use replace_clip instead of a no-op duration patch")
    parser.add_argument("--port", type=int, default=0, help="Port for the temporary server")
    parser.add_argument("--out", help="Optional JSON output path")
    args = parser.parse_args(argv)

    root = Path(args.artifact_root).resolve()
    server = None
    thread = None
    try:
        base_url = args.base_url
        if not base_url:
            server, thread, base_url = start_threaded_server(root, args.port)
        result = run_smoke(root, base_url, exercise_replace=args.exercise_replace)
        text = json.dumps(result, ensure_ascii=False, indent=2)
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
        print(text)
        return 0
    except SmokeError as exc:
        print(f"[workbench-smoke] FAILED: {exc}")
        return 2
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
