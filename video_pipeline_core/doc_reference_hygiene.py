"""Lightweight docs/reference hygiene checks for route facts."""

from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path
from typing import Iterable


REFERENCE_SURFACES = [
    "docs/INDEX.md",
    "docs/branch-contract-registry.md",
    "docs/branch-contract-registry.json",
    "docs/pipeline-decision-tree.md",
    "docs/video-pipeline-operating-map.md",
    "docs/reference-repos-map.md",
]

EXEMPT_ROOT_DOCS = {
    "docs/build-capability-alignment.md": "historical_or_design_note",
    "docs/capcut-pipeline-integration-design.md": "reference_only_backend_design",
    "docs/dashboard-node-skill-output-spec.md": "reference_only_dashboard_design",
    "docs/windows-native-migration-spec.md": "historical_migration_record",
}

ENTRY_SURFACES = {
    "AGENTS.md": {"OPERATIONAL_ENTRY_POINTER": "RUNBOOK.md"},
    "RUNBOOK.md": {
        "OPERATIONAL_ENTRY": "RUNBOOK",
        "CURRENT_HANDOFF_POINTER": "HANDOFF_CURRENT.md",
    },
    "HANDOFF_CURRENT.md": {"DOCUMENT_ROLE": "CURRENT_HANDOFF"},
    "docs/START_HERE_VIDEO_PIPELINE.md": {"DOCUMENT_ROLE": "ORIENTATION"},
    "docs/INDEX.md": {"DOCUMENT_ROLE": "MAP"},
}

ENTRY_MARKER_PATTERN = re.compile(r"<!--\s*([A-Z_]+):\s*([^>]+?)\s*-->")
RUNBOOK_STATE_TOKEN_PATTERN = re.compile(r"\b(?:WAITING|STOPPED|ACTIVE)(?:_[A-Z0-9]+)+\b")
HANDOFF_STATE_START = "<!-- HANDOFF_STATE_START -->"
HANDOFF_STATE_END = "<!-- HANDOFF_STATE_END -->"
HANDOFF_ALLOWED_KEYS = {
    "artifact_role",
    "version",
    "updated_at",
    "state",
    "active_work_order",
    "active_spec",
    "active_skill",
    "active_run_root",
    "authoritative_state_artifact",
    "authoritative_state_sha256",
    "authoritative_state_field",
    "campaign_status_artifact",
    "campaign_status_field",
    "next_actions",
    "do_not_do",
    "human_creative_approval",
    "final_delivery_claimed",
    "review_packet",
}
HANDOFF_EXTENSION_KEYS = {
    "authoritative_state_sha256",
    "campaign_status_artifact",
    "campaign_status_field",
    "review_packet",
}
HANDOFF_LEGACY_KEYS = HANDOFF_ALLOWED_KEYS - HANDOFF_EXTENSION_KEYS
HANDOFF_PATH_FIELDS = (
    "active_work_order",
    "active_spec",
    "active_skill",
    "active_run_root",
)
HANDOFF_IDLE_NULL_FIELDS = HANDOFF_PATH_FIELDS + (
    "authoritative_state_artifact",
    "authoritative_state_field",
    "campaign_status_artifact",
    "campaign_status_field",
)
MACHINE_KEYS_OUTSIDE_HANDOFF = ("active_work_order", "authoritative_state_artifact", "ACTIVE_WORK_ORDER")


def _normalize_doc(rel: str | Path) -> str:
    return str(rel).replace("\\", "/")


def _read_utf8(root: Path, rel: str | Path) -> str:
    return (root / rel).read_text(encoding="utf-8")


def _resolve_repo_path(root: Path, value: object) -> Path | None:
    if value is None or not isinstance(value, str) or not value.strip():
        return None
    try:
        root_resolved = root.resolve()
        candidate = (root / value).resolve(strict=False)
        candidate.relative_to(root_resolved)
    except (OSError, RuntimeError, ValueError):
        return None
    return candidate


def parse_handoff_state(text: str) -> tuple[dict[str, object] | None, list[str]]:
    start_count = text.count(HANDOFF_STATE_START)
    end_count = text.count(HANDOFF_STATE_END)

    if start_count == 0 or end_count == 0:
        return None, ["handoff_block_missing"]
    if start_count != 1 or end_count != 1:
        return None, ["handoff_block_duplicate"]

    start_index = text.index(HANDOFF_STATE_START) + len(HANDOFF_STATE_START)
    end_index = text.index(HANDOFF_STATE_END)
    if end_index < start_index:
        return None, ["handoff_json_invalid"]

    payload_text = text[start_index:end_index].strip()
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        return None, ["handoff_json_invalid"]

    if not isinstance(payload, dict):
        return None, ["handoff_json_invalid"]

    errors: set[str] = set()
    unknown_keys = sorted(set(payload) - HANDOFF_ALLOWED_KEYS)
    errors.update(f"handoff_unknown_key:{key}" for key in unknown_keys)

    missing_keys = HANDOFF_ALLOWED_KEYS - set(payload)
    legacy_idle = payload.get("state") == "IDLE" and not (
        missing_keys - HANDOFF_EXTENSION_KEYS
    )
    if missing_keys and not legacy_idle:
        errors.add("handoff_json_invalid")

    if payload.get("artifact_role") != "current_handoff_state":
        errors.add("handoff_json_invalid")
    if payload.get("version") != 1:
        errors.add("handoff_json_invalid")
    if not isinstance(payload.get("state"), str):
        errors.add("handoff_json_invalid")
    if not isinstance(payload.get("next_actions"), list):
        errors.add("handoff_json_invalid")
    if not isinstance(payload.get("do_not_do"), list):
        errors.add("handoff_json_invalid")
    if not isinstance(payload.get("human_creative_approval"), bool):
        errors.add("handoff_json_invalid")
    if not isinstance(payload.get("final_delivery_claimed"), bool):
        errors.add("handoff_json_invalid")

    return payload, sorted(errors)


def evaluate_entry_contract(repo_root: str | Path) -> dict[str, object]:
    """Validate exact markers and the one HANDOFF JSON block."""

    root = Path(repo_root)
    texts = {surface: _read_utf8(root, surface) for surface in ENTRY_SURFACES}
    errors: set[str] = set()
    markers_by_surface: dict[str, dict[str, list[str]]] = {}
    allowed_surfaces_by_key: dict[str, set[str]] = {}
    for surface, expected_markers in ENTRY_SURFACES.items():
        for key in expected_markers:
            allowed_surfaces_by_key.setdefault(key, set()).add(surface)

    for surface, text in texts.items():
        surface_markers: dict[str, list[str]] = {}
        for match in ENTRY_MARKER_PATTERN.finditer(text):
            key = match.group(1)
            value = match.group(2).strip()
            surface_markers.setdefault(key, []).append(value)
            allowed_surfaces = allowed_surfaces_by_key.get(key)
            if allowed_surfaces is not None and surface not in allowed_surfaces:
                errors.add(f"entry_marker_wrong_surface:{surface}:{key}")
        markers_by_surface[surface] = surface_markers

        if surface != "HANDOFF_CURRENT.md":
            for machine_key in MACHINE_KEYS_OUTSIDE_HANDOFF:
                if machine_key in text:
                    errors.add(f"entry_machine_key_outside_handoff:{surface}:{machine_key}")

        if surface == "RUNBOOK.md":
            for token in RUNBOOK_STATE_TOKEN_PATTERN.findall(text):
                errors.add(f"entry_runbook_state_token:{token}")

    for surface, expected_markers in ENTRY_SURFACES.items():
        actual_markers = markers_by_surface.get(surface, {})
        for key, expected_value in expected_markers.items():
            values = actual_markers.get(key, [])
            if not values:
                errors.add(f"entry_marker_missing:{surface}:{key}")
                continue
            if len(values) > 1:
                errors.add(f"entry_marker_duplicate:{surface}:{key}")
            if any(value != expected_value for value in values):
                errors.add(f"entry_marker_wrong_value:{surface}:{key}")

    handoff, handoff_errors = parse_handoff_state(texts["HANDOFF_CURRENT.md"])
    errors.update(handoff_errors)

    if handoff is not None:
        state = handoff.get("state")
        if state == "IDLE":
            if any(handoff.get(field) is not None for field in HANDOFF_IDLE_NULL_FIELDS):
                errors.add("handoff_idle_has_active_fields")
        elif isinstance(state, str):
            for field in HANDOFF_PATH_FIELDS:
                resolved = _resolve_repo_path(root, handoff.get(field))
                if handoff.get(field) is not None and (resolved is None or not resolved.exists()):
                    errors.add(f"handoff_path_missing:{field}")

            if handoff.get("state") != "IDLE":
                authoritative_artifact = handoff.get("authoritative_state_artifact")
                authoritative_field = handoff.get("authoritative_state_field")
                authoritative_path = _resolve_repo_path(root, authoritative_artifact)
                if authoritative_path is None or not isinstance(authoritative_field, str) or not authoritative_field:
                    errors.add("handoff_state_authority_missing")
                elif not authoritative_path.exists():
                    errors.add("handoff_state_authority_missing")
                else:
                    try:
                        authority_bytes = authoritative_path.read_bytes()
                        authority_payload = json.loads(authority_bytes.decode("utf-8"))
                    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                        errors.add("handoff_state_authority_missing")
                    else:
                        if not isinstance(authority_payload, dict) or authoritative_field not in authority_payload:
                            errors.add("handoff_state_authority_missing")
                        expected_hash = handoff.get("authoritative_state_sha256")
                        if not isinstance(expected_hash, str) or not expected_hash:
                            errors.add("handoff_state_authority_hash_missing")
                        elif hashlib.sha256(authority_bytes).hexdigest() != expected_hash:
                            errors.add("handoff_state_authority_hash_mismatch")

                campaign_artifact = handoff.get("campaign_status_artifact")
                campaign_field = handoff.get("campaign_status_field")
                campaign_path = _resolve_repo_path(root, campaign_artifact)
                if campaign_path is None or not isinstance(campaign_field, str) or not campaign_field:
                    errors.add("handoff_campaign_state_missing")
                elif not campaign_path.exists():
                    errors.add("handoff_campaign_state_missing")
                else:
                    try:
                        campaign_payload = json.loads(campaign_path.read_text(encoding="utf-8"))
                    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                        campaign_payload = None
                    if not isinstance(campaign_payload, dict) or campaign_field not in campaign_payload:
                        errors.add("handoff_campaign_state_missing")
                    elif campaign_payload[campaign_field] != state:
                        errors.add("handoff_campaign_state_mismatch")

                review_packet = handoff.get("review_packet")
                if review_packet is not None:
                    if not isinstance(review_packet, dict):
                        errors.add("handoff_review_packet_invalid")
                    else:
                        review_path = _resolve_repo_path(root, review_packet.get("path"))
                        review_hash = review_packet.get("sha256")
                        if review_path is None or not isinstance(review_hash, str) or not review_hash:
                            errors.add("handoff_review_packet_missing")
                        elif not review_path.exists():
                            errors.add("handoff_review_packet_missing")
                        elif hashlib.sha256(review_path.read_bytes()).hexdigest() != review_hash:
                            errors.add("handoff_review_packet_hash_mismatch")

    return {
        "artifact_role": "entry_contract_report",
        "version": 1,
        "ok": not errors,
        "errors": sorted(errors),
        "handoff": handoff,
        "scanned_surfaces": list(ENTRY_SURFACES),
    }


def evaluate_doc_reference_hygiene(
    *,
    repo_root: str | Path,
    root_docs: Iterable[str | Path],
    reference_texts: Iterable[str],
    exemptions: Iterable[str | Path] | dict[str, str],
) -> dict[str, object]:
    refs = "\n".join(reference_texts)
    exempt_map = (
        {_normalize_doc(key): value for key, value in exemptions.items()}
        if isinstance(exemptions, dict)
        else {_normalize_doc(item): "explicit_exemption" for item in exemptions}
    )
    referenced: list[str] = []
    exempted: list[dict[str, str]] = []
    orphan: list[str] = []

    for doc in sorted({_normalize_doc(item) for item in root_docs}):
        if doc == "docs/INDEX.md":
            referenced.append(doc)
            continue
        if doc in exempt_map:
            exempted.append({"path": doc, "classification": str(exempt_map[doc])})
            continue
        basename = Path(doc).name
        if doc in refs or basename in refs:
            referenced.append(doc)
            continue
        orphan.append(doc)

    return {
        "artifact_role": "doc_reference_hygiene_report",
        "version": 1,
        "ok": not orphan,
        "classified_count": len(referenced) + len(exempted) + len(orphan),
        "referenced_docs": referenced,
        "exempted_docs": exempted,
        "orphan_canonical_docs": orphan,
    }


def evaluate_current_doc_reference_hygiene(repo_root: str | Path) -> dict[str, object]:
    root = Path(repo_root)
    root_docs = [f"docs/{path.name}" for path in (root / "docs").glob("*.md")]
    reference_texts = [
        _read_utf8(root, rel)
        for rel in REFERENCE_SURFACES
        if (root / rel).exists()
    ]
    report = evaluate_doc_reference_hygiene(
        repo_root=root,
        root_docs=root_docs,
        reference_texts=reference_texts,
        exemptions=EXEMPT_ROOT_DOCS,
    )
    entry_contract = evaluate_entry_contract(root)
    report["entry_contract"] = entry_contract
    report["ok"] = bool(report["ok"]) and bool(entry_contract["ok"])
    return report


def write_doc_reference_hygiene_report(repo_root: str | Path, out: str | Path) -> dict[str, object]:
    report = evaluate_current_doc_reference_hygiene(repo_root)
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
