"""Portable run-local asset references and artifact path audit helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from typing import Any, Iterable


WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
POSIX_ABSOLUTE_RE = re.compile(r"^/[^/]")
STRICT_FAMILIES: set[str] = {"material"}


@dataclass(frozen=True)
class AssetRef:
    ref: str
    portable: bool


def _is_windows_path(value: object) -> bool:
    text = str(value)
    return isinstance(value, PureWindowsPath) or bool(WINDOWS_ABSOLUTE_RE.match(text))


def _pure_path_like(run_dir: str | PurePath, value: str | PurePath) -> PurePath:
    if _is_windows_path(run_dir) or _is_windows_path(value):
        return PureWindowsPath(value)
    return PurePosixPath(value)


def _is_relative_to(path: PurePath, base: PurePath) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        if isinstance(path, PureWindowsPath) and isinstance(base, PureWindowsPath):
            try:
                PureWindowsPath(str(path).lower()).relative_to(PureWindowsPath(str(base).lower()))
                return True
            except ValueError:
                return False
        return False


def to_asset_ref(run_dir: str | PurePath, path: str | PurePath) -> AssetRef:
    """Return a run-relative ref for paths under ``run_dir``.

    External absolute paths are preserved so old/current consumers keep working,
    with ``portable=False`` exposed for writers and audits.
    """

    base = _pure_path_like(run_dir, run_dir)
    target = _pure_path_like(run_dir, path)
    if _is_relative_to(target, base):
        rel = target.relative_to(base).as_posix()
        return AssetRef(ref=rel, portable=True)
    return AssetRef(ref=str(path).replace("\\", "/") if isinstance(path, PureWindowsPath) else str(path), portable=False)


def resolve_asset_ref(run_dir: str | PurePath, ref: str | PurePath) -> PurePath:
    """Resolve a persisted asset ref at point of use without touching disk."""

    target = _pure_path_like(run_dir, ref)
    if target.is_absolute():
        return target
    base = _pure_path_like(run_dir, run_dir)
    return base / target


def is_absolute_path_string(value: str) -> bool:
    return bool(WINDOWS_ABSOLUTE_RE.match(value) or POSIX_ABSOLUTE_RE.match(value))


def _iter_json_strings(value: Any, path: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _iter_json_strings(item, f"{path}.{key}")
    elif isinstance(value, list):
        for idx, item in enumerate(value):
            yield from _iter_json_strings(item, f"{path}[{idx}]")


def _load_dictionary_names(root: Path) -> set[str]:
    names: set[str] = set()
    for rel in (
        "docs/interface-contracts/pipeline-product-artifact-dictionary.json",
        "docs/interface-contracts/pipeline-api-dictionary.json",
    ):
        path = root / rel
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            continue
        for item in payload.get("artifacts") or []:
            name = item.get("artifact_name")
            if name:
                names.add(str(name))
        for item in payload.get("interfaces") or []:
            for section in ("request", "response", "trigger"):
                section_payload = item.get(section) or {}
                artifact = section_payload.get("artifact")
                if artifact:
                    names.add(str(artifact))
                for output in section_payload.get("outputs") or []:
                    names.add(str(output))
                for input_name in section_payload.get("inputs") or []:
                    names.add(str(input_name))
    return names


def classify_artifact_family(path: Path, payload: Any, dictionary_names: set[str] | None = None) -> str:
    role = ""
    if isinstance(payload, dict):
        role = str(payload.get("artifact_role") or payload.get("role") or "")
    stem = path.name
    key = f"{stem} {role}".lower()
    if dictionary_names and stem in dictionary_names:
        key = f"{key} {stem.lower()}"
    if any(token in key for token in ("material", "source_media", "source_asset", "inventory")):
        return "material"
    if any(token in key for token in ("audio", "soundtrack", "music", "voiceover", "narration", "subtitle")):
        return "audio"
    if any(token in key for token in ("effect", "remotion", "visual_technique")):
        return "effect"
    if any(token in key for token in ("timeline", "build", "handoff", "edit_decision")):
        return "build"
    return "other"


def build_asset_path_audit(run_dir: str | Path, *, strict: bool = False, repo_root: str | Path | None = None) -> dict:
    run_path = Path(run_dir)
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[1]
    dictionary_names = _load_dictionary_names(root)
    findings = []
    families: dict[str, dict[str, Any]] = {}
    for json_path in sorted(run_path.rglob("*.json")):
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        family = classify_artifact_family(json_path, payload, dictionary_names)
        family_bucket = families.setdefault(family, {"finding_count": 0, "artifacts": {}})
        for value_path, value in _iter_json_strings(payload):
            if not is_absolute_path_string(value):
                continue
            rel_artifact = json_path.relative_to(run_path).as_posix()
            findings.append({
                "artifact": rel_artifact,
                "family": family,
                "json_path": value_path,
                "value": value,
            })
            family_bucket["finding_count"] += 1
            family_bucket["artifacts"][rel_artifact] = family_bucket["artifacts"].get(rel_artifact, 0) + 1
    strict_findings = [item for item in findings if item["family"] in STRICT_FAMILIES]
    return {
        "ok": not strict or not strict_findings,
        "run_dir": str(run_path),
        "strict": strict,
        "strict_families": sorted(STRICT_FAMILIES),
        "finding_count": len(findings),
        "strict_finding_count": len(strict_findings),
        "families": families,
        "findings": findings,
    }
