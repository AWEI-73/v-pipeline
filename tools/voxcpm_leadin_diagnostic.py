"""Run a VoxCPM provider lead-in artifact diagnostic matrix."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.voiceover_provider import (  # noqa: E402
    VoiceoverProviderError,
    build_voiceover_provider_plan,
    write_voiceover_provider_artifacts,
)
from video_pipeline_core.voxcpm_leadin_diagnostic import (  # noqa: E402
    classify_provider_leadin,
    evaluate_case_leadin,
    first_800ms_analysis,
    plan_diagnostic_matrix,
    run_ffmpeg_trim,
    wav_duration_sec,
    write_case_script,
)


def _run_asr(paths: list[Path], model_name: str, language: str) -> dict[str, Any]:
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception as exc:  # pragma: no cover - environment dependent
        return {
            "ok": False,
            "error": str(exc),
            "items": [],
        }
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    items = []
    for path in paths:
        segments, info = model.transcribe(str(path), language=language)
        texts = []
        segs = []
        for segment in segments:
            text = str(getattr(segment, "text", "")).strip()
            texts.append(text)
            segs.append({
                "start": float(getattr(segment, "start", 0.0)),
                "end": float(getattr(segment, "end", 0.0)),
                "text": text,
            })
        items.append({
            "path": str(path),
            "exists": path.exists(),
            "language": getattr(info, "language", language),
            "segments": segs,
            "text": " ".join(texts).strip(),
        })
    return {"ok": True, "method": "faster_whisper", "model": model_name, "language": language, "items": items}


def _voiceover_paths(case_dir: Path) -> list[Path]:
    return sorted((case_dir / "voiceover").glob("*.wav"))


def _copy_snippet(source: Path, target: Path) -> dict[str, Any]:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return {
        "path": str(target),
        "exists": target.exists(),
        "size_bytes": target.stat().st_size if target.exists() else 0,
        "duration_sec": wav_duration_sec(target) if target.exists() else None,
    }


def run_diagnostic(out_dir: Path, model: str, language: str, timeout_sec: int) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cases_root = out_dir / "cases"
    snippets_root = out_dir / "snippets"
    matrix_rows = []
    generated_wavs = []

    for case in plan_diagnostic_matrix():
        label = str(case["label"])
        case_dir_name = label if case.get("path_mode") != "ascii" else f"ascii_{len(matrix_rows) + 1:02d}"
        case_dir = cases_root / case_dir_name
        script_path = write_case_script(case, case_dir)
        row: dict[str, Any] = {
            "label": label,
            "text": case["text"],
            "voice_style": case["voice_style"],
            "path_mode": case["path_mode"],
            "script_path": str(script_path),
        }
        try:
            payload = build_voiceover_provider_plan(
                script_path=script_path,
                out_dir=case_dir,
                provider="voxcpm",
                voice_style=str(case.get("voice_style") or ""),
                device="auto",
                execute=True,
                timeout_sec=timeout_sec,
            )
            write_voiceover_provider_artifacts(payload, case_dir)
            errors = payload["plan"].get("errors") or []
            row.update({
                "returncode": 0 if not errors else 1,
                "provider_available": payload["plan"].get("provider_available"),
                "provider_python": payload["plan"].get("provider_python"),
                "provider_repo": payload["plan"].get("provider_repo"),
                "provider_entry_type": payload["plan"].get("provider_entry_type"),
                "voiceover_ready": payload["handoff"].get("voiceover_ready"),
                "error_count": len(errors),
                "errors": errors,
                "provider_segments": payload["plan"].get("segments", []),
            })
        except VoiceoverProviderError as exc:
            row.update({"returncode": 2, "error": str(exc), "voiceover_ready": False})

        wavs = _voiceover_paths(case_dir)
        row["wav_files"] = [
            {
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "duration_sec": wav_duration_sec(path),
            }
            for path in wavs
        ]
        generated_wavs.extend(wavs)
        if wavs:
            snippet_info = _copy_snippet(wavs[0], snippets_root / f"{label}_original.wav")
            row["human_listening_snippet"] = snippet_info["path"]
        asr = _run_asr(wavs, model, language) if wavs else {"ok": False, "items": []}
        row["independent_asr"] = asr
        first_text = ""
        if asr.get("items"):
            first_text = str(asr["items"][0].get("text") or "")
        row["first_token_analysis"] = first_800ms_analysis(first_text, str(case["text"]))
        lead = evaluate_case_leadin(case, first_text)
        row["lead_in_qa_pass"] = lead["pass"]
        row["detected_extra_leadin"] = (
            lead.get("detected_leadin_mismatches", [{}])[0].get("detected_extra_leadin")
            if lead.get("detected_leadin_mismatches")
            else ""
        )
        row["lead_in_qa"] = lead
        matrix_rows.append(row)

    diagnostic = {
        "artifact_role": "voxcpm_provider_leadin_diagnostic",
        "version": 1,
        "out_dir": str(out_dir),
        "model": model,
        "language": language,
        "matrix": matrix_rows,
        "generated_wav_count": len(generated_wavs),
    }
    (out_dir / "voxcpm_provider_leadin_diagnostic.json").write_text(
        json.dumps(diagnostic, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    trim_probe = run_trim_probe(out_dir, matrix_rows, model, language)
    classification = classify_provider_leadin(matrix_rows, trim_probe)
    classification["out_dir"] = str(out_dir)
    (out_dir / "provider_leadin_classification.json").write_text(
        json.dumps(classification, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"diagnostic": diagnostic, "trim_probe": trim_probe, "classification": classification}


def run_trim_probe(out_dir: Path, matrix_rows: list[dict[str, Any]], model: str, language: str) -> dict[str, Any]:
    trim_root = out_dir / "trim_probe"
    offsets = [100, 200, 300, 500]
    candidates = [row for row in matrix_rows if row.get("lead_in_qa_pass") is False and row.get("wav_files")]
    results = []
    rows_to_probe = candidates if candidates else [row for row in matrix_rows if row.get("wav_files")][:1]
    safe_by_label: dict[str, bool] = {}
    for source_row in rows_to_probe:
        source = Path(source_row["wav_files"][0]["path"])
        safe_by_label[str(source_row["label"])] = False
        for offset in offsets:
            target = trim_root / f"{source_row['label']}_trim_{offset}ms.wav"
            trim = run_ffmpeg_trim(source, target, offset)
            asr = _run_asr([target], model, language) if target.exists() else {"ok": False, "items": []}
            text = str(asr.get("items", [{}])[0].get("text") if asr.get("items") else "")
            lead = evaluate_case_leadin(source_row, text)
            expected_norm = first_800ms_analysis(text, str(source_row["text"]))
            intended_first_survives = expected_norm["recognized_prefix"].startswith(expected_norm["expected_first_token"])
            safe = bool(lead["pass"] and intended_first_survives)
            safe_by_label[str(source_row["label"])] = safe_by_label[str(source_row["label"])] or safe
            results.append({
                "source_label": source_row["label"],
                "source_path": str(source),
                "offset_ms": offset,
                "trim": trim,
                "asr_text": text,
                "lead_in_qa_pass": lead["pass"],
                "detected_mismatches": lead.get("detected_leadin_mismatches", []),
                "intended_first_syllable_survives": intended_first_survives,
                "safe_trim": safe,
            })
    safe_trim_available = bool(safe_by_label) and all(safe_by_label.values())
    probe = {
        "artifact_role": "lead_in_trim_probe",
        "version": 1,
        "safe_trim_available": safe_trim_available,
        "safe_by_label": safe_by_label,
        "offsets_ms": offsets,
        "results": results,
    }
    (out_dir / "lead_in_trim_probe.json").write_text(
        json.dumps(probe, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return probe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--model", default="tiny")
    parser.add_argument("--language", default="zh")
    parser.add_argument("--timeout-sec", type=int, default=1200)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run_diagnostic(Path(args.out_dir), args.model, args.language, args.timeout_sec)
    summary = {
        "ok": True,
        "out_dir": args.out_dir,
        "matrix_count": len(result["diagnostic"]["matrix"]),
        "generated_wav_count": result["diagnostic"]["generated_wav_count"],
        "classification": result["classification"]["classification"],
        "safe_trim_available": result["trim_probe"]["safe_trim_available"],
        "artifacts": {
            "diagnostic": str(Path(args.out_dir) / "voxcpm_provider_leadin_diagnostic.json"),
            "trim_probe": str(Path(args.out_dir) / "lead_in_trim_probe.json"),
            "classification": str(Path(args.out_dir) / "provider_leadin_classification.json"),
        },
    }
    print(json.dumps(summary if args.json else result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
