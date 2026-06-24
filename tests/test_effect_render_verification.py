import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import video_tools


class EffectRenderVerificationTest(unittest.TestCase):
    def _effect_plan(self):
        return {
            "artifact_role": "effect_intent_plan",
            "version": 1,
            "effects": [
                {
                    "effect_id": "fx_memory_wall_01",
                    "role": "title_card",
                    "template_id": "memory_photo_wall",
                    "required_for_story": True,
                },
                {
                    "effect_id": "fx_story_to_mv_01",
                    "role": "chapter_transition",
                    "template_id": "film_strip_transition_card",
                    "required_for_story": True,
                },
            ],
        }

    def _accepted_review(self, root):
        sheet = root / "contact_sheet.jpg"
        keyframe = root / "keyframe_1s.jpg"
        preview = root / "preview.mp4"
        rendered = root / "rendered.mov"
        for path in (sheet, keyframe, preview, rendered):
            path.write_bytes(path.name.encode("utf-8"))
        return {
            "artifact_role": "remotion_effect_review",
            "version": 1,
            "status": "accepted",
            "items": [
                {
                    "job_id": "rm_fx_memory_wall_01",
                    "source_effect_id": "fx_memory_wall_01",
                    "status": "accepted",
                    "role": "title_card",
                    "preview_file": str(preview),
                    "rendered_asset": str(rendered),
                    "evidence_refs": [str(sheet), str(keyframe)],
                },
                {
                    "job_id": "rm_fx_story_to_mv_01",
                    "source_effect_id": "fx_story_to_mv_01",
                    "status": "accepted",
                    "role": "chapter_transition",
                    "preview_file": str(preview),
                    "rendered_asset": str(rendered),
                    "evidence_refs": [str(sheet)],
                },
            ],
        }

    def test_builds_delivery_gate_effect_render_verification_from_accepted_review(self):
        from video_pipeline_core.effect_render_verification import build_effect_render_verification

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            verification = build_effect_render_verification(
                self._effect_plan(),
                self._accepted_review(root),
                root=root,
            )

        self.assertEqual(verification["artifact_role"], "effect_render_verification")
        self.assertTrue(verification["pass"], verification)
        self.assertEqual(verification["summary"]["planned_count"], 2)
        self.assertEqual(verification["summary"]["rendered_count"], 2)
        self.assertEqual(verification["verified_effects"][0]["effect_id"], "fx_memory_wall_01")
        self.assertTrue(verification["verified_effects"][0]["rendered"])
        self.assertTrue(verification["verified_effects"][0]["evidence_refs"])

    def test_marks_missing_or_unaccepted_effects_as_not_rendered(self):
        from video_pipeline_core.effect_render_verification import build_effect_render_verification

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            review = self._accepted_review(root)
            review["items"] = review["items"][:1]

            verification = build_effect_render_verification(
                self._effect_plan(),
                review,
                root=root,
            )

        self.assertFalse(verification["pass"])
        missing = verification["verified_effects"][1]
        self.assertEqual(missing["effect_id"], "fx_story_to_mv_01")
        self.assertFalse(missing["rendered"])
        self.assertEqual(missing["reason"], "missing_accepted_remotion_review_item")

    def test_cli_writes_effect_render_verification_json(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = root / "effect_intent_plan.json"
            review = root / "remotion_effect_review.json"
            out = root / "effect_render_verification.json"
            plan.write_text(json.dumps(self._effect_plan()), encoding="utf-8")
            review.write_text(json.dumps(self._accepted_review(root)), encoding="utf-8")

            video_tools.cmd_effect_render_verification(SimpleNamespace(
                effect_intent_plan=str(plan),
                remotion_review=str(review),
                out=str(out),
                root=str(root),
            ))
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertTrue(payload["pass"])
        self.assertEqual(payload["summary"]["rendered_count"], 2)

    def test_video_tools_effect_render_verification_subcommand(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = root / "effect_intent_plan.json"
            review = root / "remotion_effect_review.json"
            out = root / "effect_render_verification.json"
            plan.write_text(json.dumps(self._effect_plan()), encoding="utf-8")
            review.write_text(json.dumps(self._accepted_review(root)), encoding="utf-8")

            proc = subprocess.run([
                sys.executable,
                "video_tools.py",
                "effect-render-verification",
                "--effect-intent-plan", str(plan),
                "--remotion-review", str(review),
                "--out", str(out),
                "--root", str(root),
            ], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(out.is_file())


if __name__ == "__main__":
    unittest.main()
