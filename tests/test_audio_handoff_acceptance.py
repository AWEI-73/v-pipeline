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
    def test_accepts_explicit_preview_false_as_delivery_track(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio = root / "source_speech.wav"
            audio.write_bytes(b"RIFF original speech")
            handoff = {
                "artifact_role": "audio_director_handoff",
                "ready_for_audio_director": True,
                "selected_audio_files": [{
                    "candidate_id": "source_speech",
                    "section_id": "interview",
                    "source_type": "original_audio",
                    "audio_file": str(audio),
                    "license_status": "source_original",
                    "preview_only": False,
                    "delivery_allowed": True,
                    "ducking_policy": "preserve_original_audio",
                }],
            }

            result = accept_audio_handoff(handoff, out_dir=root)

            self.assertTrue(result["audio_handoff_acceptance"]["ok"])
            track = result["audio_mix_plan"]["tracks"][0]
            self.assertFalse(track["preview_only"])
            self.assertTrue(track["delivery_allowed"])

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

    def test_accepts_human_declared_source_folder_music_for_internal_rehearsal_without_legal_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            music = root / "source" / "music" / "opening.wav"
            music.parent.mkdir(parents=True)
            music.write_bytes(b"RIFF source folder music")
            basis = {
                "status": "human_declared_allowed",
                "usage_scope": "internal_rehearsal",
                "declared_by": "human",
                "basis_note": "User allowed source-folder music for internal review.",
                "legal_approval_claimed": False,
            }
            handoff = {
                "artifact_role": "audio_director_handoff",
                "ready_for_audio_director": True,
                "selected_audio_files": [{
                    "candidate_id": "source_music_opening",
                    "section_id": "opening",
                    "source_type": "source_folder_audio",
                    "audio_file": str(music),
                    "source_relative_path": "music/opening.wav",
                    "license_status": "human_declared_allowed",
                    "usage_scope": "internal_rehearsal",
                    "music_use_basis": basis,
                    "delivery_allowed": True,
                }],
            }
            soundtrack = {
                "artifact_role": "soundtrack_plan",
                "sections": [{
                    "section_id": "opening",
                    "duration_sec": 6,
                    "music_role": "bgm",
                    "ducking_policy": "none",
                    "vocal_policy": "instrumental_preferred",
                }],
            }
            manifest = {
                "artifact_role": "sound_license_manifest",
                "delivery_allowed": True,
                "legal_approval_claimed": False,
                "music_use_basis": basis,
            }

            result = accept_audio_handoff(
                handoff,
                soundtrack_plan=soundtrack,
                sound_license_manifest=manifest,
                soundtrack_probe_report=_probe_for(music),
                out_dir=root,
            )

            self.assertTrue(result["audio_handoff_acceptance"]["ok"])
            track = result["audio_mix_plan"]["tracks"][0]
            self.assertEqual(track["source_type"], "source_folder_audio")
            self.assertEqual(track["license_status"], "human_declared_allowed")
            self.assertEqual(track["music_use_basis"]["status"], "human_declared_allowed")
            self.assertFalse(track["legal_approval_claimed"])

    def test_accepts_default_internal_preview_without_human_basis(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            music = root / "audio" / "sources" / "candidate_l2_bgm.wav"
            speech = root / "audio" / "sources" / "original_speech.wav"
            music.parent.mkdir(parents=True)
            music.write_bytes(b"RIFF preview music")
            speech.write_bytes(b"RIFF original speech")
            handoff = {
                "artifact_role": "audio_director_handoff",
                "ready_for_audio_director": True,
                "selected_audio_files": [
                    {
                        "candidate_id": "candidate_l2_bgm",
                        "section_id": "interview",
                        "source_type": "candidate_l2_internal_reference",
                        "audio_file": str(music),
                        "license_status": "not_reapproved_for_delivery",
                        "preview_only": True,
                        "delivery_allowed": False,
                        "usage_scope": "internal_technical_reference",
                    },
                    {
                        "candidate_id": "interview_original_speech",
                        "section_id": "interview",
                        "source_type": "original_audio",
                        "audio_file": str(speech),
                        "license_status": "source_original",
                        "delivery_allowed": True,
                        "ducking_policy": "preserve_original_audio",
                    },
                ],
            }
            soundtrack = {
                "artifact_role": "soundtrack_plan",
                "required_track_count": 2,
                "sections": [{
                    "section_id": "interview",
                    "start_sec": 0,
                    "duration_sec": 22,
                    "music_role": "bgm",
                    "ducking_policy": "duck_under_voice",
                    "vocal_policy": "preserve_speech",
                }],
            }

            result = accept_audio_handoff(
                handoff,
                soundtrack_plan=soundtrack,
                soundtrack_probe_report=_probe_for(music),
                out_dir=root,
            )

            acceptance = result["audio_handoff_acceptance"]
            plan = result["audio_mix_plan"]
            self.assertTrue(acceptance["ok"])
            self.assertEqual(acceptance["accepted_track_count"], 2)
            self.assertEqual(acceptance["next_action"], "audio_preview_mix_plan_ready")
            self.assertTrue(acceptance["preview_only"])
            self.assertFalse(acceptance["delivery_allowed"])
            self.assertTrue(acceptance["external_publication_requires_rights_review"])
            self.assertTrue(plan["ready_for_mix"])
            self.assertTrue(plan["preview_only"])
            self.assertFalse(plan["delivery_allowed"])
            bgm = next(track for track in plan["tracks"] if track["candidate_id"] == "candidate_l2_bgm")
            self.assertTrue(bgm["mix_allowed"])
            self.assertTrue(bgm["preview_only"])
            self.assertFalse(bgm["delivery_allowed"])
            self.assertEqual(bgm["usage_scope"], "internal_technical_reference")
            self.assertEqual(bgm["music_use_basis"]["status"], "pipeline_default_internal_preview")
            self.assertEqual(bgm["music_use_basis"]["declared_by"], "pipeline_policy")
            self.assertFalse(bgm["music_use_basis"]["legal_approval_claimed"])
            self.assertTrue(bgm["music_use_basis"]["external_publication_requires_rights_review"])

    def test_blocks_preview_when_mix_allowed_is_explicitly_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            music = root / "audio" / "sources" / "candidate_l2_bgm.wav"
            music.parent.mkdir(parents=True)
            music.write_bytes(b"RIFF preview music")
            handoff = {
                "artifact_role": "audio_director_handoff",
                "ready_for_audio_director": True,
                "selected_audio_files": [{
                    "candidate_id": "candidate_l2_bgm",
                    "section_id": "interview",
                    "source_type": "candidate_l2_internal_reference",
                    "audio_file": str(music),
                    "license_status": "not_reapproved_for_delivery",
                    "preview_only": True,
                    "mix_allowed": False,
                    "delivery_allowed": False,
                    "usage_scope": "internal_technical_reference",
                }],
            }
            soundtrack = {
                "artifact_role": "soundtrack_plan",
                "sections": [{
                    "section_id": "interview",
                    "duration_sec": 22,
                    "music_role": "bgm",
                    "ducking_policy": "duck_under_voice",
                    "vocal_policy": "preserve_speech",
                }],
            }

            result = accept_audio_handoff(
                handoff,
                soundtrack_plan=soundtrack,
                soundtrack_probe_report=_probe_for(music),
                out_dir=root,
            )

            self.assertFalse(result["audio_handoff_acceptance"]["ok"])
            rules = {item["rule"] for item in result["audio_handoff_acceptance"]["blocking"]}
            self.assertIn("preview_mix_not_allowed", rules)

    def test_preview_music_still_requires_soundtrack_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            music = root / "audio" / "sources" / "candidate_l2_bgm.wav"
            music.parent.mkdir(parents=True)
            music.write_bytes(b"RIFF preview music")
            handoff = {
                "artifact_role": "audio_director_handoff",
                "ready_for_audio_director": True,
                "selected_audio_files": [{
                    "candidate_id": "candidate_l2_bgm",
                    "section_id": "interview",
                    "source_type": "candidate_l2_internal_reference",
                    "audio_file": str(music),
                    "license_status": "not_reapproved_for_delivery",
                    "preview_only": True,
                    "delivery_allowed": False,
                    "usage_scope": "internal_technical_reference",
                }],
            }
            soundtrack = {
                "artifact_role": "soundtrack_plan",
                "sections": [{
                    "section_id": "interview",
                    "duration_sec": 22,
                    "music_role": "bgm",
                    "ducking_policy": "duck_under_voice",
                    "vocal_policy": "preserve_speech",
                }],
            }

            result = accept_audio_handoff(handoff, soundtrack_plan=soundtrack, out_dir=root)

            self.assertFalse(result["audio_handoff_acceptance"]["ok"])
            rules = {item["rule"] for item in result["audio_handoff_acceptance"]["blocking"]}
            self.assertIn("missing_soundtrack_probe_report", rules)

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
