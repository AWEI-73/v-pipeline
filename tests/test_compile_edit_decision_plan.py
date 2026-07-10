import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.edit_decision_plan import compile_edit_decision_plan


def _write_json(root: Path, name: str, payload: dict) -> Path:
    path = root / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


class CompileEditDecisionPlanTest(unittest.TestCase):
    def test_compiles_rough_cut_and_branch_handoffs_into_product_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_json(root, "video_intent.json", {
                "video_type": "training recap",
                "goal": "60-90 second highlight",
            })
            _write_json(root, "rough_cut_plan.json", {
                "artifact_role": "rough_cut_plan",
                "ok": True,
                "clips": [
                    {
                        "segment": 1,
                        "source_path": "materials/a.mp4",
                        "start_sec": 2.0,
                        "duration_sec": 4.0,
                        "need_id": "need_opening",
                        "scene_id": "clip-a:0",
                        "reason": "opening cohort",
                    }
                ],
                "gaps": [],
            })
            _write_json(root, "audio_director_handoff.json", {
                "artifact_role": "audio_director_handoff",
                "ready_for_audio_director": True,
                "selected_audio_files": [
                    {
                        "section_id": "mv_climax",
                        "audio_file": "audio/song.mp3",
                        "source_type": "youtube_audio_library",
                        "license_note": "internal use confirmed",
                        "music_role": "energetic_mv",
                        "vocal_policy": "instrumental_preferred",
                    }
                ],
                "speech_preservation": "duck_required",
            })
            _write_json(root, "effect_handoff.json", {
                "artifact_role": "effect_handoff",
                "status": "ready_for_human_review",
                "accepted_assets": [
                    {
                        "effect_id": "fx_opening",
                        "rendered_asset": "effects/opening.webm",
                        "duration_sec": 5,
                        "evidence_refs": ["effects/contact.jpg"],
                    }
                ],
            })
            _write_json(root, "subtitle_voiceover_build_handoff.json", {
                "artifact_role": "subtitle_voiceover_build_handoff",
                "subtitle_ready": True,
                "voiceover_ready": False,
                "language": "zh-TW",
                "subtitles": "subtitles.srt",
            })

            result = compile_edit_decision_plan(root)

            self.assertEqual(result["edit_decision_plan"]["artifact_role"], "edit_decision_plan")
            self.assertEqual(result["edit_decision_plan"]["cuts"][0]["source"], "materials/a.mp4")
            self.assertEqual(result["edit_decision_plan"]["cuts"][0]["in_seconds"], 2.0)
            self.assertEqual(result["edit_decision_plan"]["cuts"][0]["out_seconds"], 6.0)
            self.assertEqual(result["edit_decision_plan"]["audio"]["music"]["asset_id"], "audio/song.mp3")
            self.assertEqual(result["edit_decision_plan"]["effects"][0]["asset_id"], "effects/opening.webm")
            self.assertTrue(result["edit_decision_plan"]["subtitles"]["enabled"])
            self.assertEqual(result["audio_decision_plan"]["source_audio_policy"], "duck_required")
            self.assertEqual(result["effect_decision_plan"]["effects"][0]["effect_id"], "fx_opening")
            self.assertEqual(result["subtitle_voiceover_decision_plan"]["language"], "zh-TW")
            self.assertEqual(result["build_handoff"]["accepted_handoffs"]["audio"], "audio_director_handoff.json")

    def test_missing_side_branches_are_deferred_not_invented(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_json(root, "rough_cut_plan.json", {
                "artifact_role": "rough_cut_plan",
                "ok": True,
                "clips": [],
                "gaps": [],
            })

            result = compile_edit_decision_plan(root)

            deferred = {item["owner"] for item in result["build_handoff"]["deferred_items"]}
            self.assertIn("soundtrack-arranger", deferred)
            self.assertIn("effect-factory", deferred)
            self.assertIn("subtitle-voiceover", deferred)
            self.assertEqual(result["edit_decision_plan"]["audio"], {})
            self.assertEqual(result["edit_decision_plan"]["effects"], [])

    def test_carries_accepted_opening_graphics_and_generated_poetry_card(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            overlay = {
                "id": "opening_title",
                "kind": "text",
                "text": {"main": "TITLE", "subtitle": "SUBTITLE"},
                "treatment": "progressive_typewriter",
                "start_sec": 0.0,
                "end_sec": 11.0,
            }
            transition = {"type": "hard_cut", "at_sec": 11.0}
            _write_json(root, "opening_sequence.json", {
                "artifact_role": "opening_sequence",
                "settings": {"fps": 30, "resolution": "1920x1080"},
                "clips": [
                    {
                        "id": "opening_photo",
                        "source": "assets/photo.jpg",
                        "start_sec": 0.0,
                        "duration_sec": 11.0,
                        "lineage": {"asset_id": "accepted_photo", "accepted": True},
                    },
                    {
                        "id": "poetry_card",
                        "source_type": "generated_background",
                        "generated_background": {"color": "black"},
                        "start_sec": 0.0,
                        "duration_sec": 7.0,
                        "lineage": {"generated": True, "reason": "poetry_card"},
                    },
                ],
                "overlays": [overlay],
                "transitions": [transition],
            })

            result = compile_edit_decision_plan(root)["edit_decision_plan"]

            self.assertEqual(result["overlays"], [overlay])
            self.assertEqual(result["transitions"], [transition])
            self.assertEqual(result.get("settings"), {"fps": 30, "resolution": "1920x1080"})
            self.assertEqual(result["cuts"][1]["generated_background"], {"color": "black"})
            self.assertEqual(result["cuts"][0]["lineage"]["asset_id"], "accepted_photo")

    def test_cli_writes_product_artifacts_without_rendering(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_json(root, "rough_cut_plan.json", {
                "artifact_role": "rough_cut_plan",
                "ok": True,
                "clips": [
                    {"source_path": "one.mp4", "start_sec": 0, "duration_sec": 3}
                ],
                "gaps": [],
            })

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/compile_edit_decision_plan.py",
                    "--run",
                    str(root),
                    "--json",
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["ok"])
            self.assertFalse((root / "final.mp4").exists())
            for name in [
                "edit_decision_plan.json",
                "audio_decision_plan.json",
                "effect_decision_plan.json",
                "subtitle_voiceover_decision_plan.json",
                "build_handoff.json",
            ]:
                self.assertTrue((root / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
