import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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


class AudioMixPlanExecutorTest(unittest.TestCase):
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
