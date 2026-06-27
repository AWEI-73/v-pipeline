"""No-render handoff gate for subtitle and voiceover evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_json(path: str | Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else None


def _contract_requires_subtitles(contract: Mapping[str, Any]) -> bool:
    return contract.get("subtitle_required") is True


def _contract_requires_voiceover(contract: Mapping[str, Any]) -> bool:
    return contract.get("voiceover_required") is True or contract.get("narration_policy") == "required"


def _manifest_items(manifest: Mapping[str, Any] | None) -> list[Mapping[str, Any]]:
    if not manifest:
        return []
    for key in ("segments", "clips", "lines"):
        value = manifest.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, Mapping)]
    return []


def _voiceover_audio_refs(manifest: Mapping[str, Any] | None) -> list[str]:
    refs: list[str] = []
    for item in _manifest_items(manifest):
        for key in ("audio_file", "audio_ref", "path", "file"):
            ref = _clean(item.get(key))
            if ref:
                refs.append(ref)
                break
    return refs


def _resolve_ref(ref: str, out_root: Path) -> Path:
    path = Path(ref)
    return path if path.is_absolute() else out_root / path


def _has_existing_audio_refs(manifest: Mapping[str, Any] | None, out_root: Path) -> bool:
    refs = _voiceover_audio_refs(manifest)
    return bool(refs) and all(_resolve_ref(ref, out_root).is_file() for ref in refs)


def accept_subtitle_voiceover_handoff(
    subtitle_voiceover_contract: Mapping[str, Any],
    *,
    caption_audit: Mapping[str, Any] | None = None,
    narration_manifest: Mapping[str, Any] | None = None,
    subtitles_path: str | Path | None = None,
    out_dir: str | Path,
) -> dict[str, Any]:
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    subtitles_ref = Path(subtitles_path) if subtitles_path else out_root / "subtitles.srt"
    language = _clean(subtitle_voiceover_contract.get("language")) or "unknown"
    subtitle_required = _contract_requires_subtitles(subtitle_voiceover_contract)
    voiceover_required = _contract_requires_voiceover(subtitle_voiceover_contract)

    blocking: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if subtitle_required:
        if not subtitles_ref.is_file():
            blocking.append({
                "rule": "subtitles_missing",
                "message": "subtitle_voiceover_contract requires subtitles, but subtitles.srt is missing",
            })
        if not isinstance(caption_audit, Mapping):
            blocking.append({
                "rule": "caption_audit_missing",
                "message": "required subtitles need caption_audit.json before BUILD handoff",
            })
        elif caption_audit.get("pass") is not True:
            blocking.append({
                "rule": "caption_audit_not_passed",
                "message": "caption_audit.json must pass before subtitle BUILD handoff",
            })

    if voiceover_required:
        if not isinstance(narration_manifest, Mapping):
            blocking.append({
                "rule": "narration_manifest_missing",
                "message": "voiceover is required but narration_manifest.json is missing",
            })
        elif not _manifest_items(narration_manifest):
            blocking.append({
                "rule": "narration_manifest_empty",
                "message": "narration_manifest.json has no narration segments",
            })
        elif not _has_existing_audio_refs(narration_manifest, out_root):
            blocking.append({
                "rule": "voiceover_audio_missing",
                "message": "narration manifest must reference existing voiceover audio files",
            })

    if language == "unknown" and (subtitle_required or voiceover_required):
        warnings.append({
            "rule": "language_unknown",
            "message": "subtitle/voiceover language is unknown; keep visible for review",
        })

    ok = not blocking
    acceptance = {
        "artifact_role": "subtitle_voiceover_handoff_acceptance",
        "version": 1,
        "ok": ok,
        "language": language,
        "subtitle_required": subtitle_required,
        "voiceover_required": voiceover_required,
        "blocking": blocking,
        "warnings": warnings,
        "next_action": "subtitle_voiceover_build_handoff_ready" if ok else "repair_subtitle_voiceover_handoff",
    }
    build_handoff = {
        "artifact_role": "subtitle_voiceover_build_handoff",
        "version": 1,
        "language": language,
        "subtitle_ready": bool(ok and (not subtitle_required or subtitles_ref.is_file())),
        "voiceover_ready": bool(ok and (not voiceover_required or _has_existing_audio_refs(narration_manifest, out_root))),
        "subtitles": str(subtitles_ref) if subtitles_ref.is_file() else None,
        "caption_audit": str(out_root / "caption_audit.json") if isinstance(caption_audit, Mapping) else None,
        "narration_manifest": str(out_root / "narration_manifest.json") if isinstance(narration_manifest, Mapping) else None,
        "rendered_video": False,
    }

    _write_json(out_root / "subtitle_voiceover_handoff_acceptance.json", acceptance)
    _write_json(out_root / "subtitle_voiceover_build_handoff.json", build_handoff)
    if isinstance(caption_audit, Mapping):
        _write_json(out_root / "caption_audit.json", caption_audit)
    if isinstance(narration_manifest, Mapping):
        _write_json(out_root / "narration_manifest.json", narration_manifest)
    return {
        "subtitle_voiceover_handoff_acceptance": acceptance,
        "subtitle_voiceover_build_handoff": build_handoff,
    }


def accept_subtitle_voiceover_handoff_files(
    contract_path: str | Path,
    *,
    out_dir: str | Path,
    caption_audit_path: str | Path | None = None,
    narration_manifest_path: str | Path | None = None,
    subtitles_path: str | Path | None = None,
) -> dict[str, Any]:
    contract = _load_json(contract_path) or {}
    return accept_subtitle_voiceover_handoff(
        contract,
        caption_audit=_load_json(caption_audit_path),
        narration_manifest=_load_json(narration_manifest_path),
        subtitles_path=subtitles_path,
        out_dir=out_dir,
    )
