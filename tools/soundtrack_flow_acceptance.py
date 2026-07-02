"""No-render acceptance for Soundtrack Arranger -> Audio Director handoff."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.pipeline_home import summarize_run
from video_pipeline_core.artifact_manifest import register_handoff
from video_pipeline_core.audio_handoff_acceptance import accept_audio_handoff
from video_pipeline_core.soundtrack_arranger import write_soundtrack_artifacts


def _load_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _update_artifact_manifest(out_dir: Path) -> None:
    manifest_path = out_dir / "artifact_manifest.json"
    manifest: dict[str, Any] = {}
    if manifest_path.is_file():
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            if isinstance(loaded, dict):
                manifest.update(loaded)
        except json.JSONDecodeError:
            manifest = {}
    manifest.setdefault("artifact_role", "artifact_manifest")
    manifest.setdefault("artifact_manifest_version", 1)
    names = {
        "soundtrack_plan": "soundtrack_plan.json",
        "music_source_candidates": "music_source_candidates.json",
        "sound_license_manifest": "sound_license_manifest.json",
        "audio_director_handoff": "audio_director_handoff.json",
        "soundtrack_probe_report": "soundtrack_probe_report.json",
        "audio_handoff_acceptance": "audio_handoff_acceptance.json",
        "audio_mix_plan": "audio_mix_plan.json",
        "soundtrack_flow_acceptance_report": "soundtrack_flow_acceptance_report.json",
    }
    for key, filename in names.items():
        path = out_dir / filename
        if path.is_file():
            manifest[key] = str(path)
    _write_json(manifest_path, manifest)
    handoff_path = out_dir / "audio_director_handoff.json"
    if handoff_path.is_file():
        register_handoff(
            out_dir,
            artifact_path=handoff_path,
            owner_branch="soundtrack-arranger",
            status="accepted",
            updated_by="tools/soundtrack_flow_acceptance.py",
            interface_id="soundtrack_arranger.to.audio_director.handoff",
            next_action="audio_director_mix_or_build",
        )


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _section_by_id(plan: Mapping[str, Any], section_id: str) -> dict[str, Any]:
    for section in plan.get("sections") or []:
        if str(section.get("section_id")) == section_id:
            return dict(section)
    raise ValueError(f"selected section not found in soundtrack_plan: {section_id}")


def _write_selected_handoff(
    out_dir: Path,
    *,
    soundtrack_plan: Mapping[str, Any],
    section_id: str,
    source_type: str,
    license_note: str,
    selected_audio_file: str = "",
    fake_reviewed_audio: bool,
) -> dict[str, Any]:
    if not license_note.strip():
        raise ValueError("license_note is required for selected audio")
    out_dir = out_dir.resolve()
    section = _section_by_id(soundtrack_plan, section_id)
    audio_dir = out_dir / "audio" / "sources"
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_file = Path(selected_audio_file).resolve() if selected_audio_file else (audio_dir / f"reviewed_{section_id}.mp3").resolve()
    if selected_audio_file and not audio_file.is_file():
        raise ValueError(f"selected_audio_file does not exist: {selected_audio_file}")
    if fake_reviewed_audio and not selected_audio_file:
        audio_file.write_bytes(b"ID3 fake reviewed audio")

    def selected_for(item: Mapping[str, Any], item_source_type: str, item_audio_file: Path) -> dict[str, Any]:
        item_section_id = str(item.get("section_id"))
        return {
            "candidate_id": f"reviewed_{item_section_id}",
            "provider": "reviewed_manual",
            "section_id": item_section_id,
            "source_type": item_source_type,
            "audio_file": str(item_audio_file),
            "license_note": license_note,
            "license_status": "user_asserted",
            "usage_scope": "internal_only",
            "delivery_allowed": True,
            "music_role": item.get("music_role"),
            "vocal_policy": item.get("vocal_policy"),
            "ducking_policy": item.get("ducking_policy"),
        }

    selected_audio_files = [selected_for(section, source_type, audio_file)]
    if fake_reviewed_audio:
        covered_roles = {
            _clean(item.get("music_role"))
            for item in selected_audio_files
            if _clean(item.get("music_role")) in {"bgm", "song"}
        }
        for item in soundtrack_plan.get("sections") or []:
            role = _clean(item.get("music_role"))
            item_section_id = _clean(item.get("section_id"))
            if role not in {"bgm", "song"} or role in covered_roles or not item_section_id:
                continue
            fake_file = (audio_dir / f"reviewed_{item_section_id}.mp3").resolve()
            fake_file.write_bytes(b"ID3 fake reviewed audio")
            item_source_type = "jamendo_song" if role == "song" else "licensed_library"
            selected_audio_files.append(selected_for(item, item_source_type, fake_file))
            covered_roles.add(role)
    manifest = {
        "artifact_role": "sound_license_manifest",
        "version": 1,
        "delivery_allowed": True,
        "blocked_reasons": [],
        "selected_sources": selected_audio_files,
    }
    handoff = {
        "artifact_role": "audio_director_handoff",
        "version": 1,
        "handoff_to": "audio-director",
        "ready_for_audio_director": True,
        "blocks": [],
        "selected_audio_files": selected_audio_files,
        "sections": [
            {
                "section_id": section.get("section_id"),
                "music_role": section.get("music_role"),
                "vocal_policy": section.get("vocal_policy"),
                "ducking_policy": section.get("ducking_policy"),
                "source_type": source_type if section.get("section_id") == section_id else section.get("source_type"),
            }
            for section in soundtrack_plan.get("sections") or []
        ],
    }
    _write_json(out_dir / "sound_license_manifest.json", manifest)
    _write_json(out_dir / "audio_director_handoff.json", handoff)
    return {"sound_license_manifest": manifest, "audio_director_handoff": handoff}


def _minimal_soundtrack_probe(audio_file: str | Path) -> dict[str, Any]:
    audio_path = Path(audio_file).resolve()
    return {
        "artifact_role": "soundtrack_probe_report",
        "version": 1,
        "pass": True,
        "audio_file": str(audio_path),
        "duration_sec": 30.0,
        "analysis_depth": "acceptance_stub",
        "features": {
            "mean_dbfs": -18.0,
            "peak_dbfs": -3.0,
            "vocal_analysis": {
                "has_vocals": False,
                "method": "acceptance_stub",
                "vocal_density": "none",
                "vocal_ratio": 0.0,
                "segments": [],
            },
        },
        "sections": [{"start_sec": 0.0, "end_sec": 30.0, "role": "full_track"}],
        "editing_fit": {"montage": "medium", "speech_underlay": "high"},
        "section_fit": [{"video_section": "hotblooded_montage", "fit": "medium"}],
        "limitations": ["No-render acceptance stub; real delivery must run tools/soundtrack_probe.py."],
    }


def _minimal_soundtrack_probe_bundle(selected_audio_files: list[Mapping[str, Any]]) -> dict[str, Any]:
    reports = []
    for selected in selected_audio_files:
        report = _minimal_soundtrack_probe(selected.get("audio_file"))
        report["candidate_id"] = selected.get("candidate_id")
        report["section_id"] = selected.get("section_id")
        reports.append(report)
    if len(reports) == 1:
        return reports[0]
    return {
        "artifact_role": "soundtrack_probe_bundle",
        "version": 1,
        "track_reports": reports,
    }


def run_acceptance(
    input_path: str | Path,
    out_dir: str | Path,
    *,
    selected_section_id: str = "",
    source_type: str = "licensed_library",
    license_note: str = "",
    selected_audio_file: str = "",
    soundtrack_probe_report: str = "",
    fake_reviewed_audio: bool = False,
) -> dict[str, Any]:
    out_root = Path(out_dir).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    payload = _load_json(input_path)
    artifacts = write_soundtrack_artifacts(payload, out_root)

    if selected_section_id:
        artifacts.update(
            _write_selected_handoff(
                out_root,
                soundtrack_plan=artifacts["soundtrack_plan"],
                section_id=selected_section_id,
                source_type=source_type,
                license_note=license_note,
                selected_audio_file=selected_audio_file,
                fake_reviewed_audio=fake_reviewed_audio,
            )
        )
        if soundtrack_probe_report:
            probe_payload = _load_json(soundtrack_probe_report)
            _write_json(out_root / "soundtrack_probe_report.json", probe_payload)
        elif fake_reviewed_audio:
            selected = artifacts["audio_director_handoff"].get("selected_audio_files") or []
            _write_json(out_root / "soundtrack_probe_report.json", _minimal_soundtrack_probe_bundle(selected))

    acceptance = accept_audio_handoff(
        artifacts["audio_director_handoff"],
        soundtrack_plan=artifacts["soundtrack_plan"],
        sound_license_manifest=artifacts["sound_license_manifest"],
        soundtrack_probe_report=_load_json(out_root / "soundtrack_probe_report.json")
        if (out_root / "soundtrack_probe_report.json").is_file()
        else None,
        out_dir=out_root,
    )
    home = summarize_run(out_root)
    ok = bool(acceptance["audio_handoff_acceptance"].get("ok"))
    report = {
        "artifact_role": "soundtrack_flow_acceptance_report",
        "version": 1,
        "ok": ok,
        "failed_stage": None if ok else "audio_handoff_acceptance",
        "rendered": False,
        "artifacts": [
            "soundtrack_plan.json",
            "music_source_candidates.json",
            "sound_license_manifest.json",
            "audio_director_handoff.json",
            "soundtrack_probe_report.json",
            "audio_handoff_acceptance.json",
            "audio_mix_plan.json",
        ],
        "pipeline_home": home,
        "next_action": home.get("next"),
    }
    _write_json(out_root / "soundtrack_flow_acceptance_report.json", report)
    _update_artifact_manifest(out_root)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="video_intent/brief JSON")
    parser.add_argument("--out-dir", required=True, help="run folder for artifacts")
    parser.add_argument("--selected-section-id", default="", help="section id with reviewed/selected audio")
    parser.add_argument("--source-type", default="licensed_library", help="selected audio source_type")
    parser.add_argument("--license-note", default="", help="required when selected audio is provided")
    parser.add_argument("--selected-audio-file", default="", help="existing reviewed/downloaded audio file to pass to Audio Director")
    parser.add_argument("--soundtrack-probe-report", default="", help="existing soundtrack_probe_report.json for selected audio")
    parser.add_argument("--fake-reviewed-audio", action="store_true", help="write a tiny fake audio file for no-render tests")
    parser.add_argument("--json", action="store_true", help="print report JSON")
    args = parser.parse_args()

    try:
        report = run_acceptance(
            args.input,
            args.out_dir,
            selected_section_id=args.selected_section_id,
            source_type=args.source_type,
            license_note=args.license_note,
            selected_audio_file=args.selected_audio_file,
            soundtrack_probe_report=args.soundtrack_probe_report,
            fake_reviewed_audio=args.fake_reviewed_audio,
        )
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            "soundtrack_flow_acceptance "
            f"ok={str(report['ok']).lower()} next={report.get('next_action')}"
        )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
