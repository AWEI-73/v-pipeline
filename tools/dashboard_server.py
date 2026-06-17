#!/usr/bin/env python3
"""
Review Dashboard V1 Server
Lightweight HTTP server for viewing Hermes video pipeline artifacts.
"""

import argparse
import hashlib
import json
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path

# Files for Profile A (review_demo)
PROFILE_A_FILES = {
    "timeline": "timeline.json",
    "review_report": "review_report.json",
    "project_material_map": "project_material_map.json",
    "state": "state.json",
    "contact_sheet": "contact_sheet.jpg"
}

# Files for Profile B (verify_bundle)
PROFILE_B_FILES = {
    "delivery_gate": "delivery_gate.json",
    "timeline_invariants": "timeline_invariants.json",
    "caption_audit": "caption_audit.json",
    "broll_audit": "broll_audit.json",
    "black_frame_audit": "black_frame_audit.json",
    "verify_evidence_bundle": "verify_evidence_bundle.json",
    "contact_sheet": "contact_sheet.jpg",
    "overview_grid": "overview_grid.jpg"
}


def resolve_artifact_path(root_dir: Path, filename: str) -> Path:
    """Find a file in the root directory or common subdirectories (verify/, m5_verify_evidence/)."""
    direct_path = root_dir / filename
    if direct_path.exists():
        return direct_path
    
    subdirs = ["verify", "m5_verify_evidence", "verify_evidence"]
    for sd in subdirs:
        subdir_path = root_dir / sd / filename
        if subdir_path.exists():
            return subdir_path
            
    return direct_path


def detect_profile(root_dir: Path) -> str:
    """Detect the artifact profile based on existing files in root_dir."""
    has_review_report = resolve_artifact_path(root_dir, "review_report.json").exists()
    has_timeline = resolve_artifact_path(root_dir, "timeline.json").exists() or resolve_artifact_path(root_dir, "timeline_build.json").exists()
    has_verify_bundle = resolve_artifact_path(root_dir, "verify_evidence_bundle.json").exists()
    has_delivery_gate = resolve_artifact_path(root_dir, "delivery_gate.json").exists()

    if has_review_report and has_timeline:
        return "review_demo"
    elif has_verify_bundle or has_delivery_gate:
        return "verify_bundle"
    else:
        return "unknown"


def load_json_file(file_path: Path):
    """Load JSON from a file, returning errors gracefully if malformed or missing."""
    if not file_path.exists():
        return None
    try:
        content = file_path.read_text(encoding="utf-8")
        return json.loads(content)
    except json.JSONDecodeError as e:
        return {"error": f"Malformed JSON: {str(e)}"}
    except Exception as e:
        return {"error": f"Failed to read file: {str(e)}"}


WORKBENCH_DRAFT_ARTIFACTS = {
    "timeline_patch": "timeline_patch.json",
    "patched_draft_timeline": "patched_draft_timeline.json",
    "workbench_contract_patch": "workbench_contract_patch.json",
    "workbench_handoff": "workbench_handoff.json",
    "subtitle_patch": "subtitle_patch.json",
    "audio_cue_patch": "audio_cue_patch.json",
    "effect_patch": "effect_patch.json",
    "workbench_review_report": "workbench_review_report.json",
    "workbench_review_report_md": "workbench_review_report.md",
}


def _json_patch_op_count(path: Path) -> int:
    data = load_json_file(path)
    if not isinstance(data, dict):
        return 0
    patches = data.get("patches")
    if not isinstance(patches, list):
        return 0
    return len([p for p in patches if isinstance(p, dict)])


def collect_workbench_draft_status(root_dir: Path):
    """Return read-only status for draft artifacts produced by the Workbench."""
    artifacts = {}
    present_count = 0
    for key, filename in WORKBENCH_DRAFT_ARTIFACTS.items():
        path = root_dir / filename
        detail = {
            "filename": filename,
            "exists": False,
            "path": None,
            "size_bytes": 0,
            "sha256": None,
        }
        if path.is_file():
            data = path.read_bytes()
            detail.update({
                "exists": True,
                "path": filename,
                "size_bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            })
            present_count += 1
        artifacts[key] = detail

    summary = {
        "present_count": present_count,
        "timeline_edits": _json_patch_op_count(root_dir / "timeline_patch.json"),
        "contract_edits": _json_patch_op_count(root_dir / "workbench_contract_patch.json"),
        "subtitle_edits": _json_patch_op_count(root_dir / "subtitle_patch.json"),
        "audio_cues": _json_patch_op_count(root_dir / "audio_cue_patch.json"),
        "effect_intents": _json_patch_op_count(root_dir / "effect_patch.json"),
    }
    return artifacts, summary


def scan_available_projects():
    """Scan `.tmp` and `C:/Users/user/Desktop/video_project` to list all valid runs."""
    projects = []

    # 1. Add default temp folders if they exist
    default_runs = [
        ("預設展示 (srp_real67_review_demo)", Path(".tmp/srp_real67_review_demo")),
        ("67 期完整回放 (srp_real67_fuller_replay)", Path(".tmp/srp_real67_fuller_replay")),
        ("預設驗收 (srp_acceptance)", Path(".tmp/srp_acceptance")),
    ]
    for name, run_path in default_runs:
        if run_path.is_dir():
            projects.append({
                "name": name,
                "path": str(run_path.resolve())
            })

    # 2. Scan C:/Users/user/Desktop/video_project
    vp_dir = Path("C:/Users/user/Desktop/video_project")
    if vp_dir.is_dir():
        # Search for state.json files up to 4 sublevels deep
        for root, dirs, files in os.walk(str(vp_dir)):
            # Limit depth to avoid walking forever
            depth = len(Path(root).relative_to(vp_dir).parts)
            if depth > 4:
                dirs.clear()  # Don't go deeper
                continue
            
            if "state.json" in files or "verify_evidence_bundle.json" in files or "delivery_gate.json" in files:
                parent_path = Path(root).resolve()
                # Skip duplicate entries
                if any(p["path"] == str(parent_path) for p in projects):
                    continue
                
                rel = parent_path.relative_to(vp_dir)
                projects.append({
                    "name": f"專案: {rel}",
                    "path": str(parent_path)
                })
    
    return projects


def parse_srt(srt_content: str):
    import re
    cues = []
    # Split by double newline (or similar) to parse blocks
    blocks = re.split(r'\n\s*\n', srt_content.strip())
    for block in blocks:
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if len(lines) >= 3:
            # First line is index, second line is timestamps, third+ is text
            time_match = re.match(r'(\d+:\d+:\d+,\d+)\s*-->\s*(\d+:\d+:\d+,\d+)', lines[1])
            if time_match:
                start_str, end_str = time_match.groups()
                def to_secs(t_str):
                    parts = t_str.replace(',', '.').split(':')
                    return float(parts[0])*3600 + float(parts[1])*60 + float(parts[2])
                try:
                    start_sec = to_secs(start_str)
                    end_sec = to_secs(end_str)
                    text = " ".join(lines[2:])
                    cues.append({
                        "start_sec": start_sec,
                        "end_sec": end_sec,
                        "text": text
                    })
                except Exception:
                    pass
    return cues


class DashboardHandler(BaseHTTPRequestHandler):
    artifact_root: Path = Path(".")
    dashboard_dir: Path = Path(".")

    def log_message(self, format, *args):
        pass

    def send_error_response(self, status_code, message):
        self.send_response(status_code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(message.encode("utf-8"))

    def get_validated_root(self, query_params) -> Path:
        """Extract and validate the root path from query parameters, fallback to default."""
        root_val = query_params.get("root", [None])[0]
        if not root_val:
            return self.artifact_root

        candidate_root = Path(root_val).resolve()
        
        # Security Boundary Check: must reside within C:/Users/user/Desktop/video_project
        # or the workspace's .tmp directory, or the current workspace root.
        allowed_roots = [
            Path("C:/Users/user/Desktop/video_project").resolve(),
            Path(".tmp").resolve(),
            Path(".").resolve()
        ]
        
        is_allowed = False
        for allowed in allowed_roots:
            if allowed in candidate_root.parents or candidate_root == allowed:
                is_allowed = True
                break

        if not is_allowed or not candidate_root.is_dir():
            return self.artifact_root
            
        return candidate_root

    def serve_file(self, file_path: Path, content_type: str):
        """Helper to serve a local file, supporting range requests for video playback."""
        if not file_path.is_file():
            self.send_error_response(404, "File Not Found")
            return

        file_size = file_path.stat().st_size
        range_header = self.headers.get("Range")

        if range_header and range_header.startswith("bytes="):
            try:
                ranges = range_header.replace("bytes=", "").split("-")
                start = int(ranges[0])
                end = int(ranges[1]) if ranges[1] else file_size - 1
                if start >= file_size or end >= file_size or start > end:
                    raise ValueError("Range out of bounds")
            except Exception:
                self.send_error_response(416, "Requested Range Not Satisfiable")
                return

            length = end - start + 1
            self.send_response(206)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
            self.send_header("Content-Length", str(length))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()

            try:
                with open(file_path, "rb") as f:
                    f.seek(start)
                    remaining = length
                    while remaining > 0:
                        chunk_size = min(remaining, 64 * 1024)
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            except Exception:
                pass
        else:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(file_size))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            try:
                with open(file_path, "rb") as f:
                    while True:
                        chunk = f.read(64 * 1024)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
            except Exception:
                pass

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path_str = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # Route / -> dashboard_v1.html
        if path_str == "/" or path_str == "/index.html":
            html_path = self.dashboard_dir / "dashboard_v1.html"
            self.serve_file(html_path, "text/html; charset=utf-8")
            return

        # Serve static dashboard assets
        if path_str == "/dashboard_v1.css":
            css_path = self.dashboard_dir / "dashboard_v1.css"
            self.serve_file(css_path, "text/css; charset=utf-8")
            return

        if path_str == "/dashboard_v1.js":
            js_path = self.dashboard_dir / "dashboard_v1.js"
            self.serve_file(js_path, "application/javascript; charset=utf-8")
            return

        # Route /api/projects -> list scanned folders containing runs
        if path_str == "/api/projects":
            projects = scan_available_projects()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(projects, ensure_ascii=False, indent=2).encode("utf-8"))
            return

        # Route /api/artifacts -> aggregate JSON data
        if path_str == "/api/artifacts":
            active_root = self.get_validated_root(query_params)
            profile = detect_profile(active_root)
            artifact_errors = []

            # 1. Resolve Media URLs
            final_mp4_resolved = resolve_artifact_path(active_root, "final.mp4")
            if final_mp4_resolved.exists():
                rel_path = final_mp4_resolved.relative_to(active_root).as_posix()
                final_video_url = f"/static/{rel_path}?root={urllib.parse.quote(str(active_root))}"
            else:
                final_video_url = None

            contact_sheet_resolved = resolve_artifact_path(active_root, "contact_sheet.jpg")
            if contact_sheet_resolved.exists():
                rel_path = contact_sheet_resolved.relative_to(active_root).as_posix()
                contact_sheet_url = f"/static/{rel_path}?root={urllib.parse.quote(str(active_root))}"
            else:
                contact_sheet_url = None

            # Helper to load optional JSON and log error if malformed
            def load_optional_json(filename):
                p = resolve_artifact_path(active_root, filename)
                if p.exists() and p.is_file():
                    try:
                        return json.loads(p.read_text(encoding="utf-8"))
                    except Exception as e:
                        err_msg = f"Malformed JSON: {str(e)}"
                        artifact_errors.append({
                            "file": filename,
                            "error": err_msg
                        })
                        return {"error": err_msg}
                return None

            # Load Raw files
            timeline_data = load_optional_json("timeline.plan")
            if not timeline_data:
                timeline_data = load_optional_json("timeline.json")
            if not timeline_data:
                timeline_data = load_optional_json("timeline_build.json")

            review_report = load_optional_json("review_report.json")
            delivery_gate = load_optional_json("delivery_gate.json")
            state = load_optional_json("state.json")
            black_frame_audit = load_optional_json("black_frame_audit.json")
            broll_audit = load_optional_json("broll_audit.json")
            caption_audit = load_optional_json("caption_audit.json")
            verify_evidence_bundle = load_optional_json("verify_evidence_bundle.json")

            # Extract timeline slots list
            plan_list = []
            if timeline_data:
                if isinstance(timeline_data, list):
                    plan_list = timeline_data
                elif isinstance(timeline_data, dict):
                    if "plan" in timeline_data and isinstance(timeline_data["plan"], list):
                        plan_list = timeline_data["plan"]
                    elif "clips" in timeline_data and isinstance(timeline_data["clips"], list):
                        plan_list = timeline_data["clips"]
                    elif "slots" in timeline_data and isinstance(timeline_data["slots"], list):
                        plan_list = timeline_data["slots"]

            # 2. Normalize timeline_slots
            timeline_slots = []
            accumulated_time = 0.0
            for idx, raw_slot in enumerate(plan_list):
                slot = dict(raw_slot)
                if "slot_index" not in slot:
                    slot["slot_index"] = idx

                duration = slot.get("duration_sec") or slot.get("extract_dur") or slot.get("target_duration_sec") or slot.get("duration") or 0.0
                try:
                    duration = float(duration)
                except (ValueError, TypeError):
                    duration = 0.0

                start = slot.get("start_sec") or slot.get("start")
                if start is None:
                    start = accumulated_time
                else:
                    try:
                        start = float(start)
                    except (ValueError, TypeError):
                        start = accumulated_time

                end = slot.get("end_sec") or slot.get("end")
                if end is None:
                    end = start + duration
                else:
                    try:
                        end = float(end)
                    except (ValueError, TypeError):
                        end = start + duration

                slot["start_sec"] = start
                slot["duration_sec"] = duration
                slot["end_sec"] = end
                accumulated_time = end
                timeline_slots.append(slot)

            # 3. Read semantic_alignment
            semantic_alignment = None
            if review_report and isinstance(review_report, dict):
                semantic_alignment = review_report.get("semantic_alignment")

            # 4. Map Segment & Slot status
            seg_status_map = {}
            if isinstance(semantic_alignment, list):
                for align in semantic_alignment:
                    seg_id = align.get("segment") or align.get("segment_id")
                    status = align.get("status")
                    if seg_id is not None:
                        seg_status_map[str(seg_id)] = status
            elif isinstance(semantic_alignment, dict):
                for seg_id, align in semantic_alignment.items():
                    if isinstance(align, dict):
                        status = align.get("status")
                    else:
                        status = align
                    seg_status_map[str(seg_id)] = status

            # Collect failed slots
            failed_slots = set()
            if review_report and isinstance(review_report, dict):
                src = review_report.get("slot_render_check")
                if isinstance(src, dict) and "failed_slots" in src:
                    for s in src["failed_slots"]:
                        failed_slots.add(int(s))
            verify_result = load_optional_json("verify_result.json")
            if verify_result and isinstance(verify_result, dict):
                src = verify_result.get("slot_render_check")
                if isinstance(src, dict) and "failed_slots" in src:
                    for s in src["failed_slots"]:
                        failed_slots.add(int(s))

            for slot in timeline_slots:
                slot_idx = slot.get("slot_index")
                seg_id = slot.get("segment") or slot.get("segment_id")
                status = slot.get("status") or "matched"

                if seg_id is not None:
                    align_status = seg_status_map.get(str(seg_id))
                    if align_status in ["drift", "wrong_need", "gap"]:
                        status = align_status
                    elif align_status:
                        status = align_status

                if slot_idx is not None and int(slot_idx) in failed_slots:
                    status = "render_failed"

                slot["status"] = status

            # 5. Load subtitles
            subtitles = []
            srt_path = resolve_artifact_path(active_root, "review_subtitles.srt")
            if not srt_path.exists():
                srt_path = resolve_artifact_path(active_root, "subtitles.srt")
            if srt_path.exists():
                try:
                    subtitles = parse_srt(srt_path.read_text(encoding="utf-8"))
                except Exception as e:
                    artifact_errors.append({
                        "file": srt_path.name,
                        "error": f"Failed to parse SRT: {str(e)}"
                    })

            # 6. Extract Issues
            issues = []
            if isinstance(semantic_alignment, list):
                for align in semantic_alignment:
                    status = align.get("status")
                    if status in ["drift", "wrong_need", "gap"]:
                        issues.append({
                            "type": "semantic",
                            "severity": "error",
                            "segment": align.get("segment") or align.get("segment_id"),
                            "message": f"Segment {align.get('segment')}: Semantic {status} - {align.get('reason') or 'unmatched'}"
                        })
            elif isinstance(semantic_alignment, dict):
                for seg_id, align in semantic_alignment.items():
                    if isinstance(align, dict):
                        status = align.get("status")
                        reason = align.get("reason") or align.get("message") or "unmatched"
                    else:
                        status = align
                        reason = "unmatched"
                    if status in ["drift", "wrong_need", "gap"]:
                        issues.append({
                            "type": "semantic",
                            "severity": "error",
                            "segment": seg_id,
                            "message": f"Segment {seg_id}: Semantic {status} - {reason}"
                        })

            for f_slot in failed_slots:
                seg_num = None
                for slot in timeline_slots:
                    if slot.get("slot_index") == f_slot:
                        seg_num = slot.get("segment") or slot.get("segment_id")
                        break
                issues.append({
                    "type": "render",
                    "severity": "warning",
                    "slot_index": f_slot,
                    "segment": seg_num,
                    "message": f"Slot {f_slot} (Seg {seg_num or 'N/A'}): Render check failed (black frame or low visual quality)"
                })

            if review_report and isinstance(review_report, dict):
                gaps = review_report.get("material_gaps") or review_report.get("gaps")
                if isinstance(gaps, list):
                    for gap in gaps:
                        issues.append({
                            "type": "material_gap",
                            "severity": "error",
                            "message": str(gap)
                        })
                elif isinstance(gaps, dict):
                    for k, v in gaps.items():
                        issues.append({
                            "type": "material_gap",
                            "severity": "error",
                            "message": f"Gap in {k}: {v}"
                        })

            # Read review markdown if available
            review_report_md = None
            review_md_path = resolve_artifact_path(active_root, "review_report.md")
            if review_md_path.exists():
                try:
                    review_report_md = review_md_path.read_text(encoding="utf-8")
                except Exception:
                    pass

            workbench_draft_artifacts, workbench_draft_summary = collect_workbench_draft_status(active_root)

            aggregated = {
                "profile": profile,
                "artifact_root": str(active_root.resolve()),
                "workbench": {
                    "mode": "external_server",
                    "url": "http://localhost:8770/workbench",
                    "command": (
                        f"python tools/workbench_server.py --artifact-root "
                        f"\"{active_root.resolve()}\" --port 8770"
                    ),
                    "note": "Workbench is the write-limited interactive editor; Dashboard stays read-only.",
                    "draft_artifacts": workbench_draft_artifacts,
                    "draft_summary": workbench_draft_summary,
                },
                "final_video_url": final_video_url,
                "contact_sheet_url": contact_sheet_url,
                "timeline_slots": timeline_slots,
                "issues": issues,
                "semantic_alignment": semantic_alignment,
                "subtitles": subtitles,
                "artifact_errors": artifact_errors,
                "raw_paths": {
                    "timeline": str(resolve_artifact_path(active_root, "timeline.json").resolve()) if resolve_artifact_path(active_root, "timeline.json").exists() else None,
                    "review_report": str(resolve_artifact_path(active_root, "review_report.json").resolve()) if resolve_artifact_path(active_root, "review_report.json").exists() else None,
                    "state": str(resolve_artifact_path(active_root, "state.json").resolve()) if resolve_artifact_path(active_root, "state.json").exists() else None,
                },
                # Raw/original fields for compatibility
                "timeline": timeline_data,
                "review_report": review_report,
                "delivery_gate": delivery_gate,
                "state": state,
                "black_frame_audit": black_frame_audit,
                "broll_audit": broll_audit,
                "caption_audit": caption_audit,
                "verify_evidence_bundle": verify_evidence_bundle,
                "review_report_md": review_report_md
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(aggregated, ensure_ascii=False, indent=2).encode("utf-8"))
            return

        # Route /static/<path> -> serve static artifacts under artifact_root securely
        if path_str.startswith("/static/"):
            active_root = self.get_validated_root(query_params)
            
            relative_subpath = path_str[8:]
            relative_subpath = urllib.parse.unquote(relative_subpath)

            if not relative_subpath or relative_subpath.startswith("/") or relative_subpath.startswith("\\"):
                self.send_error_response(403, "Access Denied")
                return

            try:
                resolved_root = active_root.resolve()
                candidate_path = (resolved_root / relative_subpath).resolve()
            except Exception:
                self.send_error_response(400, "Invalid Path")
                return

            # Path Traversal Check
            if resolved_root not in candidate_path.parents and candidate_path != resolved_root:
                self.send_error_response(403, "Access Denied")
                return

            ext = candidate_path.suffix.lower()
            mime_types = {
                ".mp4": "video/mp4",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".svg": "image/svg+xml",
                ".srt": "text/plain; charset=utf-8",
                ".json": "application/json; charset=utf-8",
                ".md": "text/markdown; charset=utf-8"
            }
            content_type = mime_types.get(ext, "application/octet-stream")

            self.serve_file(candidate_path, content_type)
            return

        # Route /api/available_materials -> list files in materials/ and map
        if path_str == "/api/available_materials":
            active_root = self.get_validated_root(query_params)
            materials = []
            seen_paths = set()

            # 1. Scan active_root / materials
            materials_dir = active_root / "materials"
            if materials_dir.is_dir():
                for root, _, files in os.walk(str(materials_dir)):
                    for f in files:
                        ext = Path(f).suffix.lower()
                        path_obj = Path(root) / f
                        abs_path = str(path_obj.resolve())
                        if abs_path in seen_paths:
                            continue
                        
                        m_type = "unknown"
                        if ext in [".mp4", ".mov", ".webm"]:
                            m_type = "video"
                        elif ext in [".png", ".jpg", ".jpeg", ".gif"]:
                            m_type = "image"
                        elif ext in [".mp3", ".wav", ".m4a", ".ogg"]:
                            m_type = "audio"
                        else:
                            continue

                        materials.append({
                            "name": f,
                            "path": abs_path,
                            "type": m_type
                        })
                        seen_paths.add(abs_path)

            # 2. Scan project_material_map.json
            pmap_path = resolve_artifact_path(active_root, "project_material_map.json")
            if pmap_path.exists() and pmap_path.is_file():
                pmap = load_json_file(pmap_path)
                if pmap and isinstance(pmap, dict) and "assets" in pmap:
                    for asset in pmap["assets"]:
                        source = asset.get("source")
                        if source:
                            path_obj = Path(source)
                            abs_path = str(path_obj.resolve()) if path_obj.is_absolute() else str((active_root / source).resolve())
                            if abs_path in seen_paths:
                                continue

                            ext = path_obj.suffix.lower()
                            m_type = asset.get("asset_type") or "video"
                            if not m_type:
                                if ext in [".mp3", ".wav"]:
                                    m_type = "audio"
                                elif ext in [".png", ".jpg", ".jpeg"]:
                                    m_type = "image"
                                else:
                                    m_type = "video"

                            materials.append({
                                "name": path_obj.name,
                                "path": abs_path,
                                "type": m_type
                            })
                            seen_paths.add(abs_path)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(materials, ensure_ascii=False, indent=2).encode("utf-8"))
            return

        self.send_error_response(404, "Not Found")

    def do_POST(self):
        self.send_error_response(
            405,
            "Review Dashboard is read-only. Write-back endpoints are disabled."
        )


def run_server(artifact_root: str, port: int):
    resolved_root = Path(artifact_root).resolve()
    if not resolved_root.is_dir():
        print(f"Error: Artifact root '{artifact_root}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    script_dir = Path(__file__).resolve().parent
    dashboard_dir = script_dir.parent / "dashboard"

    print(f"Starting Hermes Review Dashboard Server V1...")
    print(f"Artifact Root : {resolved_root}")
    print(f"Dashboard Dir : {dashboard_dir}")
    print(f"Port          : {port}")
    print(f"Detected Profile: {detect_profile(resolved_root)}")
    print(f"Access URL    : http://localhost:{port}")

    class BoundDashboardHandler(DashboardHandler):
        artifact_root = resolved_root
        dashboard_dir = script_dir.parent / "dashboard"

    server = ThreadingHTTPServer(("localhost", port), BoundDashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hermes Review Dashboard V1 Server")
    parser.add_argument("--artifact-root", required=True, help="Path to project output artifacts directory")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on (default: 8000)")
    args = parser.parse_args()

    run_server(args.artifact_root, args.port)
