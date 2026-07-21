"""Build a private, source-only Agent-only Technical Preview package."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Iterable
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


class PackageError(RuntimeError):
    """Raised when a release would violate the bounded package contract."""


REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_STATUS = "PRIVATE_AGENT_ONLY_TECHNICAL_PREVIEW_V1"
LICENSE_STATUS = "owner_decision_pending"

INCLUDE_FILES = {
    ".env.example",
    "AGENTS.md",
    "CLAUDE.md",
    "HANDOFF_CURRENT.md",
    "README.md",
    "RUNBOOK.md",
    "THIRD_PARTY_NOTICES.md",
    "requirements.txt",
    "runtime.py",
    "video_pipeline.py",
    "video_tools.py",
}
INCLUDE_ROOTS = {
    "dashboard",
    "docs",
    "examples",
    "skills",
    "tests",
    "tools",
    "video_pipeline_core",
    "distribution/agent-skill",
}
EXCLUDED_SEGMENTS = {
    ".agents",
    ".cache",
    ".claude",
    ".codex-remote-attachments",
    ".git",
    ".graphify-corpus",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tmp",
    ".understand-anything",
    ".venv",
    ".venv_voxcpm",
    ".vscode",
    "__pycache__",
    "archive",
    "deliveries",
    "graphify-out",
    "reference repo",
    "runs",
    "scratch",
    "output",
    "tmp_runs",
    "workbench_proxy",
    "workbench_thumbs",
}
MEDIA_SUFFIXES = {
    ".avi",
    ".gif",
    ".heic",
    ".jpeg",
    ".jpg",
    ".m4a",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".png",
    ".wav",
    ".webm",
    ".webp",
}
SECRET_PATH_SUFFIXES = {".key", ".pem", ".p12", ".pfx"}
HANDOFF_PATH_FIELDS = (
    "active_work_order",
    "active_spec",
    "active_skill",
    "active_run_root",
    "authoritative_state_artifact",
    "campaign_status_artifact",
)
HANDOFF_IDLE_NULL_FIELDS = HANDOFF_PATH_FIELDS + (
    "authoritative_state_field",
    "campaign_status_field",
)
HANDOFF_START = "<!-- HANDOFF_STATE_START -->"
HANDOFF_END = "<!-- HANDOFF_STATE_END -->"
SECRET_CONTENT_PATTERNS = (
    re.compile(r"-----BEGIN [^-]+ PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:sk|pk)-live-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"(?i)\bxox[baprs]-[A-Za-z0-9-]{16,}\b"),
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_paths(root: Path, *, include_untracked: bool) -> list[str]:
    args = ["git", "ls-files", "-z"]
    if include_untracked:
        args = ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"]
    try:
        raw = subprocess.check_output(args, cwd=root)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PackageError(f"cannot enumerate release files: {exc}") from exc
    return sorted({item.replace("\\", "/") for item in raw.decode("utf-8").split("\0") if item})


def _git_head(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, encoding="utf-8"
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PackageError(f"cannot determine source HEAD: {exc}") from exc


def _is_excluded(rel: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    lowered = [part.lower() for part in parts]
    if any(part in EXCLUDED_SEGMENTS for part in lowered):
        return True
    name = lowered[-1]
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return True
    if Path(name).suffix.lower() in MEDIA_SUFFIXES:
        return True
    if Path(name).suffix.lower() in SECRET_PATH_SUFFIXES:
        return True
    return False


def _is_included(rel: str) -> bool:
    normalized = rel.replace("\\", "/")
    if _is_excluded(normalized):
        return False
    if normalized in INCLUDE_FILES:
        return True
    root = normalized.split("/", 1)[0]
    if root not in INCLUDE_ROOTS:
        return False
    if root == "docs" and normalized.lower().startswith("docs/archive/"):
        return False
    if root == "distribution" and not normalized.startswith("distribution/agent-skill/"):
        return False
    return True


def _handoff_payload(root: Path) -> tuple[str, dict[str, object]]:
    path = root / "HANDOFF_CURRENT.md"
    if not path.is_file():
        raise PackageError("HANDOFF_CURRENT.md is missing")
    text = path.read_text(encoding="utf-8")
    if text.count(HANDOFF_START) != 1 or text.count(HANDOFF_END) != 1:
        raise PackageError("HANDOFF_CURRENT.md must contain one state block")
    start = text.index(HANDOFF_START) + len(HANDOFF_START)
    end = text.index(HANDOFF_END)
    try:
        payload = json.loads(text[start:end].strip())
    except json.JSONDecodeError as exc:
        raise PackageError(f"HANDOFF_CURRENT.md JSON is invalid: {exc}") from exc
    if not isinstance(payload, dict):
        raise PackageError("HANDOFF_CURRENT.md state must be a JSON object")
    return text, payload


def _is_excluded_reference(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    path = Path(value)
    if path.is_absolute() or re.match(r"^[A-Za-z]:[\\/]", value):
        return True
    return _is_excluded(value.replace("\\", "/"))


def validate_handoff_for_release(root: Path) -> dict[str, object]:
    """Validate that the source handoff is safe to ship in a source package."""

    text, payload = _handoff_payload(root)
    state = payload.get("state")
    if state != "IDLE":
        for field in HANDOFF_PATH_FIELDS:
            if _is_excluded_reference(payload.get(field)):
                raise PackageError(
                    f"active handoff depends on excluded artifact: {field}={payload[field]}"
                )
        raise PackageError("active handoff must be IDLE for an Agent-only release")

    for field in HANDOFF_IDLE_NULL_FIELDS:
        if payload.get(field) is not None:
            raise PackageError(f"IDLE handoff has active field: {field}")
    if re.search(r"(?i)(^|[\\/])\.tmp([\\/]|$)|(^|[\\/])runs([\\/]|$)", text):
        raise PackageError("IDLE handoff references an excluded artifact")
    if re.search(r"(?i)(?:[A-Z]:[\\/]|\\\\[^\\/]+[\\/])", text):
        raise PackageError("IDLE handoff contains an absolute local path")
    return payload


def _source_root_variants(root: Path) -> tuple[str, ...]:
    resolved = str(root.resolve())
    variants = {resolved, resolved.replace("\\", "/")}
    return tuple(sorted(variants, key=len, reverse=True))


def _package_bytes(source: Path, root: Path) -> tuple[bytes, str | None]:
    original = source.read_bytes()
    try:
        text = original.decode("utf-8")
    except UnicodeDecodeError:
        return original, None
    for variant in _source_root_variants(root):
        text = re.sub(re.escape(variant), "<VIDEO_PIPELINE_HOME>", text, flags=re.IGNORECASE)
    packaged = text.encode("utf-8")
    for pattern in SECRET_CONTENT_PATTERNS:
        if pattern.search(text):
            raise PackageError(f"secret-like content found in release file: {source}")
    return packaged, _sha256_bytes(original)


def _assert_output_available(path: Path, *, allow_empty_dir: bool = True) -> None:
    if path.exists():
        if path.is_dir() and allow_empty_dir and not any(path.iterdir()):
            return
        raise PackageError(f"refusing to overwrite existing non-empty output: {path}")


def _write_deterministic_zip(source_dir: Path, zip_path: Path) -> None:
    _assert_output_available(zip_path, allow_empty_dir=False)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        files = sorted(
            (item for item in source_dir.rglob("*") if item.is_file()),
            key=lambda item: item.relative_to(source_dir).as_posix(),
        )
        for path in files:
            rel = path.relative_to(source_dir).as_posix()
            info = ZipInfo(rel)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = ZIP_DEFLATED
            info.create_system = 0
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())


def package_release(
    source_root: Path,
    output_dir: Path,
    *,
    zip_output: Path | None = None,
    include_untracked: bool = False,
) -> dict[str, object]:
    """Package the tracked release surface, optionally including dirty files for tests."""

    root = source_root.resolve()
    output = output_dir.resolve()
    if output == root:
        raise PackageError("output directory cannot be the source root")
    _assert_output_available(output)
    if zip_output is not None and zip_output.resolve() == output:
        raise PackageError("zip output cannot be the source directory")

    handoff = validate_handoff_for_release(root)
    candidates = _git_paths(root, include_untracked=include_untracked)
    included = [rel for rel in candidates if _is_included(rel) and (root / rel).is_file()]
    excluded = sorted(set(candidates) - set(included))
    if "HANDOFF_CURRENT.md" not in included:
        raise PackageError("HANDOFF_CURRENT.md is not in the release surface")

    output.mkdir(parents=True, exist_ok=True)
    file_records: list[dict[str, str]] = []
    for rel in included:
        source = root / rel
        target = output / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        data, source_hash = _package_bytes(source, root)
        target.write_bytes(data)
        record = {"path": rel, "sha256": _sha256_bytes(data)}
        if source_hash is not None and source_hash != record["sha256"]:
            record["source_sha256"] = source_hash
        file_records.append(record)

    manifest = {
        "artifact_role": "agent_only_release_manifest",
        "exclusions": {
            "files": excluded,
            "rules": [
                "excluded local state and VCS roots",
                "excluded virtual environments and caches",
                "excluded .env files except .env.example",
                "excluded generated media and private-key files",
                "excluded docs/archive and archive history",
            ],
        },
        "file_count": len(file_records),
        "included_files": file_records,
        "license_status": LICENSE_STATUS,
        "platform_assumptions": [
            "Windows workspace",
            "Miniconda Python >= 3.10",
            "ffmpeg, Node.js, and yt-dlp available on PATH",
        ],
        "release_status": RELEASE_STATUS,
        "source_head": _git_head(root),
        "source_mode": "working_tree" if include_untracked else "tracked_head",
        "handoff_state": handoff.get("state"),
    }
    manifest_path = output / "release_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if zip_output is not None:
        _write_deterministic_zip(output, zip_output.resolve())

    return {
        "release_status": RELEASE_STATUS,
        "source_head": manifest["source_head"],
        "output_dir": str(output),
        "zip_output": str(zip_output.resolve()) if zip_output is not None else None,
        "file_count": len(file_records),
        "manifest_sha256": _sha256_file(manifest_path),
    }


def _parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--zip-output", type=Path)
    parser.add_argument(
        "--include-untracked",
        action="store_true",
        help="Include non-ignored working-tree files for local tests only.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = package_release(
            args.source_root,
            args.output_dir,
            zip_output=args.zip_output,
            include_untracked=args.include_untracked,
        )
    except PackageError as exc:
        print(f"ERROR: {exc}")
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
