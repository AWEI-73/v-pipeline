"""Optional soundtrack provider search and candidate download helpers."""

from __future__ import annotations

import json
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Mapping, Sequence

from .env_loader import load_env_file


JAMENDO_TRACKS_URL = "https://api.jamendo.com/v3.0/tracks/"


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_id(value: Any) -> str:
    text = _clean(value).lower()
    text = re.sub(r"[^a-z0-9_.-]+", "_", text)
    return text.strip("._") or "candidate"


def _query_for_section(section: Mapping[str, Any]) -> str:
    role = _clean(section.get("story_function") or section.get("section_id"))
    energy = _clean(section.get("energy_curve"))
    music_role = _clean(section.get("music_role"))
    vocal = _clean(section.get("vocal_policy"))
    pieces = [role, energy, music_role]
    if vocal == "instrumental_required":
        pieces.append("instrumental")
    elif vocal == "vocal_ok":
        pieces.append("vocal")
    return " ".join(piece for piece in pieces if piece)


def _provider_unavailable(provider: str, section: Mapping[str, Any], note: str) -> dict[str, Any]:
    return {
        "candidate_id": f"{provider}_{_safe_id(section.get('section_id'))}_unavailable",
        "provider": provider,
        "section_id": section.get("section_id"),
        "source_type": section.get("source_type"),
        "status": "provider_unavailable",
        "delivery_allowed": False,
        "license_status": "provider_unavailable",
        "note": note,
    }


def _read_json_url(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "HermesVideoPipeline/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:  # noqa: S310 - trusted provider URL.
        payload = response.read()
    data = json.loads(payload.decode("utf-8"))
    return data if isinstance(data, dict) else {}


def _jamendo_candidates(section: Mapping[str, Any], *, client_id: str, limit: int) -> list[dict[str, Any]]:
    query = _query_for_section(section)
    params = {
        "client_id": client_id,
        "format": "json",
        "limit": str(limit),
        "search": query,
        "include": "musicinfo",
        "audioformat": "mp31",
    }
    url = f"{JAMENDO_TRACKS_URL}?{urllib.parse.urlencode(params)}"
    data = _read_json_url(url)
    candidates: list[dict[str, Any]] = []
    for item in data.get("results") or []:
        track_id = _clean(item.get("id"))
        download_url = _clean(item.get("audiodownload"))
        audio_url = _clean(item.get("audio"))
        license_url = _clean(item.get("license_ccurl") or item.get("license_url"))
        delivery_allowed = bool(download_url and license_url and item.get("audiodownload_allowed", True))
        candidates.append(
            {
                "candidate_id": f"jamendo_{_safe_id(section.get('section_id'))}_{_safe_id(track_id)}",
                "provider": "jamendo",
                "section_id": section.get("section_id"),
                "source_type": "jamendo_song" if section.get("music_role") == "song" else "licensed_library",
                "status": "candidate",
                "title": item.get("name"),
                "artist": item.get("artist_name"),
                "url": item.get("shareurl"),
                "preview_url": audio_url,
                "download_url": download_url,
                "duration_sec": item.get("duration"),
                "license_url": license_url,
                "license_status": "license_metadata_present" if license_url else "license_missing",
                "attribution": " - ".join(part for part in [item.get("artist_name"), item.get("name")] if part),
                "delivery_allowed": delivery_allowed,
                "search_query": query,
            }
        )
    return candidates


def search_soundtrack_providers(
    soundtrack_plan: Mapping[str, Any],
    *,
    providers: Sequence[str] = ("jamendo", "pixabay"),
    env: Mapping[str, str] | None = None,
    limit: int = 3,
) -> dict[str, Any]:
    env_map = load_env_file() if env is None else dict(env)
    sections = soundtrack_plan.get("sections") or []
    candidates: list[dict[str, Any]] = []
    provider_status: dict[str, str] = {}
    for section in sections:
        music_role = _clean(section.get("music_role"))
        if music_role in {"silence", "diegetic"}:
            continue
        source_type = _clean(section.get("source_type"))
        wants_song = music_role == "song" or source_type == "jamendo_song"
        wants_bgm = music_role == "bgm" or source_type in {"pixabay_music", "licensed_library"}

        if "jamendo" in providers and wants_song:
            client_id = _clean(env_map.get("JAMENDO_CLIENT_ID"))
            if not client_id:
                candidates.append(_provider_unavailable("jamendo", section, "JAMENDO_CLIENT_ID is not configured"))
                provider_status["jamendo"] = "missing_credentials"
            else:
                try:
                    found = _jamendo_candidates(section, client_id=client_id, limit=limit)
                except Exception as exc:  # pragma: no cover - network errors vary.
                    candidates.append(_provider_unavailable("jamendo", section, f"Jamendo search failed: {exc}"))
                    provider_status["jamendo"] = "error"
                else:
                    candidates.extend(found)
                    provider_status["jamendo"] = "ok"

        if "pixabay" in providers and wants_bgm:
            if not _clean(env_map.get("PIXABAY_API_KEY")):
                candidates.append(_provider_unavailable("pixabay", section, "PIXABAY_API_KEY is not configured"))
                provider_status["pixabay"] = "missing_credentials"
            else:
                candidates.append(
                    _provider_unavailable(
                        "pixabay",
                        section,
                        "Pixabay official audio API is not available in the documented API surface; use direct_download_url or manual candidate import.",
                    )
                )
                provider_status["pixabay"] = "official_audio_api_unavailable"

    return {
        "artifact_role": "music_source_candidates",
        "version": 1,
        "provider_status": provider_status,
        "candidates": candidates,
    }


def write_provider_candidates(
    soundtrack_plan: Mapping[str, Any],
    out_path: str | Path,
    *,
    providers: Sequence[str] = ("jamendo", "pixabay"),
    env: Mapping[str, str] | None = None,
    limit: int = 3,
) -> dict[str, Any]:
    result = search_soundtrack_providers(soundtrack_plan, providers=providers, env=env, limit=limit)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _candidate_download_url(candidate: Mapping[str, Any]) -> str:
    return _clean(candidate.get("download_url") or candidate.get("direct_download_url") or candidate.get("audio_url"))


def download_candidate(candidate: Mapping[str, Any], out_dir: str | Path) -> dict[str, Any]:
    if not candidate.get("delivery_allowed"):
        raise ValueError("candidate is not delivery_allowed")
    url = _candidate_download_url(candidate)
    if not url:
        raise ValueError("candidate has no download_url/direct_download_url")
    out_root = Path(out_dir)
    audio_dir = out_root / "audio" / "sources"
    audio_dir.mkdir(parents=True, exist_ok=True)
    suffix = ".mp3"
    parsed_path = urllib.parse.urlparse(url).path
    parsed_suffix = Path(parsed_path).suffix.lower()
    if parsed_suffix in {".mp3", ".wav", ".m4a", ".ogg", ".webm"}:
        suffix = parsed_suffix
    audio_path = audio_dir / f"{_safe_id(candidate.get('candidate_id'))}{suffix}"
    req = urllib.request.Request(url, headers={"User-Agent": "HermesVideoPipeline/1.0"})
    with urllib.request.urlopen(req, timeout=60) as response:  # noqa: S310 - candidate URL is explicit.
        audio_path.write_bytes(response.read())

    selected = {
        "candidate_id": candidate.get("candidate_id"),
        "provider": candidate.get("provider"),
        "section_id": candidate.get("section_id"),
        "source_type": candidate.get("source_type"),
        "title": candidate.get("title"),
        "artist": candidate.get("artist"),
        "url": candidate.get("url"),
        "download_url": url,
        "audio_file": str(audio_path),
        "license_url": candidate.get("license_url"),
        "license_status": candidate.get("license_status"),
        "attribution": candidate.get("attribution"),
        "delivery_allowed": True,
    }
    manifest = {
        "artifact_role": "sound_license_manifest",
        "version": 1,
        "delivery_allowed": True,
        "blocked_reasons": [],
        "selected_sources": [selected],
    }
    handoff = {
        "artifact_role": "audio_director_handoff",
        "version": 1,
        "handoff_to": "audio-director",
        "ready_for_audio_director": True,
        "blocks": [],
        "selected_audio_files": [selected],
    }
    (out_root / "sound_license_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_root / "audio_director_handoff.json").write_text(
        json.dumps(handoff, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"ok": True, "audio_file": str(audio_path), "manifest": manifest, "audio_director_handoff": handoff}


def _write_selected_audio_handoff(out_root: Path, selected: dict[str, Any]) -> dict[str, Any]:
    manifest = {
        "artifact_role": "sound_license_manifest",
        "version": 1,
        "delivery_allowed": True,
        "blocked_reasons": [],
        "selected_sources": [selected],
    }
    handoff = {
        "artifact_role": "audio_director_handoff",
        "version": 1,
        "handoff_to": "audio-director",
        "ready_for_audio_director": True,
        "blocks": [],
        "selected_audio_files": [selected],
    }
    (out_root / "sound_license_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_root / "audio_director_handoff.json").write_text(
        json.dumps(handoff, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"manifest": manifest, "audio_director_handoff": handoff}


def import_url_with_ytdlp(
    url: str,
    out_dir: str | Path,
    *,
    section_id: str,
    source_type: str,
    usage_scope: str,
    license_note: str,
    license_url: str = "",
    ytdlp_path: str = "yt-dlp",
    audio_format: str = "mp3",
) -> dict[str, Any]:
    source_type = _clean(source_type)
    usage_scope = _clean(usage_scope) or "internal_only"
    license_note = _clean(license_note)
    license_url = _clean(license_url)
    if source_type == "reference_only":
        raise ValueError("reference_only URLs cannot be imported as deliverable audio")
    if source_type not in {"youtube_audio_library", "licensed_library", "user_provided", "suno_udio_external"}:
        raise ValueError(f"unsupported import source_type: {source_type}")
    if not (license_note or license_url):
        raise ValueError("license_note or license_url is required for URL audio import")
    if usage_scope not in {"internal_only", "non_commercial", "public_delivery", "commercial_delivery"}:
        raise ValueError(f"unsupported usage_scope: {usage_scope}")

    out_root = Path(out_dir)
    audio_dir = out_root / "audio" / "sources"
    audio_dir.mkdir(parents=True, exist_ok=True)
    candidate_id = f"url_{_safe_id(section_id)}"
    output_template = str(audio_dir / f"{candidate_id}.%(ext)s")
    cmd = [
        ytdlp_path,
        "-x",
        "--audio-format",
        audio_format,
        "--audio-quality",
        "0",
        "-o",
        output_template,
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"yt-dlp import failed: {proc.stderr or proc.stdout}")

    expected = audio_dir / f"{candidate_id}.{audio_format}"
    if expected.exists():
        audio_path = expected
    else:
        literal_template_output = audio_dir / f"{candidate_id}.%(ext)s"
        if literal_template_output.exists():
            literal_template_output.replace(expected)
            audio_path = expected
        else:
            matches = sorted(audio_dir.glob(f"{candidate_id}.*"))
            if not matches:
                raise RuntimeError("yt-dlp completed but no audio file was found")
            audio_path = matches[0]

    selected = {
        "candidate_id": candidate_id,
        "provider": "yt-dlp",
        "section_id": section_id,
        "source_type": source_type,
        "url": url,
        "audio_file": str(audio_path),
        "license_note": license_note,
        "license_url": license_url,
        "license_status": "user_asserted" if usage_scope == "internal_only" else "license_metadata_required",
        "usage_scope": usage_scope,
        "delivery_allowed": True,
    }
    written = _write_selected_audio_handoff(out_root, selected)
    return {"ok": True, "audio_file": str(audio_path), **written}


def load_candidate_by_id(candidates_path: str | Path, candidate_id: str) -> dict[str, Any]:
    payload = json.loads(Path(candidates_path).read_text(encoding="utf-8-sig"))
    for candidate in payload.get("candidates") or []:
        if str(candidate.get("candidate_id")) == str(candidate_id):
            return candidate
    raise ValueError(f"candidate_id not found: {candidate_id}")
