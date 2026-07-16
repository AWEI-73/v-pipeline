import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_pipeline_core.audio_mix_plan_executor import execute_audio_mix_plan
from video_pipeline_core.platform_tools import resolve_ffmpeg, resolve_ffprobe
from tools.pipeline_home import summarize_run


def _write_json(root: Path, name: str, payload: dict):
    path = root / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _sine(path: Path, duration: float = 1.0):
    subprocess.run(
        [
            resolve_ffmpeg(),
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={duration}",
            "-af",
            "aformat=channel_layouts=stereo",
            "-ar",
            "48000",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


def _duration(path: Path) -> float:
    proc = subprocess.run(
        [
            resolve_ffprobe(),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return float(proc.stdout.strip())


def _speech_tone(path: Path, *, shift: float = 0.0, duration: float = 6.0):
    first_start = 1.0 + shift
    first_end = 2.0 + shift
    second_start = 4.0 + shift
    second_end = 5.0 + shift
    expression = (
        f"if(between(t,{first_start},{first_end})+between(t,{second_start},{second_end}),"
        "0.35,0)"
    )
    subprocess.run(
        [
            resolve_ffmpeg(), "-y", "-f", "lavfi",
            "-i", "sine=frequency=440:sample_rate=48000:duration=6",
            "-af", f"volume='{expression}':eval=frame,aformat=channel_layouts=stereo",
            "-t", str(duration), "-ar", "48000", str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


def _speech_aware_plan(root: Path, music: Path, speech: Path, *, ducking=None):
    return {
        "artifact_role": "audio_mix_plan",
        "ready_for_mix": True,
        "target_duration_sec": 6.0,
        "ducking_policy": "speech_aware",
        **({"ducking": ducking} if ducking is not None else {}),
        "source_audio_policy": {"original_audio_policy": "preserve_speech"},
        "sections": [{"section_id": "interview", "start_sec": 0.0, "duration_sec": 6.0}],
        "tracks": [
            {
                "section_id": "interview",
                "candidate_id": "bgm",
                "audio_file": str(music),
                "role": "music_bed",
                "ducking_policy": "speech_aware",
                "source_type": "licensed_library",
                "license_status": "accepted",
            },
            {
                "section_id": "interview",
                "candidate_id": "protected_speech",
                "audio_file": str(speech),
                "role": "source_speech",
                "ducking_policy": "preserve_original_audio",
                "source_type": "original_audio",
                "license_status": "source_original",
                "volume": 1.0,
            },
        ],
    }


class AudioMixPlanExecutorTest(unittest.TestCase):
    def test_speech_aware_nonzero_music_placement_preserves_volume_and_waveform(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            music = root / "music.wav"
            speech = root / "speech.wav"
            _sine(music, 4.0)
            _speech_tone(speech, shift=2.0, duration=6.0)
            plan = {
                "artifact_role": "audio_mix_plan",
                "ready_for_mix": True,
                "target_duration_sec": 6.0,
                "ducking_policy": "speech_aware",
                "ducking": {"duck_db": -18.0, "attack_ms": 80, "release_ms": 350},
                "source_audio_policy": {"original_audio_policy": "preserve_speech"},
                "sections": [
                    {"section_id": "early_music", "start_sec": 0.0, "duration_sec": 2.0},
                    {"section_id": "late_music", "start_sec": 2.0, "duration_sec": 4.0},
                    {"section_id": "speech", "start_sec": 0.0, "duration_sec": 6.0},
                ],
                "tracks": [
                    {
                        "section_id": "early_music",
                        "candidate_id": "early_bgm",
                        "audio_file": str(music),
                        "role": "music_bed",
                        "ducking_policy": "speech_aware",
                        "source_type": "licensed_library",
                        "license_status": "accepted",
                        "volume": 0.2,
                    },
                    {
                        "section_id": "late_music",
                        "candidate_id": "bgm",
                        "audio_file": str(music),
                        "role": "music_bed",
                        "ducking_policy": "speech_aware",
                        "source_type": "licensed_library",
                        "license_status": "accepted",
                        "volume": 0.2,
                    },
                    {
                        "section_id": "speech",
                        "candidate_id": "protected_speech",
                        "audio_file": str(speech),
                        "role": "source_speech",
                        "ducking_policy": "preserve_original_audio",
                        "source_type": "original_audio",
                        "license_status": "source_original",
                        "volume": 1.0,
                    },
                ],
            }

            with patch(
                "video_pipeline_core.material_map.detect_speech_runs",
                return_value=[
                    {"start": 0.0, "end": 3.0, "kind": "silence"},
                    {"start": 3.0, "end": 4.0, "kind": "speech"},
                    {"start": 4.0, "end": 6.0, "kind": "silence"},
                ],
            ):
                result = execute_audio_mix_plan(plan, acceptance={"ok": True}, out_dir=root)

            self.assertTrue(result["ok"], result)
            report = result["audio_mix_report"]
            music_placement = next(item for item in report["placements"] if item["candidate_id"] == "bgm")
            self.assertEqual(music_placement["start_sec"], 2.0)
            self.assertEqual(music_placement["applied_volume"], 0.2)
            self.assertTrue(music_placement["ducking_applied"])
            self.assertTrue(report["protected_speech_waveform_check"]["pass"])

    def test_speech_aware_defaults_report_dynamic_rms_and_waveform_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            music = root / "music.wav"
            speech = root / "speech.wav"
            _sine(music, 6.0)
            _speech_tone(speech)
            plan = _speech_aware_plan(root, music, speech)

            with patch(
                "video_pipeline_core.material_map.detect_speech_runs",
                return_value=[
                    {"start": 0.0, "end": 1.0, "kind": "silence"},
                    {"start": 1.0, "end": 2.0, "kind": "speech"},
                    {"start": 2.0, "end": 4.0, "kind": "silence"},
                    {"start": 4.0, "end": 5.0, "kind": "speech"},
                    {"start": 5.0, "end": 6.0, "kind": "silence"},
                ],
            ):
                result = execute_audio_mix_plan(
                    plan,
                    acceptance={"ok": True},
                    out_dir=root,
                )

            self.assertTrue(result["ok"], result)
            report = result["audio_mix_report"]
            self.assertEqual(report["ducking_mode"], "speech_aware")
            self.assertEqual(report["ducking_parameters"]["duck_db"], -12.0)
            self.assertEqual(report["ducking_parameters"]["attack_ms"], 80)
            self.assertEqual(report["ducking_parameters"]["release_ms"], 300)
            evidence = report["speech_aware_evidence"]
            self.assertGreaterEqual(evidence["active_reduction_db"], 8.0)
            self.assertGreaterEqual(evidence["recovery_gain_over_active_db"], 4.0)
            self.assertTrue(evidence["ramp_evidence"]["attack_monotonic"])
            self.assertTrue(evidence["ramp_evidence"]["release_monotonic"])
            waveform = report["protected_speech_waveform_check"]
            self.assertTrue(waveform["pass"], waveform)
            self.assertEqual(waveform["passing_window_ratio"], 1.0)
            self.assertEqual(report["protected_speech"]["gain"], 1.0)
            self.assertAlmostEqual(report["duration_sec"], 6.0, delta=0.02)

    def test_speech_aware_contract_rejects_unknown_keys_and_missing_protected_track(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            music = root / "music.wav"
            _sine(music, 6.0)
            unknown = _speech_aware_plan(
                root, music, music,
                ducking={"duck_db": -12.0, "unknown": 1},
            )
            unknown["tracks"] = unknown["tracks"][:1]
            result = execute_audio_mix_plan(unknown, acceptance={"ok": True}, out_dir=root)
            self.assertFalse(result["ok"])
            rules = {item["rule"] for item in result["audio_mix_report"]["blocking"]}
            self.assertIn("speech_aware_invalid_contract", rules)
            self.assertIn("speech_aware_protected_track_missing", rules)

    def test_speech_aware_waveform_check_rejects_shifted_protected_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            music = root / "music.wav"
            speech = root / "speech_shifted.wav"
            _sine(music, 6.0)
            _speech_tone(speech, shift=0.05)
            plan = _speech_aware_plan(root, music, speech)

            with patch(
                "video_pipeline_core.material_map.detect_speech_runs",
                return_value=[
                    {"start": 0.0, "end": 1.0, "kind": "silence"},
                    {"start": 1.0, "end": 2.0, "kind": "speech"},
                    {"start": 2.0, "end": 4.0, "kind": "silence"},
                    {"start": 4.0, "end": 5.0, "kind": "speech"},
                    {"start": 5.0, "end": 6.0, "kind": "silence"},
                ],
            ):
                result = execute_audio_mix_plan(plan, acceptance={"ok": True}, out_dir=root)

            self.assertFalse(result["ok"])
            self.assertFalse(result["audio_mix_report"]["protected_speech_waveform_check"]["pass"])

    def test_cli_executes_ready_mix_plan_and_writes_report(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio = root / "audio" / "sources" / "mv.wav"
            audio.parent.mkdir(parents=True)
            _sine(audio, 1.2)
            acceptance = _write_json(root, "audio_handoff_acceptance.json", {
                "artifact_role": "audio_handoff_acceptance",
                "ok": True,
                "accepted_track_count": 1,
            })
            plan = _write_json(root, "audio_mix_plan.json", {
                "artifact_role": "audio_mix_plan",
                "ready_for_mix": True,
                "rendered": False,
                "tracks": [{
                    "section_id": "mv_climax",
                    "candidate_id": "reviewed_mv",
                    "audio_file": str(audio),
                    "role": "music_main",
                    "ducking_policy": "none",
                    "source_type": "youtube_audio_library",
                    "license_status": "user_asserted",
                }],
            })

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/audio_mix_plan_execute.py",
                    "--plan",
                    str(plan),
                    "--acceptance",
                    str(acceptance),
                    "--out-dir",
                    str(root),
                    "--json",
                ],
                cwd=repo,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            summary = json.loads(proc.stdout)
            self.assertTrue(summary["ok"])
            final_audio = root / "final_audio.wav"
            report = root / "audio_mix_report.json"
            self.assertTrue(final_audio.is_file())
            self.assertTrue(report.is_file())
            self.assertAlmostEqual(_duration(final_audio), 1.2, delta=0.25)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertTrue(payload["audio_stream_present"])
            self.assertTrue(payload["music_included"])
            self.assertFalse(payload["narration_included"])
            self.assertFalse(payload["rendered_video"])
            self.assertEqual(payload["output_audio"], "final_audio.wav")
            self.assertEqual(payload["tracks"][0]["audio_file"], "audio/sources/mv.wav")
            self.assertIn("peak_dbfs", payload)
            self.assertLessEqual(payload["peak_dbfs"], -0.5)

            summary = summarize_run(root)
            self.assertEqual(summary["cursor"], "audio_ready")
            self.assertEqual(summary["next"], "return_to_build_with_final_audio")
            self.assertEqual(summary["source"], "audio_mix_report.json")

    def test_blocks_when_acceptance_is_not_ok(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            acceptance = _write_json(root, "audio_handoff_acceptance.json", {
                "artifact_role": "audio_handoff_acceptance",
                "ok": False,
                "blocking": [{"rule": "reference_only_source"}],
            })
            plan = _write_json(root, "audio_mix_plan.json", {
                "artifact_role": "audio_mix_plan",
                "ready_for_mix": True,
                "tracks": [],
            })

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/audio_mix_plan_execute.py",
                    "--plan",
                    str(plan),
                    "--acceptance",
                    str(acceptance),
                    "--out-dir",
                    str(root),
                    "--json",
                ],
                cwd=repo,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            summary = json.loads(proc.stdout)
            self.assertFalse(summary["ok"])
            self.assertEqual(summary["failed_stage"], "audio_handoff_acceptance")
            self.assertFalse((root / "final_audio.wav").exists())

    def test_places_tracks_by_section_timing_instead_of_simple_concat(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            warm = root / "audio" / "sources" / "warm.wav"
            climax = root / "audio" / "sources" / "climax.wav"
            warm.parent.mkdir(parents=True)
            _sine(warm, 3.0)
            _sine(climax, 3.0)
            acceptance = _write_json(root, "audio_handoff_acceptance.json", {
                "artifact_role": "audio_handoff_acceptance",
                "ok": True,
                "accepted_track_count": 2,
            })
            plan = _write_json(root, "audio_mix_plan.json", {
                "artifact_role": "audio_mix_plan",
                "ready_for_mix": True,
                "rendered": False,
                "sections": [
                    {"section_id": "opening", "start_sec": 0.0, "duration_sec": 1.5},
                    {"section_id": "mv_climax", "start_sec": 4.0, "duration_sec": 1.0},
                ],
                "tracks": [
                    {
                        "section_id": "opening",
                        "audio_file": str(warm),
                        "role": "music_bed",
                        "source_type": "pixabay",
                        "license_status": "accepted",
                        "fade_in_sec": 0.1,
                        "fade_out_sec": 0.1,
                    },
                    {
                        "section_id": "mv_climax",
                        "audio_file": str(climax),
                        "role": "music_main",
                        "source_type": "jamendo",
                        "license_status": "accepted",
                    },
                ],
            })

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/audio_mix_plan_execute.py",
                    "--plan",
                    str(plan),
                    "--acceptance",
                    str(acceptance),
                    "--out-dir",
                    str(root),
                    "--json",
                ],
                cwd=repo,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            final_audio = root / "final_audio.wav"
            self.assertAlmostEqual(_duration(final_audio), 5.0, delta=0.25)
            payload = json.loads((root / "audio_mix_report.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["mix_mode"], "section_timeline")
            self.assertLessEqual(payload["peak_dbfs"], -0.5)
            self.assertEqual(
                [(p["section_id"], p["start_sec"], p["duration_sec"]) for p in payload["placements"]],
                [("opening", 0.0, 1.5), ("mv_climax", 4.0, 1.0)],
            )

    def test_clamps_section_mix_to_video_duration_and_fades_out(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            long_bgm = root / "audio" / "sources" / "long.wav"
            long_bgm.parent.mkdir(parents=True)
            _sine(long_bgm, 6.0)
            acceptance = _write_json(root, "audio_handoff_acceptance.json", {
                "artifact_role": "audio_handoff_acceptance",
                "ok": True,
                "accepted_track_count": 1,
            })
            plan = _write_json(root, "audio_mix_plan.json", {
                "artifact_role": "audio_mix_plan",
                "ready_for_mix": True,
                "target_duration_sec": 3.0,
                "sections": [
                    {"section_id": "intro", "start_sec": 0.0, "duration_sec": 5.0},
                ],
                "tracks": [{
                    "section_id": "intro",
                    "audio_file": str(long_bgm),
                    "role": "music_bed",
                    "source_type": "licensed_library",
                    "license_status": "accepted",
                }],
            })

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/audio_mix_plan_execute.py",
                    "--plan",
                    str(plan),
                    "--acceptance",
                    str(acceptance),
                    "--out-dir",
                    str(root),
                    "--json",
                ],
                cwd=repo,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            final_audio = root / "final_audio.wav"
            self.assertAlmostEqual(_duration(final_audio), 3.0, delta=0.25)
            payload = json.loads((root / "audio_mix_report.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["duration_alignment"]["decision"], "clamped_to_video_duration")
            self.assertTrue(payload["duration_alignment"]["fade_out_applied"])
            self.assertEqual(payload["placements"][0]["duration_sec"], 3.0)
            self.assertGreater(payload["placements"][0]["fade_out_sec"], 0)

    def test_blocks_when_audio_plan_is_shorter_than_video_duration_without_waiver(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            short_bgm = root / "audio" / "sources" / "short.wav"
            short_bgm.parent.mkdir(parents=True)
            _sine(short_bgm, 2.0)
            acceptance = _write_json(root, "audio_handoff_acceptance.json", {
                "artifact_role": "audio_handoff_acceptance",
                "ok": True,
                "accepted_track_count": 1,
            })
            plan = _write_json(root, "audio_mix_plan.json", {
                "artifact_role": "audio_mix_plan",
                "ready_for_mix": True,
                "target_duration_sec": 5.0,
                "sections": [
                    {"section_id": "intro", "start_sec": 0.0, "duration_sec": 2.0},
                ],
                "tracks": [{
                    "section_id": "intro",
                    "audio_file": str(short_bgm),
                    "role": "music_bed",
                    "source_type": "licensed_library",
                    "license_status": "accepted",
                }],
            })

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/audio_mix_plan_execute.py",
                    "--plan",
                    str(plan),
                    "--acceptance",
                    str(acceptance),
                    "--out-dir",
                    str(root),
                    "--json",
                ],
                cwd=repo,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertFalse((root / "final_audio.wav").exists())
            payload = json.loads((root / "audio_mix_report.json").read_text(encoding="utf-8"))
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["duration_alignment"]["decision"], "shorter_than_video_duration")
            self.assertEqual(payload["duration_alignment"]["missing_duration_sec"], 3.0)
            rules = {item["rule"] for item in payload["blocking"]}
            self.assertIn("audio_shorter_than_video_duration", rules)

    def test_ducks_music_when_section_preserves_voice(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            music = root / "audio" / "sources" / "music.wav"
            voice = root / "audio" / "sources" / "voice.wav"
            music.parent.mkdir(parents=True)
            _sine(music, 2.0)
            _sine(voice, 2.0)
            acceptance = _write_json(root, "audio_handoff_acceptance.json", {
                "artifact_role": "audio_handoff_acceptance",
                "ok": True,
                "accepted_track_count": 2,
            })
            plan = _write_json(root, "audio_mix_plan.json", {
                "artifact_role": "audio_mix_plan",
                "ready_for_mix": True,
                "source_audio_policy": {
                    "original_audio_policy": "preserve_speech",
                    "music_policy": "bgm",
                    "time_authority": "video_sections",
                },
                "sections": [
                    {"section_id": "director_words", "start_sec": 0.0, "duration_sec": 2.0}
                ],
                "tracks": [
                    {
                        "section_id": "director_words",
                        "audio_file": str(music),
                        "role": "music_bed",
                        "ducking_policy": "duck_under_voice",
                        "source_type": "jamendo",
                        "license_status": "accepted",
                    },
                    {
                        "section_id": "director_words",
                        "audio_file": str(voice),
                        "role": "voice",
                        "ducking_policy": "preserve_original_audio",
                        "source_type": "original_audio",
                        "license_status": "accepted",
                    },
                ],
            })

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/audio_mix_plan_execute.py",
                    "--plan",
                    str(plan),
                    "--acceptance",
                    str(acceptance),
                    "--out-dir",
                    str(root),
                    "--json",
                ],
                cwd=repo,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads((root / "audio_mix_report.json").read_text(encoding="utf-8"))
            music_placement = next(p for p in payload["placements"] if p["role"] == "music_bed")
            voice_placement = next(p for p in payload["placements"] if p["role"] == "voice")
            self.assertTrue(payload["ducking_applied"])
            self.assertEqual(payload["source_audio_policy"]["original_audio_policy"], "preserve_speech")
            self.assertTrue(music_placement["ducking_applied"])
            self.assertAlmostEqual(music_placement["applied_volume"], 0.28, delta=0.01)
            self.assertFalse(voice_placement["ducking_applied"])
            self.assertAlmostEqual(voice_placement["applied_volume"], 1.0, delta=0.01)

    def test_preview_only_mix_carries_contract_and_stops_for_review(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            music = root / "audio" / "sources" / "candidate_l2_bgm.wav"
            speech = root / "audio" / "sources" / "original_speech.wav"
            music.parent.mkdir(parents=True)
            _sine(music, 1.0)
            _sine(speech, 1.0)
            acceptance = _write_json(root, "audio_handoff_acceptance.json", {
                "artifact_role": "audio_handoff_acceptance",
                "ok": True,
                "accepted_track_count": 2,
                "preview_only": True,
                "delivery_allowed": False,
                "external_publication_requires_rights_review": True,
            })
            plan = _write_json(root, "audio_mix_plan.json", {
                "artifact_role": "audio_mix_plan",
                "ready_for_mix": True,
                "preview_only": True,
                "delivery_allowed": False,
                "mix_allowed": True,
                "usage_scope": "internal_technical_reference",
                "external_publication_requires_rights_review": True,
                "source_audio_policy": {
                    "original_audio_policy": "preserve_speech",
                    "music_policy": "bgm",
                    "time_authority": "video_sections",
                },
                "sections": [{
                    "section_id": "interview",
                    "start_sec": 0.0,
                    "duration_sec": 1.0,
                    "audio_required": True,
                }],
                "tracks": [
                    {
                        "section_id": "interview",
                        "candidate_id": "candidate_l2_bgm",
                        "audio_file": str(music),
                        "role": "music_bed",
                        "ducking_policy": "duck_under_voice",
                        "source_type": "candidate_l2_internal_reference",
                        "license_status": "not_reapproved_for_delivery",
                        "mix_allowed": True,
                        "preview_only": True,
                        "delivery_allowed": False,
                        "usage_scope": "internal_technical_reference",
                        "music_use_basis": {
                            "status": "pipeline_default_internal_preview",
                            "usage_scope": "internal_technical_reference",
                            "declared_by": "pipeline_policy",
                            "legal_approval_claimed": False,
                            "external_publication_requires_rights_review": True,
                        },
                    },
                    {
                        "section_id": "interview",
                        "candidate_id": "original_speech",
                        "audio_file": str(speech),
                        "role": "source_speech",
                        "ducking_policy": "preserve_original_audio",
                        "source_type": "original_audio",
                        "license_status": "source_original",
                        "delivery_allowed": True,
                    },
                ],
            })

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/audio_mix_plan_execute.py",
                    "--plan",
                    str(plan),
                    "--acceptance",
                    str(acceptance),
                    "--out-dir",
                    str(root),
                    "--output-name",
                    "interview_audio_preview.wav",
                    "--json",
                ],
                cwd=repo,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            report = json.loads((root / "audio_mix_report.json").read_text(encoding="utf-8"))
            self.assertTrue(report["ok"])
            self.assertTrue(report["preview_only"])
            self.assertFalse(report["delivery_allowed"])
            self.assertTrue(report["external_publication_requires_rights_review"])
            self.assertEqual(report["next_action"], "review_internal_audio_preview")
            self.assertTrue(report["ducking_applied"])
            bgm = next(track for track in report["tracks"] if track["candidate_id"] == "candidate_l2_bgm")
            self.assertTrue(bgm["preview_only"])
            self.assertFalse(bgm["delivery_allowed"])
            self.assertEqual(bgm["music_use_basis"]["status"], "pipeline_default_internal_preview")
            self.assertTrue((root / "interview_audio_preview.wav").is_file())

    def test_preview_only_plan_with_delivery_true_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = execute_audio_mix_plan(
                {
                    "artifact_role": "audio_mix_plan",
                    "ready_for_mix": True,
                    "preview_only": True,
                    "delivery_allowed": True,
                    "tracks": [],
                },
                acceptance={"ok": True},
                out_dir=root,
            )

            self.assertFalse(result["ok"])
            rules = {item["rule"] for item in result["audio_mix_report"]["blocking"]}
            self.assertIn("contradictory_preview_delivery_contract", rules)

    def test_blocks_required_section_without_audio_placement(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            intro = root / "audio" / "sources" / "intro.wav"
            intro.parent.mkdir(parents=True)
            _sine(intro, 1.0)
            acceptance = _write_json(root, "audio_handoff_acceptance.json", {
                "artifact_role": "audio_handoff_acceptance",
                "ok": True,
                "accepted_track_count": 1,
            })
            plan = _write_json(root, "audio_mix_plan.json", {
                "artifact_role": "audio_mix_plan",
                "ready_for_mix": True,
                "sections": [
                    {"section_id": "intro", "start_sec": 0.0, "duration_sec": 1.0, "audio_required": True},
                    {"section_id": "ending", "start_sec": 1.0, "duration_sec": 1.0, "audio_required": True},
                ],
                "tracks": [{
                    "section_id": "intro",
                    "audio_file": str(intro),
                    "role": "music_bed",
                    "source_type": "jamendo",
                    "license_status": "accepted",
                }],
            })

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/audio_mix_plan_execute.py",
                    "--plan",
                    str(plan),
                    "--acceptance",
                    str(acceptance),
                    "--out-dir",
                    str(root),
                    "--json",
                ],
                cwd=repo,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            payload = json.loads((root / "audio_mix_report.json").read_text(encoding="utf-8"))
            self.assertFalse(payload["ok"])
            rules = {item["rule"] for item in payload["blocking"]}
            self.assertIn("required_section_has_no_audio", rules)

    def test_diverse_section_mix_records_story_music_voice_and_verify_evidence(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_dir = root / "audio" / "sources"
            source_dir.mkdir(parents=True)
            paths = {
                "intro": source_dir / "intro.wav",
                "warm": source_dir / "warm.wav",
                "voice": source_dir / "voice.wav",
                "drive": source_dir / "drive.wav",
                "climax": source_dir / "climax.wav",
                "ending": source_dir / "ending.wav",
            }
            for path in paths.values():
                _sine(path, 2.0)
            acceptance = _write_json(root, "audio_handoff_acceptance.json", {
                "artifact_role": "audio_handoff_acceptance",
                "ok": True,
                "accepted_track_count": 6,
            })
            plan = _write_json(root, "audio_mix_plan.json", {
                "artifact_role": "audio_mix_plan",
                "ready_for_mix": True,
                "sections": [
                    {"section_id": "intro", "start_sec": 0.0, "duration_sec": 1.0, "audio_required": True},
                    {"section_id": "warm_story", "start_sec": 1.0, "duration_sec": 2.0, "audio_required": True},
                    {"section_id": "training_drive", "start_sec": 3.0, "duration_sec": 1.5, "audio_required": True},
                    {"section_id": "mv_climax", "start_sec": 4.5, "duration_sec": 1.5, "audio_required": True},
                    {"section_id": "ending_reflection", "start_sec": 6.0, "duration_sec": 1.0, "audio_required": True},
                ],
                "tracks": [
                    {"section_id": "intro", "audio_file": str(paths["intro"]), "role": "music_bed", "fade_in_sec": 0.1, "fade_out_sec": 0.1},
                    {"section_id": "warm_story", "audio_file": str(paths["warm"]), "role": "music_bed", "ducking_policy": "duck_under_voice"},
                    {"section_id": "warm_story", "audio_file": str(paths["voice"]), "role": "voice", "ducking_policy": "preserve_original_audio"},
                    {"section_id": "training_drive", "audio_file": str(paths["drive"]), "role": "music_bed"},
                    {"section_id": "mv_climax", "audio_file": str(paths["climax"]), "role": "music_main"},
                    {"section_id": "ending_reflection", "audio_file": str(paths["ending"]), "role": "music_bed", "fade_out_sec": 0.2},
                ],
            })

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/audio_mix_plan_execute.py",
                    "--plan",
                    str(plan),
                    "--acceptance",
                    str(acceptance),
                    "--out-dir",
                    str(root),
                    "--json",
                ],
                cwd=repo,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads((root / "audio_mix_report.json").read_text(encoding="utf-8"))
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["mix_mode"], "section_timeline")
            self.assertEqual(payload["section_verification"]["required_section_count"], 5)
            self.assertEqual(payload["section_verification"]["missing_required_sections"], [])
            self.assertEqual({p["section_id"] for p in payload["placements"]}, set(payload["section_verification"]["covered_sections"]))
            self.assertTrue(payload["ducking_applied"])
            self.assertLessEqual(payload["peak_dbfs"], -0.5)
            self.assertAlmostEqual(_duration(root / "final_audio.wav"), 7.0, delta=0.3)


if __name__ == "__main__":
    unittest.main()
