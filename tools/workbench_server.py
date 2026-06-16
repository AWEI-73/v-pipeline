#!/usr/bin/env python
"""Hermes-native workbench server.

Serves the native preview workbench (``dashboard/workbench_native``) plus a tiny
API for the interactive preview engine. This is a *write-limited* server: it may
only write the three workbench artifacts (preview_timeline / timeline_patch /
patched_draft_timeline) and is hard-blocked from touching any canonical artifact.

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
except ImportError:  # pragma: no cover - direct-script fallback
    import preview_timeline as pt
    import timeline_patch as tp
    import workbench_export as wx

WORKBENCH_DIR = Path(__file__).resolve().parent.parent / "dashboard" / "workbench_native"

# The only artifacts this server may ever write.
WRITABLE_OUTPUTS = {
    "preview_timeline.json",
    "timeline_patch.json",
    "patched_draft_timeline.json",
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


def _media_allowlist(root: Path, base_url: str) -> set:
    """Resolved source paths the server is permitted to serve via /media."""
    preview = pt.build_preview_timeline(str(root), base_url)
    allow = set()
    for clip in preview.get("clips", []):
        sp = clip.get("source_path")
        if sp:
            try:
                allow.add(os.path.normcase(str(Path(sp).resolve())))
            except OSError:
                pass
    for audio in preview.get("audio", []):
        # audio src_url is itself a /media url; the underlying file lives in root.
        pass
    for name in ("music.wav", "bgm.webm", "narration.wav", "voiceover.wav"):
        p = root / name
        if p.is_file():
            allow.add(os.path.normcase(str(p.resolve())))
    return allow


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
        if resolved not in allow:
            self._send_error(403, "source not in preview allow-list")
            return

        path = Path(src)
        if not path.is_file():
            self._send_error(404, "media file missing")
            return

        ext = path.suffix.lower()
        ctype = MEDIA_MIME.get(ext, "application/octet-stream")
        size = path.stat().st_size

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
                with path.open("rb") as fh:
                    fh.seek(start)
                    chunk = fh.read(length)
                self.send_response(206)
                self.send_header("Content-Type", ctype)
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                self.send_header("Content-Length", str(len(chunk)))
                self.end_headers()
                self.wfile.write(chunk)
                return
            except (ValueError, OSError):
                pass  # fall through to full body

        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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

        if path == "/api/workbench/preview-timeline":
            preview = pt.build_preview_timeline(str(self.artifact_root), self.base_url)
            self._send_json(200, preview)
            return

        self._send_error(404, "Not found")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/workbench/export":
            self._handle_export()
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
            result = wx.export(str(self.artifact_root), out=out, patch=patch)
        except ValueError as exc:
            self._send_json(422, {"ok": False, "error": str(exc)})
            return
        except Exception as exc:  # pragma: no cover - ffmpeg/runtime failures
            self._send_json(500, {"ok": False, "error": f"export failed: {exc}"})
            return
        self._send_json(200, result)

    def _write_artifact(self, name: str, payload: Any, written: List[str]) -> None:
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
