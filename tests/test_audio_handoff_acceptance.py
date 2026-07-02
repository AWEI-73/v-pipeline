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
        "features": {
            "mean_dbfs": -18.0,
            "peak_dbfs": -3.0,
            "vocal_analysis": {
                "has_vocals": False,
                "method": "faster_whisper",
                "vocal_density": "none",
                "vocal_ratio": 0.0,
                "segments": [],
            },
        },
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

    def test_accepts_multi_section_probe_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            intro = root / "audio" / "sources" / "intro.mp3"
            climax = root / "audio" / "sources" / "climax.mp3"
            intro.parent.mkdir(parents=True)
            intro.write_bytes(b"ID3 intro")
            climax.write_bytes(b"ID3 climax")
            handoff = {
                "artifact_role": "audio_director_handoff",
                "ready_for_audio_director": True,
                "selected_audio_files": [
                    {
                        "candidate_id": "jamendo_intro",
                        "section_id": "intro",
                        "source_type": "jamendo_song",
                        "audio_file": str(intro),
                        "license_status": "license_metadata_present",
                        "delivery_allowed": True,
                    },
                    {
                        "candidate_id": "jamendo_mv_climax",
                        "section_id": "mv_climax",
                        "source_type": "jamendo_song",
                        "audio_file": str(climax),
                        "license_status": "license_metadata_present",
                        "delivery_allowed": True,
                    },
                ],
            }
            soundtrack = {
                "artifact_role": "soundtrack_plan",
                "sections": [
                    {"section_id": "intro", "duration_sec": 8, "music_role": "song"},
                    {"section_id": "mv_climax", "duration_sec": 12, "music_role": "song"},
                ],
            }
            intro_probe = _probe_for(intro)
            intro_probe["candidate_id"] = "jamendo_intro"
            intro_probe["section_id"] = "intro"
            climax_probe = _probe_for(climax)
            climax_probe["candidate_id"] = "jamendo_mv_climax"
            climax_probe["section_id"] = "mv_climax"
            probe_bundle = {
                "artifact_role": "soundtrack_probe_bundle",
                "version": 1,
                "track_reports": [intro_probe, climax_probe],
            }

            result = accept_audio_handoff(
                handoff,
                soundtrack_plan=soundtrack,
                soundtrack_probe_report=probe_bundle,
                out_dir=root,
            )

            self.assertTrue(result["audio_handoff_acceptance"]["ok"])
            self.assertEqual(result["audio_handoff_acceptance"]["accepted_track_count"], 2)
            self.assertEqual(
                {track["candidate_id"] for track in result["audio_mix_plan"]["tracks"]},
                {"jamendo_intro", "jamendo_mv_climax"},
            )

    def test_blocks_when_selected_tracks_do_not_meet_required_track_count(self):
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
                    "license_status": "license_metadata_present",
                    "delivery_allowed": True,
                }],
            }
            soundtrack = {
                "artifact_role": "soundtrack_plan",
                "required_track_count": 2,
                "sections": [
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

            self.assertFalse(result["audio_handoff_acceptance"]["ok"])
            rules = {item["rule"] for item in result["audio_handoff_acceptance"]["blocking"]}
            self.assertIn("required_track_count_not_met", rules)
            self.assertEqual(result["audio_handoff_acceptance"]["accepted_track_count"], 1)

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
            self.assertEqual(result["audio_handoff_acceptance"]["next_action"], "run_soundtrack_probe_with_asr")

    def test_blocks_vocal_heavy_music_under_voiceover(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            music = root / "audio" / "sources" / "vocal_song.mp3"
            music.parent.mkdir(parents=True)
            music.write_bytes(b"ID3 vocal")
            handoff = {
                "artifact_role": "audio_director_handoff",
                "ready_for_audio_director": True,
                "selected_audio_files": [{
                    "candidate_id": "vocal_story_bed",
                    "section_id": "warm_story",
                    "source_type": "youtube_audio_library",
                    "audio_file": str(music),
                    "license_status": "user_asserted",
                    "delivery_allowed": True,
                    "ducking_policy": "duck_under_voice",
                }],
            }
            soundtrack = {
                "artifact_role": "soundtrack_plan",
                "sections": [{
                    "section_id": "warm_story",
                    "duration_sec": 20,
                    "music_role": "bgm",
                    "ducking_policy": "duck_under_voice",
                    "vocal_policy": "instrumental_required",
                }],
            }
            probe = _probe_for(music)
            probe["features"]["vocal_analysis"] = {
                "has_vocals": True,
                "method": "faster_whisper",
                "vocal_density": "high",
                "vocal_ratio": 0.58,
                "segments": [{"start_sec": 0.0, "end_sec": 12.0, "text": "lyrics"}],
                "instrumental_windows": [{"start_sec": 12.0, "end_sec": 30.0}],
            }

            result = accept_audio_handoff(
                handoff,
                soundtrack_plan=soundtrack,
                soundtrack_probe_report=probe,
                out_dir=root,
            )

            self.assertFalse(result["audio_handoff_acceptance"]["ok"])
            rules = {item["rule"] for item in result["audio_handoff_acceptance"]["blocking"]}
            self.assertIn("vocal_music_conflicts_with_voiceover", rules)
            self.assertEqual(
                result["audio_handoff_acceptance"]["next_action"],
                "select_instrumental_music_or_use_instrumental_window",
            )

    def test_requires_asr_vocal_analysis_for_voiceover_bed_music(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            music = root / "audio" / "sources" / "unknown.mp3"
            music.parent.mkdir(parents=True)
            music.write_bytes(b"ID3 unknown")
            handoff = {
                "artifact_role": "audio_director_handoff",
                "ready_for_audio_director": True,
                "selected_audio_files": [{
                    "candidate_id": "unknown_story_bed",
                    "section_id": "warm_story",
                    "source_type": "licensed_library",
                    "audio_file": str(music),
                    "license_status": "user_asserted",
                    "delivery_allowed": True,
                    "ducking_policy": "duck_under_voice",
                }],
            }
            soundtrack = {
                "artifact_role": "soundtrack_plan",
                "sections": [{
                    "section_id": "warm_story",
                    "duration_sec": 20,
                    "music_role": "bgm",
                    "ducking_policy": "duck_under_voice",
                    "vocal_policy": "instrumental_required",
                }],
            }
            probe = _probe_for(music)
            probe["features"]["vocal_analysis"] = {"has_vocals": "unknown", "method": "not_run"}

            result = accept_audio_handoff(
                handoff,
                soundtrack_plan=soundtrack,
                soundtrack_probe_report=probe,
                out_dir=root,
            )

            self.assertFalse(result["audio_handoff_acceptance"]["ok"])
            rules = {item["rule"] for item in result["audio_handoff_acceptance"]["blocking"]}
            self.assertIn("soundtrack_probe_missing_vocal_analysis", rules)
            self.assertEqual(result["audio_handoff_acceptance"]["next_action"], "run_soundtrack_probe_with_asr")

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
