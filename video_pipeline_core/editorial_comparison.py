"""Bounded, blind A/B semantic comparison artifacts.

This module deliberately stops at reviewer flags and a proposed owner delta.
It does not decide a winner, certify creative quality, or apply editorial state.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
PACKET_ROLE = "editorial_comparison_packet"
FLAGS_ROLE = "editorial_comparison_flags"
KEY_ROLE = "editorial_comparison_owner_key"
VERDICT_ROLE = "owner_comparison_verdict"
DELTA_ROLE = "editorial_comparison_proposed_delta"
ALLOWED_ANSWERS = {"slot_1", "slot_2", "tie", "unknown"}
ALLOWED_FINDING_CLASSES = {"structural_candidate", "taste"}
ALLOWED_OWNER_DECISIONS = {"select_variant", "revise_both", "tie_keep_current"}
TEXT_SUFFIXES = {".json", ".jsonc", ".md", ".markdown", ".txt", ".yaml", ".yml", ".csv", ".tsv"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
VIDEO_SUFFIXES = {".mp4"}
TRANSPORT_SUFFIXES = TEXT_SUFFIXES | IMAGE_SUFFIXES | VIDEO_SUFFIXES
VARIANT_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{2,}")


class ComparisonError(ValueError):
    """Fail-closed comparison error with a stable machine-readable code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise ComparisonError("comparison_input_missing", "cannot read file: " + str(path)) from exc
    return digest.hexdigest()


def _payload_hash(value: dict[str, Any], excluded: set[str] | None = None) -> str:
    payload = dict(value)
    for key in excluded or set():
        payload.pop(key, None)
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _read_json(path: Path, code: str = "comparison_invalid_input") -> dict[str, Any]:
    path = Path(path)
    if not path.is_file():
        raise ComparisonError("comparison_input_missing", "JSON input does not exist: " + str(path))
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ComparisonError(code, "cannot read JSON input: " + str(path)) from exc
    if not isinstance(value, dict):
        raise ComparisonError(code, "JSON input must be an object: " + str(path))
    return value


def _write_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ComparisonError("comparison_output_exists", "immutable artifact already exists: " + str(path))
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    except FileExistsError as exc:
        raise ComparisonError("comparison_output_exists", "immutable artifact already exists: " + str(path)) from exc


def _resolve_path(value: str | Path, base: Path | None = None) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    if base is not None:
        return (Path(base) / path).resolve()
    return (Path.cwd() / path).resolve()


def _require_regular_file(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_file():
        raise ComparisonError("comparison_input_missing", "variant input does not exist: " + str(path))
    if not path.stat().st_mode:
        raise ComparisonError("comparison_input_missing", "variant input is not readable: " + str(path))
    return path.resolve()


def _normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def _scrub_json(value: Any, secrets: set[str]) -> Any:
    sensitive_keys = {
        "backend",
        "maker",
        "makerrationale",
        "rationale",
        "verdict",
        "ownerverdict",
        "chronology",
        "createdat",
        "updatedat",
        "variantid",
        "originalid",
        "originalpath",
        "sourcepath",
        "path",
        "version",
        "status",
    }
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if _normalized(key) in sensitive_keys or _normalized(key).endswith("backend"):
                continue
            result[key] = _scrub_json(item, secrets)
        return result
    if isinstance(value, list):
        return [_scrub_json(item, secrets) for item in value]
    if isinstance(value, str):
        result = value
        for secret in sorted(secrets, key=len, reverse=True):
            if secret:
                result = result.replace(secret, "[neutralized]")
        return re.sub(r"(?i)\b(?:candidate[_ -]?v\d+|v\d+|remotion|backend)\b", "[neutralized]", result)
    return value


def _probe_video(path: Path) -> dict[str, Any]:
    try:
        from .platform_tools import resolve_ffprobe

        proc = subprocess.run(
            [resolve_ffprobe(), "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        value = json.loads(proc.stdout)
    except (OSError, subprocess.SubprocessError, UnicodeError, json.JSONDecodeError) as exc:
        raise ComparisonError("comparison_neutralization_failed", "cannot probe neutral MP4: " + str(path)) from exc
    if not isinstance(value, dict) or not isinstance(value.get("streams"), list) or not value["streams"]:
        raise ComparisonError("comparison_neutralization_failed", "neutral MP4 has no probeable streams: " + str(path))
    return value


def _video_shape(probe: dict[str, Any]) -> dict[str, Any]:
    format_data = probe.get("format") or {}
    try:
        duration = round(float(format_data.get("duration")), 6)
    except (TypeError, ValueError):
        duration = None
    return {
        "duration": duration,
        "stream_count": len(probe.get("streams") or []),
        "streams": [
            {
                key: stream.get(key)
                for key in ("codec_type", "codec_name", "width", "height", "avg_frame_rate", "r_frame_rate")
            }
            for stream in probe.get("streams") or []
        ],
    }


def _neutralize_video(source: Path, destination: Path, original_id: str) -> None:
    from .platform_tools import resolve_ffmpeg

    try:
        subprocess.run(
            [
                resolve_ffmpeg(),
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-fflags",
                "+bitexact",
                "-i",
                str(source),
                "-map",
                "0",
                "-map_metadata",
                "-1",
                "-map_chapters",
                "-1",
                "-c",
                "copy",
                str(destination),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        source_probe = _probe_video(source)
        neutral_probe = _probe_video(destination)
        if _video_shape(source_probe) != _video_shape(neutral_probe):
            raise ComparisonError("comparison_neutralization_failed", "stream-copy MP4 shape changed")
        probe_text = json.dumps(neutral_probe, ensure_ascii=False).lower()
        for marker in ("remotion", "backend", original_id.lower(), source.name.lower(), source.as_posix().lower()):
            if marker and marker in probe_text:
                raise ComparisonError("comparison_blindness_leak", "neutral MP4 contains a blind-leak marker")
    except ComparisonError:
        if destination.exists():
            destination.unlink()
        raise
    except (OSError, subprocess.SubprocessError) as exc:
        if destination.exists():
            destination.unlink()
        raise ComparisonError("comparison_neutralization_failed", "cannot neutralize MP4: " + str(source)) from exc


def _neutralize_image(source: Path, destination: Path) -> None:
    try:
        from PIL import Image

        with Image.open(source) as image:
            image.load()
            output_format = "JPEG" if source.suffix.lower() in {".jpg", ".jpeg"} else image.format
            if not output_format:
                raise ComparisonError("comparison_neutralization_failed", "image format is unknown: " + str(source))
            if output_format.upper() == "JPEG":
                image = image.convert("RGB")
            image.info.clear()
            if output_format.upper() == "JPEG":
                image.save(destination, format="JPEG", quality=100, subsampling=0)
            else:
                image.save(destination, format=output_format)
    except ComparisonError:
        if destination.exists():
            destination.unlink()
        raise
    except (ImportError, OSError, ValueError) as exc:
        if destination.exists():
            destination.unlink()
        raise ComparisonError("comparison_neutralization_failed", "cannot neutralize image: " + str(source)) from exc


def _materialize_neutral_input(source: Path, destination: Path, original_id: str) -> None:
    suffix = source.suffix.lower()
    if suffix not in TRANSPORT_SUFFIXES:
        raise ComparisonError("comparison_unsupported_binary", "unsupported binary review input: " + str(source))
    destination.parent.mkdir(parents=True, exist_ok=True)
    if suffix in TEXT_SUFFIXES:
        try:
            text = source.read_text(encoding="utf-8")
            try:
                value = json.loads(text) if source.suffix.lower() in {".json", ".jsonc"} else None
            except json.JSONDecodeError:
                value = None
            secrets = {original_id, str(source), source.as_posix(), source.name}
            if isinstance(value, dict):
                destination.write_text(
                    json.dumps(_scrub_json(value, secrets), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
            else:
                scrubbed = _scrub_json(text, secrets)
                destination.write_text(str(scrubbed), encoding="utf-8")
            return
        except (OSError, UnicodeError) as exc:
            raise ComparisonError("comparison_neutralization_failed", "cannot neutralize text input: " + str(source)) from exc
    if suffix in IMAGE_SUFFIXES:
        _neutralize_image(source, destination)
        return
    if suffix in VIDEO_SUFFIXES:
        _neutralize_video(source, destination, original_id)
        return
    raise ComparisonError("comparison_unsupported_binary", "unsupported binary review input: " + str(source))


def _validate_rubric(spec: dict[str, Any]) -> tuple[str, list[dict[str, Any]], list[str]]:
    proposition = str(spec.get("proposition") or "").strip()
    rubric = spec.get("rubric")
    if not proposition or not isinstance(rubric, list) or not rubric:
        raise ComparisonError("comparison_invalid_input", "proposition and non-empty rubric are required")
    permitted_global = spec.get("permitted_evidence", [])
    if not isinstance(permitted_global, list) or not all(isinstance(item, str) for item in permitted_global):
        raise ComparisonError("comparison_invalid_input", "permitted_evidence must be a string list")
    normalized = []
    rubric_ids = set()
    permitted = set(permitted_global)
    for item in rubric:
        if not isinstance(item, dict):
            raise ComparisonError("comparison_invalid_input", "rubric items must be objects")
        item_id = str(item.get("id") or item.get("rubric_id") or "").strip()
        question = str(item.get("question") or "").strip()
        if not item_id or not question:
            raise ComparisonError("comparison_invalid_input", "each rubric item needs a stable id and question")
        if item_id in rubric_ids:
            raise ComparisonError("comparison_invalid_input", "rubric IDs must be unique")
        rubric_ids.add(item_id)
        if any(token in question.lower() for token in ("how good", "does it have soul", "overall quality", "rate this film")):
            raise ComparisonError("comparison_invalid_input", "rubric question is too broad")
        if any(key in item for key in ("score", "rating", "scale")):
            raise ComparisonError("comparison_invalid_input", "numeric creative scoring is not supported")
        evidence = item.get("permitted_evidence", item.get("evidence_refs", []))
        if not isinstance(evidence, list) or not all(isinstance(ref, str) and ref for ref in evidence):
            raise ComparisonError("comparison_invalid_input", "rubric permitted evidence must be a string list")
        evidence = sorted(set(evidence))
        permitted.update(evidence)
        normalized.append({"id": item_id, "question": question, "permitted_evidence": evidence})
    if not permitted:
        raise ComparisonError("comparison_invalid_input", "rubric must declare permitted evidence")
    return proposition, normalized, sorted(permitted)


def _blind_marker_present(value: str, marker: str) -> bool:
    lower = value.lower()
    marker_lower = marker.lower()
    if re.fullmatch(r"[a-z0-9_.:-]+", marker_lower):
        return re.search(r"(?<![a-z0-9_.:-])" + re.escape(marker_lower) + r"(?![a-z0-9_.:-])", lower) is not None
    return marker_lower in lower


def _assert_blind_text(value: Any, forbidden: set[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _assert_blind_text(key, forbidden)
            _assert_blind_text(item, forbidden)
    elif isinstance(value, list):
        for item in value:
            _assert_blind_text(item, forbidden)
    elif isinstance(value, str):
        if any(_blind_marker_present(value, token) for token in forbidden):
            raise ComparisonError("comparison_blindness_leak", "reviewer-facing content contains a blind-leak marker")


def _ensure_empty_output(output_dir: Path) -> None:
    if output_dir.exists():
        if not output_dir.is_dir() or any(output_dir.iterdir()):
            raise ComparisonError("comparison_output_exists", "output path already contains artifacts: " + str(output_dir))


def _rollback_output(output_dir: Path, existed_before: bool) -> None:
    if not output_dir.exists():
        return
    if not existed_before:
        shutil.rmtree(output_dir, ignore_errors=True)
        return
    for child in list(output_dir.iterdir()):
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=True)
        else:
            try:
                child.unlink()
            except OSError:
                pass


def build_comparison_packet(
    decision_id: str,
    proposition_rubric: dict[str, Any],
    variants: list[dict[str, Any]],
    output_dir: Path,
    seed: int | None = None,
) -> dict[str, Any]:
    if len(variants) != 2:
        raise ComparisonError("comparison_requires_exactly_two_variants", "exactly two variants are required")
    if not str(decision_id).strip():
        raise ComparisonError("comparison_invalid_input", "decision_id is required")
    output_dir = Path(output_dir)
    output_existed = output_dir.exists()
    _ensure_empty_output(output_dir)
    proposition, rubric, permitted_evidence = _validate_rubric(proposition_rubric)
    normalized_variants = []
    ids = set()
    for variant in variants:
        if not isinstance(variant, dict):
            raise ComparisonError("comparison_invalid_input", "variants must be objects")
        variant_id = str(variant.get("id") or "").strip()
        if not variant_id or variant_id in ids:
            raise ComparisonError("comparison_invalid_input", "variant IDs must be unique and non-empty")
        if VARIANT_ID_RE.fullmatch(variant_id) is None:
            raise ComparisonError("comparison_invalid_input", "variant IDs must be at least 3 token-safe characters")
        ids.add(variant_id)
        source = _require_regular_file(variant.get("path") or "")
        if source.suffix.lower() not in TRANSPORT_SUFFIXES:
            raise ComparisonError("comparison_unsupported_binary", "unsupported binary review input: " + str(source))
        normalized_variants.append({"id": variant_id, "path": source, "sha256": sha256_file(source)})

    leak_markers = set(ids)
    leak_markers.update({"remotion", "backend", "maker rationale", "owner verdict", "chronology"})
    _assert_blind_text(proposition_rubric, leak_markers)
    order = [0, 1]
    (random.Random(seed) if seed is not None else random.SystemRandom()).shuffle(order)
    slot_variants = {f"slot_{slot + 1}": normalized_variants[index] for slot, index in enumerate(order)}

    try:
        reviewer_inputs = output_dir / "reviewer" / "inputs"
        slots = []
        key_variants = []
        slot_assignment = {}
        for slot in ("slot_1", "slot_2"):
            variant = slot_variants[slot]
            suffix = variant["path"].suffix.lower() or ".bin"
            neutral_path = reviewer_inputs / f"{slot}{suffix}"
            _materialize_neutral_input(variant["path"], neutral_path, variant["id"])
            neutral_hash = sha256_file(neutral_path)
            slots.append({"slot": slot, "path": neutral_path.relative_to(output_dir).as_posix(), "sha256": neutral_hash})
            slot_assignment[slot] = variant["id"]
            key_variants.append(
                {
                    "id": variant["id"],
                    "original_path": str(variant["path"]),
                    "original_sha256": variant["sha256"],
                    "slot": slot,
                    "neutralized_sha256": neutral_hash,
                }
            )

        packet = {
            "artifact_role": PACKET_ROLE,
            "schema_version": SCHEMA_VERSION,
            "decision_id": str(decision_id),
            "decision_mode": "ab_comparison",
            "authority": "flag_only",
            "proposition": proposition,
            "rubric": rubric,
            "permitted_evidence": permitted_evidence,
            "slots": slots,
            "packet_payload_sha256": "",
            "human_creative_approval": False,
            "final_delivery_claimed": False,
        }
        packet["packet_payload_sha256"] = _payload_hash(packet, {"packet_payload_sha256"})
        packet_path = output_dir / "reviewer" / "comparison_packet.json"
        _write_json_exclusive(packet_path, packet)

        key = {
            "artifact_role": KEY_ROLE,
            "schema_version": SCHEMA_VERSION,
            "decision_id": str(decision_id),
            "slot_assignment": slot_assignment,
            "variants": key_variants,
        }
        key_path = output_dir / "owner" / "comparison_key.json"
        _write_json_exclusive(key_path, key)

        flags_template = {
            "artifact_role": FLAGS_ROLE,
            "schema_version": SCHEMA_VERSION,
            "decision_id": str(decision_id),
            "packet_path": "comparison_packet.json",
            "packet_sha256": sha256_file(packet_path),
            "authority": "flag_only",
            "answers": [],
            "findings": [],
            "finding_schema": {
                "required_fields": ["finding_id", "rubric_id", "class", "statement", "evidence_refs"],
                "class_vocabulary": sorted(ALLOWED_FINDING_CLASSES),
                "evidence_refs": "non-empty list of permitted evidence references",
            },
            "human_creative_approval": False,
            "final_delivery_claimed": False,
        }
        flags_template_path = output_dir / "reviewer" / "editorial_comparison_flags.template.json"
        _write_json_exclusive(flags_template_path, flags_template)

        owner_template = {
            "artifact_role": VERDICT_ROLE,
            "schema_version": SCHEMA_VERSION,
            "reviewer_role": "human_owner",
            "decision_id": str(decision_id),
            "decision": "PENDING",
            "rationale": "",
            "packet_path": "../reviewer/comparison_packet.json",
            "flags_path": "../reviewer/editorial_comparison_flags.template.json",
            "human_creative_approval": False,
            "final_delivery_claimed": False,
        }
        owner_template_path = output_dir / "owner" / "owner_verdict.template.json"
        _write_json_exclusive(owner_template_path, owner_template)

        manifest = {
            "artifact_role": "editorial_comparison_manifest",
            "schema_version": SCHEMA_VERSION,
            "decision_id": str(decision_id),
            "packet_path": packet_path.relative_to(output_dir).as_posix(),
            "packet_sha256": sha256_file(packet_path),
            "key_path": key_path.relative_to(output_dir).as_posix(),
            "key_sha256": sha256_file(key_path),
            "reviewer_slots": slots,
            "human_creative_approval": False,
            "final_delivery_claimed": False,
        }
        manifest_path = output_dir / "manifest.json"
        _write_json_exclusive(manifest_path, manifest)
        return {
            "status": "PASS",
            "decision_id": str(decision_id),
            "packet_path": str(packet_path),
            "key_path": str(key_path),
            "flags_template_path": str(flags_template_path),
            "owner_template_path": str(owner_template_path),
            "manifest_path": str(manifest_path),
            "packet_sha256": sha256_file(packet_path),
            "key_sha256": sha256_file(key_path),
        }
    except Exception:
        _rollback_output(output_dir, output_existed)
        raise


def _load_packet(packet_path: Path) -> dict[str, Any]:
    packet = _read_json(packet_path)
    if packet.get("artifact_role") != PACKET_ROLE or packet.get("schema_version") != SCHEMA_VERSION:
        raise ComparisonError("comparison_invalid_authority", "invalid comparison packet role or schema")
    if packet.get("authority") != "flag_only":
        raise ComparisonError("comparison_invalid_authority", "comparison packet authority must be flag_only")
    if packet.get("human_creative_approval") is not False or packet.get("final_delivery_claimed") is not False:
        raise ComparisonError("comparison_invalid_authority", "approval flags must remain false")
    expected = packet.get("packet_payload_sha256")
    if expected != _payload_hash(packet, {"packet_payload_sha256"}):
        raise ComparisonError("comparison_packet_hash_mismatch", "comparison packet payload hash mismatch")
    root = Path(packet_path).resolve().parent.parent
    slots = packet.get("slots")
    if not isinstance(slots, list) or len(slots) != 2:
        raise ComparisonError("comparison_invalid_input", "packet must contain exactly two slots")
    for item in slots:
        if not isinstance(item, dict) or item.get("slot") not in {"slot_1", "slot_2"}:
            raise ComparisonError("comparison_invalid_input", "packet slot is invalid")
        input_path = root / str(item.get("path") or "")
        if not input_path.is_file() or sha256_file(input_path) != item.get("sha256"):
            raise ComparisonError("comparison_packet_hash_mismatch", "packet input hash mismatch")
    return packet


def _walk_forbidden(value: Any, path: str = "") -> None:
    allowed_fixed = {_normalized("human_creative_approval"), _normalized("final_delivery_claimed")}
    forbidden_key_parts = (
        "winner",
        "verdict",
        "approve",
        "reject",
        "delivery",
        "canonical",
        "promot",
        "mutat",
        "applydelta",
        "selectedvariant",
        "preferredvariant",
        "recommend",
        "score",
    )
    forbidden_value_parts = ("pass", "fail", "winner", "approved", "rejected", "delivery", "canonical", "promot", "mutat")
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = _normalized(key)
            if normalized_key in allowed_fixed:
                if item is not False:
                    raise ComparisonError("comparison_forbidden_verdict", f"{path}/{key} must remain false")
                continue
            if normalized_key == "ownerverdict" and str(item).upper() == "PENDING":
                continue
            if any(part in normalized_key for part in forbidden_key_parts):
                raise ComparisonError("comparison_forbidden_verdict", f"forbidden authority field: {path}/{key}")
            _walk_forbidden(item, f"{path}/{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _walk_forbidden(item, f"{path}/{index}")
    elif isinstance(value, str):
        if any(part in value.lower() for part in forbidden_value_parts):
            if path.endswith("/packet_path") or path.endswith("/flags_path"):
                return
            raise ComparisonError("comparison_forbidden_verdict", f"forbidden authority value at {path}")


def _rubric_map(packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rubric = packet.get("rubric")
    if not isinstance(rubric, list):
        raise ComparisonError("comparison_invalid_input", "packet rubric is invalid")
    result = {}
    for item in rubric:
        if not isinstance(item, dict) or not item.get("id"):
            raise ComparisonError("comparison_invalid_input", "packet rubric item is invalid")
        result[str(item["id"])] = item
    return result


def _evidence_is_permitted(ref: str, rubric: dict[str, Any], packet: dict[str, Any]) -> bool:
    permitted = set(packet.get("permitted_evidence") or [])
    permitted.update(rubric.get("permitted_evidence") or [])
    return ref in permitted


def _validate_evidence(refs: Any, rubric: dict[str, Any], packet: dict[str, Any], required: bool) -> list[str]:
    if not isinstance(refs, list) or not all(isinstance(ref, str) and ref for ref in refs):
        raise ComparisonError("comparison_evidence_required", "evidence_refs must be a non-empty permitted string list")
    if required and not refs:
        raise ComparisonError("comparison_evidence_required", "non-UNKNOWN claim requires evidence")
    if any(not _evidence_is_permitted(ref, rubric, packet) for ref in refs):
        raise ComparisonError("comparison_evidence_required", "evidence reference is not permitted by the packet")
    return refs


def validate_flags(packet_path: Path, flags: dict[str, Any] | Path) -> dict[str, Any]:
    packet_path = Path(packet_path).resolve()
    packet = _load_packet(packet_path)
    flags_path = Path(flags).resolve() if isinstance(flags, (str, Path)) else None
    flags_data = _read_json(flags_path) if flags_path is not None else flags
    if not isinstance(flags_data, dict) or flags_data.get("artifact_role") != FLAGS_ROLE:
        raise ComparisonError("comparison_invalid_authority", "invalid reviewer flags role")
    _walk_forbidden(flags_data)
    if flags_data.get("schema_version") != SCHEMA_VERSION or flags_data.get("authority") != "flag_only":
        raise ComparisonError("comparison_invalid_authority", "reviewer flags must be schema 1 and flag_only")
    if flags_data.get("decision_id") != packet.get("decision_id"):
        raise ComparisonError("comparison_packet_hash_mismatch", "flags decision does not match packet")
    if _resolve_path(str(flags_data.get("packet_path") or ""), flags_path.parent if flags_path else None) != packet_path:
        raise ComparisonError("comparison_packet_hash_mismatch", "flags are bound to a different packet path")
    if flags_data.get("packet_sha256") != sha256_file(packet_path):
        raise ComparisonError("comparison_packet_hash_mismatch", "flags packet hash does not match packet")
    if flags_data.get("human_creative_approval") is not False or flags_data.get("final_delivery_claimed") is not False:
        raise ComparisonError("comparison_invalid_authority", "reviewer flags approval fields must remain false")

    rubric_by_id = _rubric_map(packet)
    answers = flags_data.get("answers")
    if not isinstance(answers, list) or len(answers) != len(rubric_by_id) or any(not isinstance(item, dict) for item in answers):
        raise ComparisonError("comparison_invalid_answer", "one answer is required for each rubric item")
    answer_ids = [item.get("rubric_id") for item in answers]
    if any(not isinstance(item_id, str) or not item_id for item_id in answer_ids):
        raise ComparisonError("comparison_invalid_answer", "answer rubric_id is invalid")
    if len(set(answer_ids)) != len(answer_ids) or set(answer_ids) != set(rubric_by_id):
        raise ComparisonError("comparison_invalid_answer", "one answer is required for each rubric item")
    for answer in answers:
        if not isinstance(answer, dict) or answer.get("rubric_id") not in rubric_by_id:
            raise ComparisonError("comparison_invalid_answer", "answer rubric_id is invalid")
        value = answer.get("answer")
        if value not in ALLOWED_ANSWERS:
            raise ComparisonError("comparison_invalid_answer", "answer vocabulary is not allowed")
        _validate_evidence(answer.get("evidence_refs", []), rubric_by_id[answer["rubric_id"]], packet, value != "unknown")

    findings = flags_data.get("findings", [])
    if not isinstance(findings, list):
        raise ComparisonError("comparison_invalid_finding_class", "findings must be a list")
    for finding in findings:
        if not isinstance(finding, dict) or finding.get("rubric_id") not in rubric_by_id:
            raise ComparisonError("comparison_invalid_finding_class", "finding rubric_id is invalid")
        if finding.get("class") not in ALLOWED_FINDING_CLASSES:
            raise ComparisonError("comparison_invalid_finding_class", "finding class is not allowed")
        if not str(finding.get("finding_id") or "").strip() or not str(finding.get("statement") or "").strip():
            raise ComparisonError("comparison_invalid_finding_class", "finding id and statement are required")
        _validate_evidence(finding.get("evidence_refs", []), rubric_by_id[finding["rubric_id"]], packet, True)
    return {
        "status": "PASS",
        "artifact_role": FLAGS_ROLE,
        "decision_id": packet["decision_id"],
        "packet_path": str(packet_path),
        "packet_sha256": sha256_file(packet_path),
        "flags_sha256": sha256_file(flags_path) if flags_path else None,
        "human_creative_approval": False,
        "final_delivery_claimed": False,
    }


def _verify_owner_key(packet: dict[str, Any], key_path: Path) -> dict[str, Any]:
    key = _read_json(key_path)
    if key.get("artifact_role") != KEY_ROLE or key.get("schema_version") != SCHEMA_VERSION:
        raise ComparisonError("comparison_owner_key_mismatch", "owner key role or schema is invalid")
    if key.get("decision_id") != packet.get("decision_id"):
        raise ComparisonError("comparison_owner_key_mismatch", "owner key decision does not match packet")
    variants = key.get("variants")
    assignment = key.get("slot_assignment")
    packet_hashes = {item.get("sha256") for item in packet.get("slots", [])}
    if not isinstance(variants, list) or len(variants) != 2 or not isinstance(assignment, dict):
        raise ComparisonError("comparison_owner_key_mismatch", "owner key variant mapping is invalid")
    if set(assignment) != {"slot_1", "slot_2"} or {item.get("slot") for item in variants} != set(assignment):
        raise ComparisonError("comparison_owner_key_mismatch", "owner key slot mapping is invalid")
    if {item.get("id") for item in variants} != set(assignment.values()):
        raise ComparisonError("comparison_owner_key_mismatch", "owner key variant IDs are inconsistent")
    if any(item.get("neutralized_sha256") not in packet_hashes for item in variants):
        raise ComparisonError("comparison_owner_key_mismatch", "owner key does not match packet input hashes")
    return key


def _resolve_referenced_file(value: Any, owner_file: Path) -> Path:
    if not isinstance(value, str) or not value:
        return Path("")
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (owner_file.parent / path).resolve()


def build_owner_delta(
    packet_path: Path,
    key_path: Path,
    flags_path: Path,
    verdict_path: Path | None,
    base_state_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    if verdict_path is None or not Path(verdict_path).is_file():
        raise ComparisonError("comparison_human_verdict_required", "an explicit Human owner verdict is required")
    packet_path = Path(packet_path).resolve()
    key_path = Path(key_path).resolve()
    flags_path = Path(flags_path).resolve()
    verdict_path = Path(verdict_path).resolve()
    base_state_path = Path(base_state_path).resolve()
    output_path = Path(output_path)
    packet = _load_packet(packet_path)
    key = _verify_owner_key(packet, key_path)
    flags_result = validate_flags(packet_path, flags_path)
    verdict = _read_json(verdict_path)
    if verdict.get("artifact_role") != VERDICT_ROLE or verdict.get("schema_version") != SCHEMA_VERSION:
        raise ComparisonError("comparison_human_verdict_required", "verdict role or schema is invalid")
    if verdict.get("reviewer_role") != "human_owner":
        raise ComparisonError("comparison_human_verdict_required", "verdict must identify reviewer_role=human_owner")
    if verdict.get("decision_id") != packet.get("decision_id"):
        raise ComparisonError("comparison_human_verdict_required", "verdict decision does not match packet")
    decision = verdict.get("decision")
    if decision not in ALLOWED_OWNER_DECISIONS:
        raise ComparisonError("comparison_forbidden_verdict", "owner decision is not allowed")
    if not str(verdict.get("rationale") or "").strip():
        raise ComparisonError("comparison_human_verdict_required", "Human verdict rationale is required")
    if _resolve_referenced_file(verdict.get("packet_path"), verdict_path) != packet_path:
        raise ComparisonError("comparison_packet_hash_mismatch", "verdict packet reference does not match")
    if verdict.get("packet_sha256") != sha256_file(packet_path):
        raise ComparisonError("comparison_packet_hash_mismatch", "verdict packet hash does not match")
    if _resolve_referenced_file(verdict.get("flags_path"), verdict_path) != flags_path:
        raise ComparisonError("comparison_packet_hash_mismatch", "verdict flags reference does not match")
    if verdict.get("flags_sha256") != sha256_file(flags_path):
        raise ComparisonError("comparison_packet_hash_mismatch", "verdict flags hash does not match")
    if not base_state_path.is_file() or verdict.get("base_state_path") not in {str(base_state_path), base_state_path.as_posix()}:
        raise ComparisonError("comparison_base_state_hash_mismatch", "verdict base state path is not current")
    base_hash = sha256_file(base_state_path)
    if verdict.get("base_state_sha256") != base_hash:
        raise ComparisonError("comparison_base_state_hash_mismatch", "verdict base state hash is stale")
    selected_variant = verdict.get("selected_variant_id")
    if decision == "select_variant":
        if selected_variant not in {item.get("id") for item in key["variants"]}:
            raise ComparisonError("comparison_owner_key_mismatch", "selected variant is not in owner key")
    elif selected_variant is not None:
        raise ComparisonError("comparison_forbidden_verdict", "non-selection verdict cannot select a variant")
    if output_path.exists():
        raise ComparisonError("comparison_output_exists", "proposed delta already exists: " + str(output_path))

    decision_record = {
        "decision": decision,
        "selected_variant_id": selected_variant,
        "rationale": str(verdict["rationale"]),
        "packet_sha256": sha256_file(packet_path),
        "flags_sha256": sha256_file(flags_path),
        "comparison_key_sha256": sha256_file(key_path),
        "base_state_sha256": base_hash,
        "status": "PROPOSED_ONLY",
    }
    delta = {
        "artifact_role": DELTA_ROLE,
        "schema_version": SCHEMA_VERSION,
        "decision_id": packet["decision_id"],
        "operation_result": "proposed_only",
        "base_state_path": str(base_state_path),
        "base_state_sha256": base_hash,
        "comparison_key_path": str(key_path),
        "comparison_key_sha256": sha256_file(key_path),
        "packet_path": str(packet_path),
        "packet_sha256": sha256_file(packet_path),
        "flags_path": str(flags_path),
        "flags_sha256": flags_result["flags_sha256"],
        "changes": {"operational_state": {"comparative_decisions": {packet["decision_id"]: decision_record}}},
        "human_creative_approval": False,
        "final_delivery_claimed": False,
    }
    _write_json_exclusive(output_path, delta)
    return {"status": "PASS", "operation": "build-owner-delta", "path": str(output_path), "proposed_only": True}


# Short aliases used by the thin CLI and callers that prefer command names.
build_packet = build_comparison_packet
