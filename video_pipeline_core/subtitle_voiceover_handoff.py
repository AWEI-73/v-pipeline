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


def _update_artifact_manifest(out_root: Path) -> None:
    manifest_path = out_root / "artifact_manifest.json"
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
        "subtitle_voiceover_handoff_acceptance": "subtitle_voiceover_handoff_acceptance.json",
        "subtitle_voiceover_build_handoff": "subtitle_voiceover_build_handoff.json",
        "caption_audit": "caption_audit.json",
        "narration_manifest": "narration_manifest.json",
        "voiceover_provider_plan": "voiceover_provider_plan.json",
        "voxcpm_runtime_check": "voxcpm_runtime_check.json",
    }
    for key, filename in names.items():
        path = out_root / filename
        if path.is_file():
            manifest[key] = str(path)
    _write_json(manifest_path, manifest)


def _load_json(path: str | Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else None


def _contract_requires_subtitles(contract: Mapping[str, Any]) -> bool:
    return contract.get("subtitle_required") is True


def _contract_requires_voiceover(contract: Mapping[str, Any]) -> bool:
    return contract.get("voiceover_required") is True or contract.get("narration_policy") == "required"


def _contract_fallback_allowed(contract: Mapping[str, Any]) -> bool:
    if contract.get("fallback_allowed") is False:
        return False
    fallback_policy = contract.get("fallback_policy")
    if isinstance(fallback_policy, Mapping) and fallback_policy.get("allowed") is False:
        return False
    return True


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
    voiceover_provider_plan: Mapping[str, Any] | None = None,
    voxcpm_runtime_check: Mapping[str, Any] | None = None,
    subtitles_path: str | Path | None = None,
    out_dir: str | Path,
) -> dict[str, Any]:
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    subtitles_ref = Path(subtitles_path) if subtitles_path else out_root / "subtitles.srt"
    language = _clean(subtitle_voiceover_contract.get("language")) or "unknown"
    subtitle_required = _contract_requires_subtitles(subtitle_voiceover_contract)
    voiceover_required = _contract_requires_voiceover(subtitle_voiceover_contract)
    preferred_provider = _clean(
        subtitle_voiceover_contract.get("preferred_provider")
        or subtitle_voiceover_contract.get("voiceover_provider_preference")
    )
    fallback_allowed = _contract_fallback_allowed(subtitle_voiceover_contract)

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
        provider_unavailable = (
            isinstance(voiceover_provider_plan, Mapping)
            and voiceover_provider_plan.get("provider_available") is False
        )
        selected_provider = _clean(
            (voiceover_provider_plan or {}).get("selected_provider")
            if isinstance(voiceover_provider_plan, Mapping)
            else None
        ) or preferred_provider
        if provider_unavailable and (not fallback_allowed or (voiceover_provider_plan or {}).get("fallback_allowed") is False):
            blocking.append({
                "rule": "voiceover_provider_unavailable",
                "provider": selected_provider or "unknown",
                "message": (
                    _clean((voiceover_provider_plan or {}).get("provider_unavailable_reason"))
                    or "preferred voiceover provider is unavailable and fallback is not allowed"
                ),
                "missing_modules": (voxcpm_runtime_check or {}).get("missing_modules") if isinstance(voxcpm_runtime_check, Mapping) else [],
                "python": (voxcpm_runtime_check or {}).get("python") if isinstance(voxcpm_runtime_check, Mapping) else None,
                "voxcpm_repo": (voxcpm_runtime_check or {}).get("voxcpm_repo") if isinstance(voxcpm_runtime_check, Mapping) else None,
            })
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
    provider_status = {
        "preferred_provider": preferred_provider or None,
        "selected_provider": (
            voiceover_provider_plan.get("selected_provider")
            if isinstance(voiceover_provider_plan, Mapping)
            else None
        ),
        "provider_available": (
            voiceover_provider_plan.get("provider_available")
            if isinstance(voiceover_provider_plan, Mapping)
            else None
        ),
        "fallback_allowed": fallback_allowed,
        "provider_unavailable_reason": (
            voiceover_provider_plan.get("provider_unavailable_reason")
            if isinstance(voiceover_provider_plan, Mapping)
            else None
        ),
        "runtime_check": str(out_root / "voxcpm_runtime_check.json") if isinstance(voxcpm_runtime_check, Mapping) else None,
    }
    next_action = "subtitle_voiceover_build_handoff_ready" if ok else "repair_subtitle_voiceover_handoff"
    if any(item.get("rule") == "voiceover_provider_unavailable" for item in blocking):
        next_action = "needs-context"
    acceptance = {
        "artifact_role": "subtitle_voiceover_handoff_acceptance",
        "version": 1,
        "ok": ok,
        "language": language,
        "subtitle_required": subtitle_required,
        "voiceover_required": voiceover_required,
        "provider_status": provider_status,
        "blocking": blocking,
        "warnings": warnings,
        "next_action": next_action,
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
        "provider_status": provider_status,
        "rendered_video": False,
    }

    _write_json(out_root / "subtitle_voiceover_handoff_acceptance.json", acceptance)
    _write_json(out_root / "subtitle_voiceover_build_handoff.json", build_handoff)
    if isinstance(caption_audit, Mapping):
        _write_json(out_root / "caption_audit.json", caption_audit)
    if isinstance(narration_manifest, Mapping):
        _write_json(out_root / "narration_manifest.json", narration_manifest)
    if isinstance(voiceover_provider_plan, Mapping):
        _write_json(out_root / "voiceover_provider_plan.json", voiceover_provider_plan)
    if isinstance(voxcpm_runtime_check, Mapping):
        _write_json(out_root / "voxcpm_runtime_check.json", voxcpm_runtime_check)
    _update_artifact_manifest(out_root)
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
    voiceover_provider_plan_path: str | Path | None = None,
    voxcpm_runtime_check_path: str | Path | None = None,
    subtitles_path: str | Path | None = None,
) -> dict[str, Any]:
    contract = _load_json(contract_path) or {}
    return accept_subtitle_voiceover_handoff(
        contract,
        caption_audit=_load_json(caption_audit_path),
        narration_manifest=_load_json(narration_manifest_path),
        voiceover_provider_plan=_load_json(voiceover_provider_plan_path),
        voxcpm_runtime_check=_load_json(voxcpm_runtime_check_path),
        subtitles_path=subtitles_path,
        out_dir=out_dir,
    )
