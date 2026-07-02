import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.soundtrack_arranger import arrange_soundtrack, write_soundtrack_artifacts


class SoundtrackArrangerTest(unittest.TestCase):
    def test_training_recap_plan_splits_sections_and_preserves_speech(self):
        plan = arrange_soundtrack(
            {
                "video_type": "training graduation recap",
                "target_length": "about 5 minutes",
                "style_direction": "first half warm story, second half hot-blooded MV with song feeling",
                "audience": "students, instructors, family, coworkers",
                "speech_critical": ["director speech", "student chants"],
            }
        )

        self.assertEqual(plan["soundtrack_plan"]["artifact_role"], "soundtrack_plan")
        self.assertEqual(plan["soundtrack_plan"]["target_duration_sec"], 300)
        sections = {item["section_id"]: item for item in plan["soundtrack_plan"]["sections"]}
        self.assertEqual(sections["warm_story"]["music_role"], "bgm")
        self.assertEqual(sections["mv_climax"]["music_role"], "song")
        self.assertEqual(sections["mv_climax"]["energy_curve"], "high")
        self.assertEqual(sections["director_speech"]["vocal_policy"], "preserve_speech")
        self.assertEqual(sections["director_speech"]["ducking_policy"], "duck_under_voice")
        self.assertEqual(sections["student_chants"]["ducking_policy"], "preserve_original_audio")

        self.assertEqual(
            plan["music_source_candidates"]["candidates"][0]["source_type"],
            "licensed_library",
        )
        self.assertFalse(plan["sound_license_manifest"]["delivery_allowed"])
        self.assertEqual(plan["audio_director_handoff"]["handoff_to"], "audio-director")
        self.assertIn("license_missing", plan["audio_director_handoff"]["blocks"])

    def test_famous_youtube_song_is_reference_only_not_deliverable(self):
        plan = arrange_soundtrack(
            {
                "request": "use a famous YouTube pop song as the ending MV reference, non commercial",
                "target_length": "2 minutes",
            }
        )

        candidate = next(
            item
            for item in plan["music_source_candidates"]["candidates"]
            if item["section_id"] == "mv_climax"
        )
        self.assertEqual(candidate["source_type"], "reference_only")
        self.assertFalse(candidate["delivery_allowed"])
        self.assertFalse(plan["sound_license_manifest"]["delivery_allowed"])
        self.assertIn("reference_only", plan["audio_director_handoff"]["blocks"])

    def test_video_intent_soundtrack_contract_drives_song_bgm_mix(self):
        plan = arrange_soundtrack(
            {
                "artifact_role": "video_intent",
                "target_length": "5 minutes",
                "soundtrack_contract": {
                    "artifact_role": "stage0_soundtrack_intent",
                    "music_role": "mixed",
                    "vocal_policy": "section_dependent",
                    "energy_intent": "warm_to_high",
                    "speech_preservation": "preserve_if_detected",
                    "fallback_policy": {
                        "provider_fallback": ["jamendo_song", "pixabay_music", "manual_import", "reference_only"],
                        "role_fallback": "song_to_bgm_requires_review",
                        "brownfield_fallback": "workbench_replace_or_retime_after_review",
                    },
                    "handoff_to": "soundtrack-arranger",
                },
            }
        )

        self.assertEqual(plan["soundtrack_plan"]["stage0_soundtrack_contract"]["energy_intent"], "warm_to_high")
        self.assertEqual(
            plan["sound_license_manifest"]["fallback_policy"]["role_fallback"],
            "song_to_bgm_requires_review",
        )
        self.assertIn("role_fallback_requires_review", plan["audio_director_handoff"]["blocks"])
        sections = {item["section_id"]: item for item in plan["soundtrack_plan"]["sections"]}
        self.assertEqual(sections["warm_story"]["music_role"], "bgm")
        self.assertEqual(sections["mv_climax"]["music_role"], "song")
        self.assertEqual(sections["mv_climax"]["vocal_policy"], "vocal_ok")
        self.assertEqual(
            next(
                item
                for item in plan["music_source_candidates"]["candidates"]
                if item["section_id"] == "mv_climax"
            )["source_type"],
            "jamendo_song",
        )

    def test_soundtrack_plan_declares_section_requirement_contract(self):
        plan = arrange_soundtrack(
            {
                "artifact_role": "video_intent",
                "target_length": "5 minutes",
                "soundtrack_contract": {
                    "artifact_role": "stage0_soundtrack_intent",
                    "music_role": "mixed",
                    "vocal_policy": "section_dependent",
                    "speech_preservation": "required",
                    "handoff_to": "soundtrack-arranger",
                },
            }
        )

        soundtrack_plan = plan["soundtrack_plan"]
        self.assertEqual(soundtrack_plan["required_track_count"], 2)
        self.assertEqual(
            soundtrack_plan["section_music_requirements"][0]["section_id"],
            "intro",
        )
        sections = {item["section_id"]: item for item in soundtrack_plan["sections"]}
        self.assertEqual(sections["warm_story"]["required_audio"]["role"], "bgm")
        self.assertTrue(sections["warm_story"]["probe_required"])
        self.assertTrue(sections["warm_story"]["delivery_allowed_requires_license"])
        self.assertIn("manual_import", sections["warm_story"]["source_type_priority"])
        self.assertEqual(sections["mv_climax"]["required_audio"]["role"], "song")
        self.assertIn("jamendo_song", sections["mv_climax"]["source_type_priority"])
        self.assertEqual(
            plan["audio_director_handoff"]["required_track_count"],
            soundtrack_plan["required_track_count"],
        )

    def test_video_intent_soundtrack_contract_overrides_fuzzy_song_words(self):
        plan = arrange_soundtrack(
            {
                "artifact_role": "video_intent",
                "request": "make the ending feel like a pop song MV, but no vocal delivery",
                "target_length": "5 minutes",
                "soundtrack_contract": {
                    "artifact_role": "stage0_soundtrack_intent",
                    "music_role": "bgm",
                    "vocal_policy": "instrumental_preferred",
                    "handoff_to": "soundtrack-arranger",
                },
            }
        )

        sections = {item["section_id"]: item for item in plan["soundtrack_plan"]["sections"]}
        self.assertEqual(sections["mv_climax"]["music_role"], "bgm")
        self.assertEqual(sections["mv_climax"]["vocal_policy"], "no_vocal")
        candidate = next(
            item
            for item in plan["music_source_candidates"]["candidates"]
            if item["section_id"] == "mv_climax"
        )
        self.assertNotEqual(candidate["source_type"], "jamendo_song")

    def test_not_applicable_stage0_soundtrack_contract_suppresses_music_requirements(self):
        plan = arrange_soundtrack(
            {
                "artifact_role": "video_intent",
                "request": "make a silent compliance review cut with no music",
                "target_length": "90 seconds",
                "soundtrack_contract": {
                    "artifact_role": "stage0_soundtrack_intent",
                    "status": "unspecified",
                    "contract_status": "not_applicable",
                    "music_role": "unsure",
                    "handoff_to": "none",
                },
            }
        )

        self.assertEqual(plan["soundtrack_plan"]["required_track_count"], 0)
        self.assertTrue(all(
            section["music_role"] == "silence"
            for section in plan["soundtrack_plan"]["sections"]
        ))
        self.assertEqual(plan["music_source_candidates"]["candidates"], [])
        self.assertTrue(plan["sound_license_manifest"]["delivery_allowed"])
        self.assertTrue(plan["audio_director_handoff"]["ready_for_audio_director"])

    def test_speech_preservation_policy_applies_ducking_to_music_sections(self):
        plan = arrange_soundtrack(
            {
                "artifact_role": "video_intent",
                "target_length": "4 minutes",
                "soundtrack_contract": {
                    "artifact_role": "stage0_soundtrack_intent",
                    "music_role": "bgm",
                    "vocal_policy": "instrumental_preferred",
                    "speech_preservation": "required",
                    "ducking_policy": "duck_under_voice",
                    "handoff_to": "soundtrack-arranger",
                },
            }
        )

        self.assertTrue(all(
            section["ducking_policy"] == "duck_under_voice"
            for section in plan["soundtrack_plan"]["sections"]
            if section["music_role"] == "bgm"
        ))
        self.assertEqual(plan["audio_director_handoff"]["speech_preservation"], "required")

    def test_vocal_song_conflict_blocks_preserved_speech_and_writes_revision_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)

            artifacts = write_soundtrack_artifacts(
                {
                    "artifact_role": "video_intent",
                    "target_length": "4 minutes",
                    "soundtrack_contract": {
                        "artifact_role": "stage0_soundtrack_intent",
                        "music_role": "song",
                        "vocal_policy": "vocal_required",
                        "speech_preservation": "required",
                        "handoff_to": "soundtrack-arranger",
                    },
                },
                run,
            )

            blocks = artifacts["audio_director_handoff"]["blocks"]
            self.assertIn("vocal_conflict_detected", blocks)
            packet_path = run / "soundtrack_revision_packet.json"
            self.assertTrue(packet_path.is_file())
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            self.assertEqual(packet["artifact_role"], "revision_packet")
            self.assertEqual(packet["target_branch"], "soundtrack-arranger")
            self.assertEqual(packet["problem_type"], "audio")
            self.assertTrue(any(
                target.get("suggested_change") == "choose_instrumental_bgm"
                for target in packet["revision_targets"]
            ))

    def test_cli_writes_all_artifacts(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            brief = run / "video_intent.json"
            brief.write_text(
                json.dumps(
                    {
                        "video_type": "training recap",
                        "target_length": "5 minutes",
                        "style_direction": "warm story then energetic MV",
                        "speech_critical": ["director speech"],
                    }
                ),
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/soundtrack_arranger.py",
                    "--input",
                    str(brief),
                    "--out-dir",
                    str(run),
                    "--json",
                ],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            for name in [
                "soundtrack_plan.json",
                "music_source_candidates.json",
                "sound_license_manifest.json",
                "audio_director_handoff.json",
            ]:
                self.assertTrue((run / name).is_file(), name)
            payload = json.loads((run / "audio_director_handoff.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["handoff_to"], "audio-director")

    def test_video_tools_command_writes_soundtrack_artifacts(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            brief = run / "brief.json"
            brief.write_text(
                json.dumps({"request": "training recap with warm voiceover then energetic MV song"}),
                encoding="utf-8-sig",
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "soundtrack-arrange",
                    str(brief),
                    "--out-dir",
                    str(run),
                ],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((run / "soundtrack_plan.json").is_file())


if __name__ == "__main__":
    unittest.main()
