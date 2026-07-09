"""Run or consume independent ASR evidence for voiceover output QA."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.voiceover_output_qa import write_voiceover_output_qa_for_run


def _run_faster_whisper(paths: list[Path], model_name: str, language: str) -> dict:
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception as exc:  # pragma: no cover - environment dependent
        return {
            "artifact_role": "voiceover_output_probe",
            "method": "faster_whisper_unavailable",
            "runtime_ok": False,
            "error": str(exc),
            "items": [],
            "segments": [],
            "evidence": [],
        }
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    items = []
    flat_segments = []
    evidence = []
    for path in paths:
        segments, info = model.transcribe(str(path), language=language)
        segs = []
        texts = []
        for segment in segments:
            text = str(getattr(segment, "text", "")).strip()
            seg = {
                "start": float(getattr(segment, "start", 0.0)),
                "end": float(getattr(segment, "end", 0.0)),
                "text": text,
                "recognized_text": text,
                "segment_id": path.stem,
            }
            segs.append(seg)
            flat_segments.append(seg)
            texts.append(text)
        items.append({
            "path": str(path),
            "exists": path.exists(),
            "language": getattr(info, "language", language),
            "segments": segs,
            "text": " ".join(texts),
        })
        evidence.append({"audio_ref": str(path), "method": "faster_whisper"})
    return {
        "artifact_role": "voiceover_output_probe",
        "method": "faster_whisper",
        "runtime_ok": True,
        "model": model_name,
        "items": items,
        "segments": flat_segments,
        "evidence": evidence,
    }


def _default_voiceover_paths(run: Path) -> list[Path]:
    voiceover_dir = run / "voiceover"
    paths = sorted(voiceover_dir.glob("*.wav")) if voiceover_dir.exists() else []
    final = run / "final_v5.mp4"
    if final.exists():
        paths.append(final)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="Run directory to inspect/write.")
    parser.add_argument("--probe", help="Existing independent ASR probe JSON to consume.")
    parser.add_argument("--model", default="tiny", help="faster-whisper model name.")
    parser.add_argument("--language", default="zh", help="ASR language.")
    parser.add_argument("--json", action="store_true", help="Print QA JSON.")
    args = parser.parse_args()

    run = Path(args.run)
    if args.probe:
        probe = json.loads(Path(args.probe).read_text(encoding="utf-8-sig"))
    else:
        probe = _run_faster_whisper(_default_voiceover_paths(run), args.model, args.language)
    (run / "voiceover_output_probe.json").write_text(
        json.dumps(probe, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report = write_voiceover_output_qa_for_run(run)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"independent_voiceover_asr_qa pass={report['pass']} run={run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
