"""generated_assets.py — generated fallback request/manifest artifacts.

This module creates provider-neutral requests. It does not call Antigravity,
assistant imagegen, or any other image/video generator directly.
"""
import json
from pathlib import Path


ALLOWED_GENERATED_PROVIDERS = {
    "antigravity",
    "assistant_imagegen",
    "codex_imagegen",
    "gemini_veo",
}
NON_GENERATED_PROVIDERS = {"pexels", "pixabay", "user_upload", "manual"}


def _segment_id(seg, fallback):
    return seg.get("segment") or fallback


def _is_identity_or_proof(seg):
    core = seg.get("core") or {}
    mat = seg.get("material_fit") or {}
    eg = seg.get("editing_grammar") or {}
    if mat.get("must_include"):
        return True
    if core.get("identity_sensitive") or core.get("proof_critical"):
        return True
    if eg.get("role") == "proof":
        return True
    return False


def _allows_generated(seg):
    mat = seg.get("material_fit") or {}
    policy = mat.get("fallback_policy")
    if policy not in {"generated", "generated_first"}:
        return False
    return not _is_identity_or_proof(seg)


def _validate_provider_priority(provider_priority):
    raw_priority = provider_priority or ["assistant_imagegen", "antigravity"]
    priority = []
    unsupported = []
    for provider in raw_priority:
        if provider in ALLOWED_GENERATED_PROVIDERS:
            priority.append(provider)
        elif provider in NON_GENERATED_PROVIDERS:
            continue
        else:
            unsupported.append(provider)
    if unsupported:
        raise ValueError(f"unsupported generated provider: {unsupported[0]}")
    if not priority:
        priority = ["assistant_imagegen", "antigravity"]
    for provider in priority:
        if provider not in ALLOWED_GENERATED_PROVIDERS:
            raise ValueError(f"unsupported generated provider: {provider}")
    return list(priority)


def build_generated_asset_requests(contract, *, provider_priority=None):
    priority = _validate_provider_priority(provider_priority)
    items = []
    for idx, seg in enumerate((contract or {}).get("segments", []), start=1):
        if not isinstance(seg, dict) or not _allows_generated(seg):
            continue
        mat = seg.get("material_fit") or {}
        core = seg.get("core") or {}
        visual = mat.get("visual_desc") or mat.get("search_query") or core.get("story_purpose") or ""
        reason = mat.get("reason") or "generated fallback requested by contract"
        items.append({
            "segment": _segment_id(seg, idx),
            "asset_role": "conceptual_cutaway",
            "provider": priority[0],
            "prompt": visual,
            "negative_prompt": "text, watermark, distorted hands, low quality, fake identity evidence",
            "reason": reason,
            "forbidden_as_truth": True,
            "source": "generated",
        })
    return {
        "artifact_role": "generated_asset_requests",
        "generated_asset_requests_version": 1,
        "provider_priority": priority,
        "items": items,
    }


def write_generated_asset_requests(contract, path, *, provider_priority=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_generated_asset_requests(contract, provider_priority=provider_priority)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return str(path)


def _request_by_segment(request):
    return {item.get("segment"): item for item in request.get("items", [])}


def write_generated_asset_manifest(request, outputs, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    request_items = _request_by_segment(request or {})
    items = []
    for output in outputs or []:
        segment = output.get("segment")
        req = request_items.get(segment, {})
        provider = output.get("provider") or req.get("provider")
        if provider not in ALLOWED_GENERATED_PROVIDERS:
            raise ValueError(f"unsupported generated provider: {provider}")
        items.append({
            "segment": segment,
            "source": "generated",
            "provider": provider,
            "file": output.get("file"),
            "prompt": output.get("prompt") or req.get("prompt"),
            "reason": output.get("reason") or req.get("reason"),
            "external_provider": True,
            "forbidden_as_truth": True,
            "metadata": output.get("metadata") or {},
        })
    manifest = {
        "artifact_role": "generated_asset_manifest",
        "generated_asset_manifest_version": 1,
        "request_role": request.get("artifact_role") if request else None,
        "items": items,
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return str(path)


def _load_json(path):
    with Path(path).open(encoding="utf-8") as f:
        return json.load(f)


def _items(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("items") or []
    return []


def _resolve_output_file(file_value, *, base_dir):
    if not file_value:
        raise ValueError("generated output requires file")
    path = Path(file_value)
    if not path.is_absolute():
        path = Path(base_dir) / path
    return path


def write_generated_asset_manifest_from_outputs(request_path, outputs_path, manifest_path, *,
                                                require_files=True):
    """Validate externally generated outputs and write generated_asset_manifest.json.

    This is the runtime boundary for manual/provider adapters. The core does not
    call image/video providers here; it only accepts their completed files.
    """
    request = _load_json(request_path)
    outputs_payload = _load_json(outputs_path)
    base_dir = Path(outputs_path).parent
    outputs = []
    for item in _items(outputs_payload):
        if not isinstance(item, dict):
            raise ValueError("generated output item must be object")
        output = dict(item)
        file_path = _resolve_output_file(output.get("file"), base_dir=base_dir)
        if require_files and not file_path.exists():
            raise FileNotFoundError(str(file_path))
        output["file"] = str(file_path)
        outputs.append(output)
    return write_generated_asset_manifest(request, outputs, manifest_path)


def attach_generated_manifest_to_artifact_manifest(artifact_manifest_path, generated_manifest_path):
    path = Path(artifact_manifest_path)
    payload = _load_json(path) if path.exists() else {}
    payload["generated_asset_manifest"] = str(generated_manifest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return str(path)
