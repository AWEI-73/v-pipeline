import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class SoundtrackFlowAcceptanceTest(unittest.TestCase):
    def test_no_render_flow_reaches_audio_mix_plan_ready(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            intent = run / "video_intent.json"
            intent.write_text(
                json.dumps(
                    {
                        "artifact_role": "video_intent",
                        "video_type": "training graduation recap",
                        "target_length": "5 minutes",
                        "style_direction": "warm story then energetic MV song",
                        "audience": "students, instructors, family",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/soundtrack_flow_acceptance.py",
                    "--input",
                    str(intent),
                    "--out-dir",
                    str(run),
                    "--selected-section-id",
                    "mv_climax",
                    "--source-type",
                    "youtube_audio_library",
                    "--license-note",
                    "user confirmed internal classroom use",
                    "--fake-reviewed-audio",
                    "--json",
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            summary = json.loads(proc.stdout)
            self.assertTrue(summary["ok"])
            self.assertFalse(summary["rendered"])
            self.assertEqual(summary["pipeline_home"]["cursor"], "audio_mix")
            self.assertEqual(summary["pipeline_home"]["next"], "mix_audio_from_audio_mix_plan")

            for name in [
                "soundtrack_plan.json",
                "music_source_candidates.json",
                "sound_license_manifest.json",
                "audio_director_handoff.json",
                "audio_handoff_acceptance.json",
                "audio_mix_plan.json",
                "soundtrack_flow_acceptance_report.json",
            ]:
                self.assertTrue((run / name).is_file(), name)

            mix_plan = json.loads((run / "audio_mix_plan.json").read_text(encoding="utf-8"))
            self.assertTrue(mix_plan["ready_for_mix"])
            self.assertFalse(mix_plan["rendered"])
            self.assertEqual(mix_plan["tracks"][0]["section_id"], "mv_climax")

    def test_no_render_flow_accepts_existing_reviewed_audio_file(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            intent = run / "video_intent.json"
            intent.write_text(
                json.dumps(
                    {
                        "artifact_role": "video_intent",
                        "video_type": "training graduation recap",
                        "target_length": "3 minutes",
                        "style_direction": "warm opening then montage song",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            reviewed_audio = run / "reviewed_song.mp3"
            reviewed_audio.write_bytes(b"ID3 reviewed audio from provider")
            probe = run / "soundtrack_probe_report.json"
            probe.write_text(
                json.dumps(
                    {
                        "artifact_role": "soundtrack_probe_report",
                        "version": 1,
                        "pass": True,
                        "audio_file": str(reviewed_audio),
                        "duration_sec": 30.0,
                        "features": {"mean_dbfs": -18.0, "peak_dbfs": -3.0},
                        "sections": [{"start_sec": 0.0, "end_sec": 30.0, "role": "full_track"}],
                        "editing_fit": {"montage": "medium"},
                        "section_fit": [{"video_section": "hotblooded_montage", "fit": "medium"}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/soundtrack_flow_acceptance.py",
                    "--input",
                    str(intent),
                    "--out-dir",
                    str(run),
                    "--selected-section-id",
                    "mv_climax",
                    "--source-type",
                    "jamendo_song",
                    "--license-note",
                    "Jamendo metadata reviewed for this acceptance test",
                    "--selected-audio-file",
                    str(reviewed_audio),
                    "--soundtrack-probe-report",
                    str(probe),
                    "--json",
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            summary = json.loads(proc.stdout)
            self.assertTrue(summary["ok"])
            self.assertFalse(summary["rendered"])
            mix_plan = json.loads((run / "audio_mix_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(mix_plan["tracks"][0]["audio_file"], str(reviewed_audio))
            self.assertEqual(mix_plan["tracks"][0]["source_type"], "jamendo_song")
            self.assertTrue(mix_plan["sections"])
            self.assertEqual(mix_plan["sections"][0]["start_sec"], 0.0)
            self.assertTrue(any(
                section["section_id"] == "mv_climax" and section["duration_sec"] > 0
                for section in mix_plan["sections"]
            ))

    def test_relative_out_dir_fake_audio_uses_resolvable_audio_path(self):
        repo = Path(__file__).resolve().parents[1]
        run = Path("runs") / "_tmp_soundtrack_relative_acceptance"
        if (repo / run).exists():
            import shutil
            shutil.rmtree(repo / run)
        try:
            (repo / run).mkdir(parents=True)
            intent = repo / run / "video_intent.json"
            intent.write_text(
                json.dumps(
                    {
                        "artifact_role": "video_intent",
                        "video_type": "training graduation recap",
                        "target_length": "90 seconds",
                        "soundtrack_contract": {
                            "music_role": "mixed",
                            "handoff_to": "soundtrack-arranger",
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/soundtrack_flow_acceptance.py",
                    "--input",
                    str(run / "video_intent.json"),
                    "--out-dir",
                    str(run),
                    "--selected-section-id",
                    "mv_climax",
                    "--source-type",
                    "youtube_audio_library",
                    "--license-note",
                    "reviewed internal-use test source",
                    "--fake-reviewed-audio",
                    "--json",
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            summary = json.loads(proc.stdout)
            self.assertTrue(summary["ok"], summary)
            mix_plan = json.loads((repo / run / "audio_mix_plan.json").read_text(encoding="utf-8"))
            audio_file = Path(mix_plan["tracks"][0]["audio_file"])
            self.assertTrue(audio_file.is_absolute())
            self.assertTrue(audio_file.is_file())
        finally:
            if (repo / run).exists():
                import shutil
                shutil.rmtree(repo / run)

    def test_blocks_without_selected_audio(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            intent = run / "video_intent.json"
            intent.write_text(
                json.dumps(
                    {
                        "artifact_role": "video_intent",
                        "video_type": "training graduation recap",
                        "target_length": "2 minutes",
                        "style_direction": "warm story",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/soundtrack_flow_acceptance.py",
                    "--input",
                    str(intent),
                    "--out-dir",
                    str(run),
                    "--json",
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            summary = json.loads(proc.stdout)
            self.assertFalse(summary["ok"])
            self.assertEqual(summary["failed_stage"], "audio_handoff_acceptance")
            self.assertEqual(summary["pipeline_home"]["cursor"], "audio_handoff_acceptance")
            self.assertEqual(summary["pipeline_home"]["next"], "repair_audio_handoff")


if __name__ == "__main__":
    unittest.main()
