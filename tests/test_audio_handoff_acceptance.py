import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.audio_handoff_acceptance import accept_audio_handoff


def _write(root, name, payload):
    path = Path(root) / name
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _probe_for(audio_file):
    return {
        "artifact_role": "soundtrack_probe_report",
        "version": 1,
        "pass": True,
        "audio_file": str(audio_file),
        "duration_sec": 30.0,
        "features": {"mean_dbfs": -18.0, "peak_dbfs": -3.0},
        "sections": [{"start_sec": 0.0, "end_sec": 30.0, "role": "full_track"}],
        "editing_fit": {"montage": "medium", "speech_underlay": "high"},
        "section_fit": [{"video_section": "hotblooded_montage", "fit": "medium"}],
    }


class AudioHandoffAcceptanceTest(unittest.TestCase):
    def test_accepts_downloaded_music_and_writes_mix_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio = root / "audio" / "sources" / "mv.mp3"
            audio.parent.mkdir(parents=True)
            audio.write_bytes(b"ID3 fake")
            handoff = {
                "artifact_role": "audio_director_handoff",
                "ready_for_audio_director": True,
                "selected_audio_files": [{
                    "candidate_id": "url_mv_climax",
                    "section_id": "mv_climax",
                    "source_type": "youtube_audio_library",
                    "audio_file": str(audio),
                    "license_status": "user_asserted",
                    "usage_scope": "internal_only",
                    "delivery_allowed": True,
                }],
            }
            soundtrack = {
                "artifact_role": "soundtrack_plan",
                "sections": [{
                    "section_id": "mv_climax",
                    "music_role": "song",
                    "ducking_policy": "none",
                    "vocal_policy": "vocal_ok",
                }],
            }

            result = accept_audio_handoff(
                handoff,
                soundtrack_plan=soundtrack,
                soundtrack_probe_report=_probe_for(audio),
                out_dir=root,
            )

            self.assertTrue(result["audio_handoff_acceptance"]["ok"])
            self.assertEqual(result["audio_mix_plan"]["tracks"][0]["role"], "music_main")
            self.assertEqual(result["audio_mix_plan"]["tracks"][0]["section_id"], "mv_climax")
            self.assertTrue((root / "audio_handoff_acceptance.json").is_file())
            self.assertTrue((root / "audio_mix_plan.json").is_file())

    def test_mix_plan_includes_section_timeline_when_soundtrack_has_durations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio = root / "audio" / "sources" / "mv.mp3"
            audio.parent.mkdir(parents=True)
            audio.write_bytes(b"ID3 fake")
            handoff = {
                "artifact_role": "audio_director_handoff",
                "ready_for_audio_director": True,
                "selected_audio_files": [{
                    "candidate_id": "jamendo_mv_climax",
                    "section_id": "mv_climax",
                    "source_type": "jamendo_song",
                    "audio_file": str(audio),
                    "license_status": "user_asserted",
                    "delivery_allowed": True,
                }],
            }
            soundtrack = {
                "artifact_role": "soundtrack_plan",
                "sections": [
                    {"section_id": "intro", "duration_sec": 8, "music_role": "bgm"},
                    {"section_id": "warm_story", "duration_sec": 12, "music_role": "bgm"},
                    {"section_id": "mv_climax", "duration_sec": 10, "music_role": "song", "vocal_policy": "vocal_ok"},
                ],
            }

            result = accept_audio_handoff(
                handoff,
                soundtrack_plan=soundtrack,
                soundtrack_probe_report=_probe_for(audio),
                out_dir=root,
            )

            self.assertTrue(result["audio_handoff_acceptance"]["ok"])
            sections = result["audio_mix_plan"]["sections"]
            self.assertEqual(
                [(item["section_id"], item["start_sec"], item["duration_sec"]) for item in sections],
                [("intro", 0.0, 8.0), ("warm_story", 8.0, 12.0), ("mv_climax", 20.0, 10.0)],
            )
            self.assertEqual(result["audio_mix_plan"]["tracks"][0]["section_id"], "mv_climax")

    def test_blocks_reference_only_and_missing_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            handoff = {
                "artifact_role": "audio_director_handoff",
                "ready_for_audio_director": True,
                "selected_audio_files": [{
                    "candidate_id": "ref",
                    "section_id": "mv_climax",
                    "source_type": "reference_only",
                    "audio_file": str(root / "missing.mp3"),
                    "license_status": "reference_only",
                    "delivery_allowed": False,
                }],
            }

            result = accept_audio_handoff(handoff, out_dir=root)

            self.assertFalse(result["audio_handoff_acceptance"]["ok"])
            rules = {item["rule"] for item in result["audio_handoff_acceptance"]["blocking"]}
            self.assertIn("reference_only_source", rules)
            self.assertIn("audio_file_missing", rules)
            self.assertEqual(result["audio_mix_plan"]["tracks"], [])

    def test_blocks_preserve_speech_without_ducking_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio = root / "speech_bgm.mp3"
            audio.write_bytes(b"ID3 fake")
            handoff = {
                "artifact_role": "audio_director_handoff",
                "ready_for_audio_director": True,
                "selected_audio_files": [{
                    "candidate_id": "speech_bgm",
                    "section_id": "director_speech",
                    "source_type": "licensed_library",
                    "audio_file": str(audio),
                    "license_status": "user_asserted",
                    "delivery_allowed": True,
                }],
            }
            soundtrack = {
                "artifact_role": "soundtrack_plan",
                "sections": [{
                    "section_id": "director_speech",
                    "music_role": "bgm",
                    "ducking_policy": "none",
                    "vocal_policy": "preserve_speech",
                }],
            }

            result = accept_audio_handoff(
                handoff,
                soundtrack_plan=soundtrack,
                soundtrack_probe_report=_probe_for(audio),
                out_dir=root,
            )

            self.assertFalse(result["audio_handoff_acceptance"]["ok"])
            self.assertIn(
                "speech_ducking_missing",
                {item["rule"] for item in result["audio_handoff_acceptance"]["blocking"]},
            )

    def test_accepts_music_and_original_voice_tracks_for_speech_ducking(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            music = root / "audio" / "sources" / "music.wav"
            voice = root / "audio" / "sources" / "voice.wav"
            music.parent.mkdir(parents=True)
            music.write_bytes(b"RIFF music")
            voice.write_bytes(b"RIFF voice")
            handoff = {
                "artifact_role": "audio_director_handoff",
                "ready_for_audio_director": True,
                "selected_audio_files": [
                    {
                        "candidate_id": "speech_bgm",
                        "section_id": "director_speech",
                        "source_type": "licensed_library",
                        "audio_file": str(music),
                        "license_status": "user_asserted",
                        "delivery_allowed": True,
                        "ducking_policy": "duck_under_voice",
                    },
                    {
                        "candidate_id": "director_original_voice",
                        "section_id": "director_speech",
                        "source_type": "original_audio",
                        "audio_file": str(voice),
                        "license_status": "source_is_original_material",
                        "delivery_allowed": True,
                        "ducking_policy": "preserve_original_audio",
                    },
                ],
            }
            soundtrack = {
                "artifact_role": "soundtrack_plan",
                "sections": [{
                    "section_id": "director_speech",
                    "duration_sec": 6,
                    "music_role": "bgm",
                    "ducking_policy": "duck_under_voice",
                    "vocal_policy": "preserve_speech",
                    "audio_required": True,
                }],
            }

            result = accept_audio_handoff(
                handoff,
                soundtrack_plan=soundtrack,
                soundtrack_probe_report=_probe_for(music),
                out_dir=root,
            )

            self.assertTrue(result["audio_handoff_acceptance"]["ok"])
            tracks = result["audio_mix_plan"]["tracks"]
            by_id = {track["candidate_id"]: track for track in tracks}
            self.assertEqual(by_id["speech_bgm"]["role"], "music_ducked")
            self.assertEqual(by_id["speech_bgm"]["ducking_policy"], "duck_under_voice")
            self.assertEqual(by_id["director_original_voice"]["role"], "preserve_original_audio")
            self.assertEqual(by_id["director_original_voice"]["ducking_policy"], "preserve_original_audio")
            policy = result["audio_mix_plan"]["source_audio_policy"]
            self.assertEqual(policy["original_audio_policy"], "preserve_speech")
            self.assertEqual(policy["music_policy"], "bgm")
            self.assertEqual(policy["time_authority"], "video_sections")

    def test_mix_plan_records_replace_source_audio_policy_for_music_only_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            music = root / "audio" / "sources" / "music.wav"
            music.parent.mkdir(parents=True)
            music.write_bytes(b"RIFF music")
            handoff = {
                "artifact_role": "audio_director_handoff",
                "ready_for_audio_director": True,
                "selected_audio_files": [{
                    "candidate_id": "highlight_bgm",
                    "section_id": "highlight",
                    "source_type": "licensed_library",
                    "audio_file": str(music),
                    "license_status": "user_asserted",
                    "delivery_allowed": True,
                }],
            }
            soundtrack = {
                "artifact_role": "soundtrack_plan",
                "source_audio_policy": {
                    "original_audio_policy": "replace_with_music",
                    "music_policy": "bgm",
                    "time_authority": "video_sections",
                },
                "sections": [{
                    "section_id": "highlight",
                    "duration_sec": 4,
                    "music_role": "bgm",
                    "ducking_policy": "none",
                    "vocal_policy": "instrumental_preferred",
                }],
            }

            result = accept_audio_handoff(
                handoff,
                soundtrack_plan=soundtrack,
                soundtrack_probe_report=_probe_for(music),
                out_dir=root,
            )

            self.assertTrue(result["audio_handoff_acceptance"]["ok"])
            self.assertEqual(
                result["audio_mix_plan"]["source_audio_policy"]["original_audio_policy"],
                "replace_with_music",
            )

    def test_blocks_selected_music_without_soundtrack_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            music = root / "audio" / "sources" / "music.wav"
            music.parent.mkdir(parents=True)
            music.write_bytes(b"RIFF music")
            handoff = {
                "artifact_role": "audio_director_handoff",
                "ready_for_audio_director": True,
                "selected_audio_files": [{
                    "candidate_id": "highlight_bgm",
                    "section_id": "highlight",
                    "source_type": "licensed_library",
                    "audio_file": str(music),
                    "license_status": "user_asserted",
                    "delivery_allowed": True,
                }],
            }
            soundtrack = {
                "artifact_role": "soundtrack_plan",
                "sections": [{
                    "section_id": "highlight",
                    "duration_sec": 4,
                    "music_role": "bgm",
                    "ducking_policy": "none",
                    "vocal_policy": "instrumental_preferred",
                }],
            }

            result = accept_audio_handoff(handoff, soundtrack_plan=soundtrack, out_dir=root)

            self.assertFalse(result["audio_handoff_acceptance"]["ok"])
            rules = {item["rule"] for item in result["audio_handoff_acceptance"]["blocking"]}
            self.assertIn("missing_soundtrack_probe_report", rules)
            self.assertEqual(result["audio_handoff_acceptance"]["next_action"], "run_soundtrack_probe")

    def test_cli_writes_acceptance_and_mix_plan(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio = root / "audio" / "sources" / "mv.mp3"
            audio.parent.mkdir(parents=True)
            audio.write_bytes(b"ID3 fake")
            handoff = _write(root, "audio_director_handoff.json", {
                "artifact_role": "audio_director_handoff",
                "ready_for_audio_director": True,
                "selected_audio_files": [{
                    "candidate_id": "url_mv_climax",
                    "section_id": "mv_climax",
                    "source_type": "youtube_audio_library",
                    "audio_file": str(audio),
                    "license_status": "user_asserted",
                    "usage_scope": "internal_only",
                    "delivery_allowed": True,
                }],
            })
            soundtrack = _write(root, "soundtrack_plan.json", {
                "artifact_role": "soundtrack_plan",
                "sections": [{
                    "section_id": "mv_climax",
                    "music_role": "song",
                    "ducking_policy": "none",
                    "vocal_policy": "vocal_ok",
                }],
            })
            probe = _write(root, "soundtrack_probe_report.json", _probe_for(audio))

            proc = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "soundtrack-audio-handoff-accept",
                    "--handoff",
                    str(handoff),
                    "--soundtrack-plan",
                    str(soundtrack),
                    "--out-dir",
                    str(root),
                    "--soundtrack-probe-report",
                    str(probe),
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((root / "audio_handoff_acceptance.json").is_file())
            self.assertTrue((root / "audio_mix_plan.json").is_file())


if __name__ == "__main__":
    unittest.main()
