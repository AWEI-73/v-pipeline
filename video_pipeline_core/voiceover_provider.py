"""Provider-neutral voiceover planning and optional rendering.

This module keeps heavy TTS providers such as VoxCPM behind an explicit
provider artifact. The pipeline can plan voiceover work on machines that do not
have the model installed, then execute the same plan later when the provider is
available.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

from .branch_env import bootstrap_branch_env


DEFAULT_VOXCPM_MODEL_ID = "openbmb/VoxCPM-0.5B"
DEFAULT_VOICE_STYLE = "warm, clear Mandarin narrator"


class VoiceoverProviderError(RuntimeError):
    """Raised when a voiceover provider plan or render cannot be completed."""


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise VoiceoverProviderError(f"invalid JSON: {path}: {exc}") from exc


def _segment_text(item: Mapping[str, object]) -> str:
    for key in ("text", "narration", "voiceover", "subtitle"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, Mapping):
            text = value.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
    return ""


def load_voiceover_segments(script_path: str | Path) -> list[dict]:
    """Load a script/contract-like JSON file into voiceover segments.

    Accepted shapes:
    - ``[{segment, title, text}, ...]`` legacy TTS script.
    - ``{"segments": [...]}`` segment contract style.
    """

    path = Path(script_path)
    if not path.exists():
        raise VoiceoverProviderError(f"script not found: {path}")
    payload = _read_json(path)
    raw_segments: Iterable[object]
    if isinstance(payload, list):
        raw_segments = payload
    elif isinstance(payload, Mapping) and isinstance(payload.get("segments"), list):
        raw_segments = payload["segments"]  # type: ignore[index]
    else:
        raise VoiceoverProviderError(
            "script must be a JSON list or an object with a segments list"
        )

    segments: list[dict] = []
    for index, raw in enumerate(raw_segments, 1):
        if not isinstance(raw, Mapping):
            continue
        text = _segment_text(raw)
        if not text:
            continue
        segment_id = raw.get("segment") or raw.get("segment_id") or raw.get("id") or index
        segments.append(
            {
                "index": len(segments) + 1,
                "segment": segment_id,
                "title": raw.get("title") or raw.get("name"),
                "text": text,
            }
        )
    if not segments:
        raise VoiceoverProviderError("no voiceover text found in script")
    return segments


def _default_voxcpm_repo() -> Path:
    return Path(__file__).resolve().parents[1] / "reference repo" / "VoxCPM-main"


def _voxcpm_repo_command_prefix(repo: Path, python_executable: str | None = None) -> list[str] | None:
    src_dir = repo / "src"
    cli_path = src_dir / "voxcpm" / "cli.py"
    if not cli_path.exists():
        return None
    code = (
        "import runpy, sys; "
        f"sys.path.insert(0, {str(src_dir)!r}); "
        f"runpy.run_path({str(cli_path)!r}, run_name='__main__')"
    )
    return [python_executable or sys.executable, "-c", code]


def _resolve_voxcpm_runtime(
    voxcpm_bin: str | None = None,
    voxcpm_repo: str | Path | None = None,
    voxcpm_python: str | Path | None = None,
) -> dict:
    candidate = voxcpm_bin or os.environ.get("VOXCPM_BIN") or "voxcpm"
    found = shutil.which(candidate)
    if found:
        return {
            "available": True,
            "entry_type": "bin",
            "command_prefix": [found],
            "repo": None,
            "reason": None,
        }
    if candidate and Path(candidate).exists():
        return {
            "available": True,
            "entry_type": "bin",
            "command_prefix": [str(Path(candidate))],
            "repo": None,
            "reason": None,
        }

    boot_env = bootstrap_branch_env()
    repo_raw = voxcpm_repo or os.environ.get("VOXCPM_REPO") or _default_voxcpm_repo()
    repo = Path(repo_raw)
    python_raw = voxcpm_python or boot_env.get("VOXCPM_PYTHON")
    python_executable = str(Path(python_raw)) if python_raw else None
    prefix = _voxcpm_repo_command_prefix(repo, python_executable=python_executable)
    if prefix:
        return {
            "available": True,
            "entry_type": "local_repo",
            "command_prefix": prefix,
            "repo": str(repo),
            "python": python_executable or sys.executable,
            "reason": None,
        }
    return {
        "available": False,
        "entry_type": None,
        "command_prefix": None,
        "repo": str(repo),
        "python": python_executable or sys.executable,
        "reason": "voxcpm executable not found and local repo entrypoint not found",
    }


def _voxcpm_command(
    *,
    command_prefix: Sequence[str],
    text: str,
    output: Path,
    voice_style: str,
    model_id: str,
    reference_audio: str | None,
    device: str,
    local_files_only: bool,
    inference_timesteps: int,
    cfg_value: float,
) -> list[str]:
    command = list(command_prefix) + [
        "clone" if reference_audio else "design",
        "--text",
        text,
        "--control",
        voice_style,
        "--output",
        str(output),
        "--hf-model-id",
        model_id,
        "--device",
        device,
        "--inference-timesteps",
        str(inference_timesteps),
        "--cfg-value",
        str(cfg_value),
    ]
    if reference_audio:
        command += ["--reference-audio", reference_audio]
    if local_files_only:
        command.append("--local-files-only")
    return command


def _command_with_device(command: Sequence[str], device: str) -> list[str]:
    updated = list(command)
    try:
        updated[updated.index("--device") + 1] = device
    except (ValueError, IndexError):
        updated += ["--device", device]
    return updated


def _legacy_tts_command(script_path: Path, out_dir: Path, voice: str | None) -> list[str]:
    command = [sys.executable, str(Path(__file__).resolve().parents[1] / "video_tools.py"), "tts", str(script_path)]
    if voice:
        command += ["--voice", voice]
    command += ["--outdir", str(out_dir)]
    return command


def _run_command(command: Sequence[str], timeout_sec: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(command),
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        encoding="utf-8",
        errors="replace",
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _update_artifact_manifest(output_root: Path, written: Mapping[str, str], *, voiceover_ready: bool) -> None:
    manifest_path = output_root / "artifact_manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.is_file():
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            if isinstance(loaded, dict):
                manifest.update(loaded)
        except json.JSONDecodeError:
            manifest = {}
    manifest.setdefault("artifact_role", "artifact_manifest")
    manifest.setdefault("artifact_manifest_version", 1)
    artifacts = manifest.setdefault("artifacts", {})
    if not isinstance(artifacts, dict):
        artifacts = {}
        manifest["artifacts"] = artifacts
    key_map = {
        "plan": "voiceover_provider_plan",
        "handoff": "subtitle_voiceover_build_handoff",
        "narration_manifest": "narration_manifest",
    }
    status = "accepted" if voiceover_ready else "planned_or_blocked"
    for source_key, manifest_key in key_map.items():
        path = written.get(source_key)
        if not path:
            continue
        manifest[manifest_key] = path
        artifacts[manifest_key] = {
            "path": path,
            "owner": "subtitle_voiceover",
            "status": status if source_key == "handoff" else "evidence",
            "updated_by": "video_pipeline_core.voiceover_provider.write_voiceover_provider_artifacts",
        }
    _write_json(manifest_path, manifest)


def build_voiceover_provider_plan(
    *,
    script_path: str | Path,
    out_dir: str | Path,
    provider: str = "voxcpm",
    voice_style: str = DEFAULT_VOICE_STYLE,
    model_id: str | None = None,
    reference_audio: str | None = None,
    device: str = "auto",
    local_files_only: bool = False,
    inference_timesteps: int = 10,
    cfg_value: float = 2.0,
    execute: bool = False,
    allow_fallback: bool = False,
    execute_fallback: bool = False,
    fallback_voice: str | None = None,
    voxcpm_bin: str | None = None,
    voxcpm_repo: str | Path | None = None,
    voxcpm_python: str | Path | None = None,
    timeout_sec: int = 1200,
    runner: Callable[[Sequence[str], int], subprocess.CompletedProcess] | None = None,
) -> dict:
    """Create a provider artifact and optionally execute the selected provider."""

    script = Path(script_path)
    output_root = Path(out_dir)
    voice_dir = output_root / "voiceover"
    voice_dir.mkdir(parents=True, exist_ok=True)
    segments = load_voiceover_segments(script)
    model = model_id or os.environ.get("VOXCPM_MODEL_ID") or DEFAULT_VOXCPM_MODEL_ID
    selected_provider = provider
    provider_available = True
    runtime = {"available": True, "entry_type": None, "command_prefix": None, "repo": None, "reason": None}

    if provider == "voxcpm":
        runtime = _resolve_voxcpm_runtime(
            voxcpm_bin=voxcpm_bin,
            voxcpm_repo=voxcpm_repo,
            voxcpm_python=voxcpm_python,
        )
        provider_available = bool(runtime["available"])
        if not provider_available and allow_fallback:
            selected_provider = "legacy_edge_tts"
    elif provider != "legacy_edge_tts":
        raise VoiceoverProviderError(f"unknown provider: {provider}")

    command_runner = runner or _run_command
    rendered_files: list[str] = []
    segment_entries: list[dict] = []
    errors: list[dict] = []

    for segment in segments:
        stem = f"seg{segment['index']:02d}"
        target = voice_dir / f"{stem}.wav"
        if selected_provider == "voxcpm":
            command_prefix = runtime.get("command_prefix")
            if not command_prefix:
                segment_entries.append(
                    {
                        **segment,
                        "provider": "voxcpm",
                        "target_file": str(target),
                        "status": "provider_unavailable",
                        "command": None,
                    }
                )
                if not allow_fallback:
                    errors.append(
                        {
                            "segment": segment["segment"],
                            "provider": "voxcpm",
                            "rule": "provider_unavailable",
                            "message": str(runtime.get("reason") or "VoxCPM provider entry was not found and fallback is disabled"),
                        }
                    )
                continue
            command = _voxcpm_command(
                command_prefix=command_prefix,  # type: ignore[arg-type]
                text=segment["text"],
                output=target,
                voice_style=voice_style,
                model_id=model,
                reference_audio=reference_audio,
                device=device,
                local_files_only=local_files_only,
                inference_timesteps=inference_timesteps,
                cfg_value=cfg_value,
            )
            status = "planned"
            retry: dict[str, object] | None = None
            if execute:
                result = command_runner(command, timeout_sec)
                if result.returncode == 0 and target.exists():
                    status = "rendered"
                    rendered_files.append(str(target))
                else:
                    primary_error = {
                        "returncode": result.returncode,
                        "stderr": (result.stderr or "")[-1000:],
                    }
                    if device != "cpu":
                        retry_command = _command_with_device(command, "cpu")
                        retry_result = command_runner(retry_command, timeout_sec)
                        retry = {
                            "reason": "voxcpm_primary_failed",
                            "retry_device": "cpu",
                            "primary_returncode": result.returncode,
                            "primary_stderr": (result.stderr or "")[-1000:],
                            "retry_returncode": retry_result.returncode,
                            "command": retry_command,
                        }
                        if retry_result.returncode == 0 and target.exists():
                            status = "rendered"
                            rendered_files.append(str(target))
                        else:
                            status = "failed"
                            errors.append(
                                {
                                    "segment": segment["segment"],
                                    "provider": "voxcpm",
                                    **primary_error,
                                    "retry": retry,
                                }
                            )
                    else:
                        status = "failed"
                        errors.append(
                            {
                                "segment": segment["segment"],
                                "provider": "voxcpm",
                                **primary_error,
                            }
                        )
            entry = {**segment, "provider": "voxcpm", "target_file": str(target), "status": status, "command": command}
            if retry is not None:
                entry["retry"] = retry
            segment_entries.append(entry)
        else:
            segment_entries.append(
                {
                    **segment,
                    "provider": "legacy_edge_tts",
                    "target_file": None,
                    "status": "delegated_to_legacy_tts",
                    "command": _legacy_tts_command(script, voice_dir / "legacy_edge_tts", fallback_voice),
                }
            )

    fallback_result = None
    if selected_provider == "legacy_edge_tts":
        fallback_dir = voice_dir / "legacy_edge_tts"
        fallback_command = _legacy_tts_command(script, fallback_dir, fallback_voice)
        fallback_status = "planned"
        if execute and execute_fallback:
            result = command_runner(fallback_command, timeout_sec)
            voice_file = fallback_dir / "voice.mp3"
            if result.returncode == 0 and voice_file.exists():
                fallback_status = "rendered"
                rendered_files.append(str(voice_file))
            else:
                fallback_status = "failed"
                errors.append(
                    {
                        "provider": "legacy_edge_tts",
                        "returncode": result.returncode,
                        "stderr": (result.stderr or "")[-1000:],
                    }
                )
        fallback_result = {
            "provider": "legacy_edge_tts",
            "status": fallback_status,
            "command": fallback_command,
            "out_dir": str(fallback_dir),
            "voice_file": str(fallback_dir / "voice.mp3"),
            "timing_file": str(fallback_dir / "tts_timing.json"),
        }

    voiceover_ready = bool(rendered_files) and not errors
    fallback_used = provider != selected_provider
    fallback_reason = str(runtime.get("reason") or "") if fallback_used else None
    handoff = {
        "artifact_role": "subtitle_voiceover_build_handoff",
        "version": 1,
        "subtitle_ready": False,
        "voiceover_ready": voiceover_ready,
        "voiceover_provider_plan": str(output_root / "voiceover_provider_plan.json"),
        "selected_provider": selected_provider,
        "narration_manifest": str(output_root / "narration_manifest.json"),
        "voice_files": rendered_files,
        "fallback": fallback_result,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
    }
    narration_manifest = {
        "artifact_role": "narration_manifest",
        "version": 1,
        "provider": selected_provider,
        "voice_style": voice_style,
        "model_id": model if selected_provider == "voxcpm" else None,
        "segments": segment_entries,
        "rendered_files": rendered_files,
    }
    plan = {
        "artifact_role": "voiceover_provider_plan",
        "version": 1,
        "script_path": str(script),
        "out_dir": str(output_root),
        "requested_provider": provider,
        "selected_provider": selected_provider,
        "provider_available": provider_available,
        "provider_entry_type": runtime.get("entry_type") if provider == "voxcpm" else None,
        "provider_repo": runtime.get("repo") if provider == "voxcpm" else None,
        "provider_python": runtime.get("python") if provider == "voxcpm" else None,
        "provider_unavailable_reason": runtime.get("reason") if provider == "voxcpm" else None,
        "fallback_allowed": allow_fallback,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "voice_style": voice_style,
        "model_id": model if provider == "voxcpm" else None,
        "reference_audio": reference_audio,
        "execute": execute,
        "segments": segment_entries,
        "errors": errors,
        "handoff": handoff,
    }
    return {
        "plan": plan,
        "handoff": handoff,
        "narration_manifest": narration_manifest,
    }


def write_voiceover_provider_artifacts(payload: Mapping[str, object], out_dir: str | Path) -> dict:
    output_root = Path(out_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    written = {}
    for key, filename in (
        ("plan", "voiceover_provider_plan.json"),
        ("handoff", "subtitle_voiceover_build_handoff.json"),
        ("narration_manifest", "narration_manifest.json"),
    ):
        path = output_root / filename
        _write_json(path, payload[key])
        written[key] = str(path)
    handoff = payload.get("handoff")
    _update_artifact_manifest(
        output_root,
        written,
        voiceover_ready=bool(isinstance(handoff, Mapping) and handoff.get("voiceover_ready") is True),
    )
    return written
