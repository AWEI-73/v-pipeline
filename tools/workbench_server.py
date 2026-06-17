#!/usr/bin/env python
"""Hermes-native workbench server.

Serves the native preview workbench (``dashboard/workbench_native``) plus a tiny
API for the interactive preview engine. This is a *write-limited* server: it may
only write whitelisted workbench draft artifacts (preview_timeline /
timeline_patch / patched_draft_timeline / layer patches / handoff) and is
hard-blocked from touching any canonical artifact.

It is deliberately separate from the read-only Review Dashboard. The workbench is
for interactive editorial proposals; official rendering still happens via Hermes /
ffmpeg BUILD from the canonical artifacts.

CLI::

    python tools/workbench_server.py --artifact-root <root> --port 8770
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional

try:  # works as `tools.workbench_server` (tests) and as a script
    from tools import preview_timeline as pt
    from tools import timeline_patch as tp
    from tools import workbench_export as wx
    from tools import workbench_patch_to_contract as wc
    from tools import subtitle_patch as sp
    from tools import audio_cue_patch as ap
    from tools import effect_patch as ep
    from tools import workbench_handoff as wh
    from tools import workbench_review_report as wr
    from tools import workbench_thumbs as wt
    from tools import workbench_proxy as wp
except ImportError:  # pragma: no cover - direct-script fallback
    import preview_timeline as pt
    import timeline_patch as tp
    import workbench_export as wx
    import workbench_patch_to_contract as wc
    import subtitle_patch as sp
    import audio_cue_patch as ap
    import effect_patch as ep
    import workbench_handoff as wh
    import workbench_review_report as wr
    import workbench_thumbs as wt
    import workbench_proxy as wp

WORKBENCH_DIR = Path(__file__).resolve().parent.parent / "dashboard" / "workbench_native"

# The only artifacts this server may ever write.
WRITABLE_OUTPUTS = {
    "preview_timeline.json",
    "timeline_patch.json",
    "patched_draft_timeline.json",
    "workbench_contract_patch.json",
    "subtitle_patch.json",
    "audio_cue_patch.json",
    "effect_patch.json",
    "workbench_handoff.json",
    "workbench_review_report.json",
    "workbench_review_report.md",
}

STATIC_MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
}

MEDIA_MIME = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".m4v": "video/mp4",
    ".mkv": "video/x-matroska",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
}


THUMBS_DIRNAME = "workbench_thumbs"
PROXY_DIRNAME = "workbench_proxy"

# Cache the /media allow-list per root. Rebuilding preview_timeline on every byte
# -range request was the main server-side stall during playback/scrub (NPE5).
_ALLOW_CACHE: Dict[str, set] = {}


def _build_allowlist(root: Path, base_url: str) -> set:
    preview = pt.build_preview_timeline(str(root), base_url)
    allow = set()
    for section in ("clips", "material_assets", "effect_assets"):
        for item in preview.get(section, []) or []:
            sp = item.get("source_path")
            if sp:
                try:
                    allow.add(os.path.normcase(str(Path(sp).resolve())))
                except OSError:
                    pass
    for name in ("music.wav", "bgm.webm", "narration.wav", "voiceover.wav"):
        p = root / name
        if p.is_file():
            allow.add(os.path.normcase(str(p.resolve())))
    return allow


def _media_allowlist(root: Path, base_url: str) -> set:
    """Cached resolved source paths the server may serve via /media."""
    key = os.path.normcase(str(root.resolve()))
    cached = _ALLOW_CACHE.get(key)
    if cached is None:
        cached = _build_allowlist(root, base_url)
        _ALLOW_CACHE[key] = cached
    return cached


def _is_under_thumbs(resolved: str, root: Path) -> bool:
    try:
        thumbs = os.path.normcase(str((root / THUMBS_DIRNAME).resolve()))
    except OSError:
        return False
    return resolved.startswith(thumbs + os.sep)


def _is_under_proxy(resolved: str, root: Path) -> bool:
    try:
        proxy = os.path.normcase(str((root / PROXY_DIRNAME).resolve()))
    except OSError:
        return False
    return resolved.startswith(proxy + os.sep)


def _can_preview(root: Path) -> bool:
    return any((root / name).is_file() for name in ("draft_timeline.json", "timeline.json", "timeline.plan"))


class WorkbenchHandler(BaseHTTPRequestHandler):
    artifact_root: Path = Path(".")
    base_url: str = "http://localhost:8770"

    # -- helpers ---------------------------------------------------------- #
    def _send_json(self, code: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, code: int, message: str) -> None:
        self._send_json(code, {"error": message})

    def _serve_static(self, file_path: Path) -> None:
        if not file_path.is_file():
            self._send_error(404, f"Not found: {file_path.name}")
            return
        ext = file_path.suffix.lower()
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", STATIC_MIME.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_media(self, query: Dict[str, List[str]]) -> None:
        src = (query.get("src") or [None])[0]
        if not src:
            self._send_error(400, "missing src")
            return
        src = urllib.parse.unquote(src)
        try:
            resolved = os.path.normcase(str(Path(src).resolve()))
        except OSError:
            self._send_error(400, "invalid src")
            return

        allow = _media_allowlist(self.artifact_root, self.base_url)
        if (resolved not in allow and
                not _is_under_thumbs(resolved, self.artifact_root) and
                not _is_under_proxy(resolved, self.artifact_root)):
            self._send_error(403, "source not in preview allow-list")
            return

        path = Path(src)
        if not path.is_file():
            self._send_error(404, "media file missing")
            return

        ext = path.suffix.lower()
        ctype = MEDIA_MIME.get(ext, "application/octet-stream")
        size = path.stat().st_size
        CHUNK = 262144  # 256 KiB — stream instead of loading the whole file

        # Minimal HTTP Range support so <video> can seek to source_start.
        range_header = self.headers.get("Range")
        if range_header and range_header.startswith("bytes="):
            try:
                rng = range_header.split("=", 1)[1]
                start_s, _, end_s = rng.partition("-")
                start = int(start_s) if start_s else 0
                end = int(end_s) if end_s else size - 1
                end = min(end, size - 1)
                start = max(0, min(start, end))
                length = end - start + 1
                self.send_response(206)
                self.send_header("Content-Type", ctype)
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                self.send_header("Content-Length", str(length))
                self.end_headers()
                self._stream(path, start, length, CHUNK)
                return
            except (ValueError, OSError):
                pass  # fall through to full body

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(size))
        self.end_headers()
        self._stream(path, 0, size, CHUNK)

    def _stream(self, path: Path, start: int, length: int, chunk: int) -> None:
        """Stream ``length`` bytes from ``path`` starting at ``start`` in chunks."""
        remaining = length
        try:
            with path.open("rb") as fh:
                fh.seek(start)
                while remaining > 0:
                    buf = fh.read(min(chunk, remaining))
                    if not buf:
                        break
                    self.wfile.write(buf)
                    remaining -= len(buf)
        except (BrokenPipeError, ConnectionResetError, OSError):
            # client aborted the range (normal during seeking) — ignore
            pass

    # -- routing ---------------------------------------------------------- #
    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path in ("/", "/workbench", "/workbench/"):
            self._serve_static(WORKBENCH_DIR / "index.html")
            return

        if path.startswith("/workbench/"):
            rel = path[len("/workbench/"):]
            if not rel or "/" in rel or "\\" in rel or rel.startswith("."):
                self._send_error(403, "denied")
                return
            self._serve_static(WORKBENCH_DIR / rel)
            return

        if path == "/media":
            self._serve_media(query)
            return

        if path == "/api/workbench/health":
            payload = {
                "artifact_role": "workbench_health",
                "version": 1,
                "status": "ok",
                "artifact_root": str(self.artifact_root.resolve()),
                "can_preview": _can_preview(self.artifact_root),
                "write_limited": True,
                "writable_artifacts": sorted(WRITABLE_OUTPUTS),
            }
            self._send_json(200, payload)
            return

        if path == "/api/workbench/preview-timeline":
            preview = pt.build_preview_timeline(str(self.artifact_root), self.base_url)
            self._send_json(200, preview)
            return

        if path == "/api/workbench/thumbnails":
            # one-time (cached) ffmpeg filmstrip thumbnails; first call is slow
            manifest = wt.build_thumbnails(str(self.artifact_root), self.base_url)
            self._send_json(200, manifest)
            return

        if path == "/api/workbench/proxies":
            # one-time (cached) ffmpeg preview proxies; first call can be slow
            manifest = wp.build_proxies(str(self.artifact_root), self.base_url)
            self._send_json(200, manifest)
            return

        self._send_error(404, "Not found")

    def _read_body(self) -> Any:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8")) if raw.strip() else {}
        except (ValueError, UnicodeDecodeError):
            return None

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/workbench/export":
            self._handle_export()
            return
        if parsed.path == "/api/workbench/sync-contract":
            self._handle_sync_contract()
            return
        if parsed.path == "/api/workbench/subtitle-patch":
            self._handle_track_patch("subtitle_patch.json", sp.validate_subtitle_patch)
            return
        if parsed.path == "/api/workbench/audio-cue-patch":
            self._handle_track_patch("audio_cue_patch.json", ap.validate_audio_cue_patch)
            return
        if parsed.path == "/api/workbench/effect-patch":
            self._handle_track_patch("effect_patch.json", ep.validate_effect_patch)
            return
        if parsed.path == "/api/workbench/save-all":
            self._handle_save_all()
            return
        if parsed.path == "/api/workbench/review-report":
            self._handle_review_report()
            return
        if parsed.path != "/api/workbench/patch":
            self._send_error(404, "Not found")
            return

        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self._send_error(400, "invalid JSON")
            return

        patch = body.get("patch") if isinstance(body, dict) and "patch" in body else body

        ok, errors = tp.validate_patch(str(self.artifact_root), patch)
        if not ok:
            self._send_json(422, {"ok": False, "errors": errors})
            return

        written: List[str] = []

        # 1. Persist the patch itself.
        self._write_artifact("timeline_patch.json", patch, written)

        # 2. Persist the applied patched-draft (never timeline.json).
        try:
            applied = tp.apply_patch(str(self.artifact_root), patch)
            self._write_artifact("patched_draft_timeline.json", applied, written)
        except ValueError as exc:
            self._send_json(422, {"ok": False, "errors": [str(exc)]})
            return

        # 3. Refresh preview_timeline snapshot for convenience.
        preview = pt.build_preview_timeline(str(self.artifact_root), self.base_url)
        self._write_artifact("preview_timeline.json", preview, written)

        self._send_json(200, {
            "ok": True,
            "written": written,
            "spec_alignment": applied.get("_spec_alignment", {}),
        })

    def _handle_review_report(self) -> None:
        result = wr.write_review_report(str(self.artifact_root))
        self._send_json(200, {
            "ok": True,
            "written": [result["json"], result["markdown"]],
            "summary": result["summary"],
        })

    def _handle_export(self) -> None:
        """Opt-in: render the (optionally patched) plan via canonical ffmpeg.

        This is the heavy second path -- it produces workbench_export.mp4 only and
        never a canonical artifact. Blocks until ffmpeg finishes.
        """
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8")) if raw.strip() else {}
        except (ValueError, UnicodeDecodeError):
            self._send_error(400, "invalid JSON")
            return

        patch = body.get("patch") if isinstance(body, dict) else None
        out = (body.get("out") if isinstance(body, dict) else None) or wx.DEFAULT_OUT
        render_effects = bool(body.get("effects")) if isinstance(body, dict) else False
        effect_patch = body.get("effect_patch") if isinstance(body, dict) else None
        if os.path.basename(str(out)) in wx.PROTECTED_OUTPUTS:
            self._send_error(422, f"refusing to export onto protected artifact: {out}")
            return

        # Fall back to a previously saved patch if none supplied inline.
        if patch is None:
            saved = self.artifact_root / "timeline_patch.json"
            if saved.is_file():
                try:
                    patch = json.loads(saved.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    patch = None
        try:
            result = wx.export(str(self.artifact_root), out=out, patch=patch,
                               render_effects=render_effects,
                               effect_patch=effect_patch)
        except ValueError as exc:
            self._send_json(422, {"ok": False, "error": str(exc)})
            return
        except Exception as exc:  # pragma: no cover - ffmpeg/runtime failures
            self._send_json(500, {"ok": False, "error": f"export failed: {exc}"})
            return
        self._send_json(200, result)

    def _handle_sync_contract(self) -> None:
        """Translate a timeline_patch into a draft contract patch + timeline draft.

        Writes only workbench_contract_patch.json + patched_draft_timeline.json
        (both whitelisted); a fail-closed sync writes nothing.
        """
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8")) if raw.strip() else {}
        except (ValueError, UnicodeDecodeError):
            self._send_error(400, "invalid JSON")
            return

        patch = body.get("patch") if isinstance(body, dict) and "patch" in body else body
        result = wc.sync_patch_to_contract(str(self.artifact_root), patch)
        if not result["ok"]:
            self._send_json(422, {"ok": False, "errors": result["errors"],
                                  "diagnostics": result["diagnostics"]})
            return

        written: List[str] = []
        self._write_artifact("workbench_contract_patch.json", result["workbench_contract_patch"], written)
        self._write_artifact("patched_draft_timeline.json", result["patched_draft_timeline"], written)
        self._send_json(200, {
            "ok": True,
            "written": written,
            "changes": len(result["workbench_contract_patch"]["changes"]),
            "diagnostics": result["diagnostics"],
        })

    def _handle_track_patch(self, out_name: str, validator) -> None:
        """Validate a single track patch and write only its whitelisted artifact."""
        body = self._read_body()
        if body is None:
            self._send_error(400, "invalid JSON")
            return
        patch = body.get("patch") if isinstance(body, dict) and "patch" in body else body
        ok, errors, diagnostics = validator(str(self.artifact_root), patch)
        if not ok:
            self._send_json(422, {"ok": False, "errors": errors, "diagnostics": diagnostics})
            return
        written: List[str] = []
        self._write_artifact(out_name, patch, written)
        self._send_json(200, {"ok": True, "written": written, "diagnostics": diagnostics})

    # validators for save-all, keyed by handoff/patch name
    _SAVE_ALL_LAYERS = (
        ("timeline_patch", "timeline_patch.json"),
        ("subtitle_patch", "subtitle_patch.json"),
        ("audio_cue_patch", "audio_cue_patch.json"),
        ("effect_patch", "effect_patch.json"),
    )

    def _validate_layer(self, key: str, patch: Any):
        if key == "timeline_patch":
            ok, errors = tp.validate_patch(str(self.artifact_root), patch)
            return ok, errors
        if key == "subtitle_patch":
            ok, errors, _ = sp.validate_subtitle_patch(str(self.artifact_root), patch)
            return ok, errors
        if key == "audio_cue_patch":
            ok, errors, _ = ap.validate_audio_cue_patch(str(self.artifact_root), patch)
            return ok, errors
        if key == "effect_patch":
            ok, errors, _ = ep.validate_effect_patch(str(self.artifact_root), patch)
            return ok, errors
        return False, [f"unknown layer {key}"]

    def _handle_save_all(self) -> None:
        """Atomic multi-track save. If any provided layer is invalid, write NOTHING.

        Then build workbench_handoff.json indexing the written draft artifacts.
        """
        body = self._read_body()
        if not isinstance(body, dict):
            self._send_error(400, "invalid JSON")
            return

        provided = {k: body[k] for k, _ in self._SAVE_ALL_LAYERS if k in body and body[k]}
        if not provided:
            self._send_json(422, {"ok": False, "errors": ["no patches provided"]})
            return

        # validate-all first (atomic policy: nothing written unless all valid)
        all_errors: Dict[str, Any] = {}
        for key, patch in provided.items():
            ok, errors = self._validate_layer(key, patch)
            if not ok:
                all_errors[key] = errors
        if all_errors:
            self._send_json(422, {"ok": False, "errors": all_errors})
            return

        written: List[str] = []
        for key, name in self._SAVE_ALL_LAYERS:
            if key not in provided:
                continue
            self._write_artifact(name, provided[key], written)
            if key == "timeline_patch":
                applied = tp.apply_patch(str(self.artifact_root), provided[key])
                self._write_artifact("patched_draft_timeline.json", applied, written)

        handoff = wh.build_handoff(str(self.artifact_root))
        self._write_artifact("workbench_handoff.json", handoff, written)
        self._send_json(200, {"ok": True, "written": written, "summary": handoff["summary"]})

    def _write_artifact(self, name: str, payload: Any, written: List[str]) -> None:
        # defence-in-depth: only fixed whitelisted basenames, never a path
        if name != os.path.basename(name) or "/" in name or "\\" in name:
            raise RuntimeError(f"refusing to write a path, not a basename: {name!r}")
        if name not in WRITABLE_OUTPUTS:
            raise RuntimeError(f"refusing to write non-whitelisted artifact: {name}")
        out = self.artifact_root / name
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(name)

    def log_message(self, fmt: str, *args: Any) -> None:  # quieter logs
        return


def run_server(artifact_root: str, port: int) -> None:
    root = Path(artifact_root).resolve()
    base_url = f"http://localhost:{port}"
    WorkbenchHandler.artifact_root = root
    WorkbenchHandler.base_url = base_url

    httpd = ThreadingHTTPServer(("127.0.0.1", port), WorkbenchHandler)
    print(f"[workbench] serving {root}")
    print(f"[workbench] open {base_url}/workbench")
    print("[workbench] writable: preview_timeline.json, timeline_patch.json, patched_draft_timeline.json")
    print("[workbench] canonical artifacts are write-blocked")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[workbench] shutting down")
        httpd.shutdown()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Hermes-native workbench server")
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--port", type=int, default=8770)
    args = parser.parse_args(argv)
    run_server(args.artifact_root, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
