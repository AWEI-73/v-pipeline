import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import light_effects


class LightEffectsTest(unittest.TestCase):
    def _contract(self):
        return {
            "segments": [
                {
                    "segment": 1,
                    "core": {"section_role": "opening", "story_purpose": "open"},
                    "material_fit": {"visual_desc": "city opening", "media": "photo"},
                    "visual_style": {
                        "layout": "single",
                        "pace": "hold",
                        "grade": "warm",
                        "reason": "warm opening tone",
                    },
                    "text_layer": {
                        "label": "Opening",
                        "reason": "anchor the chapter",
                    },
                },
                {
                    "segment": 2,
                    "core": {"section_role": "montage", "story_purpose": "show work"},
                    "material_fit": {"visual_desc": "team work", "media": "video"},
                    "visual_style": {
                        "layout": "montage",
                        "pace": "fast",
                        "transition": "xfade",
                        "reason": "energy",
                    },
                    "text_layer": "none",
                },
            ]
        }

    def test_no_effects_profile_produces_empty_plan(self):
        plan = light_effects.build_light_effects_plan(
            self._contract(),
            {"render_profile": "no_effects", "effects_enabled": False},
        )
        self.assertEqual(plan["artifact_role"], "light_effects_plan")
        self.assertEqual(plan["items"], [])
        self.assertEqual(plan["status"], "skipped")

    def test_light_effects_profile_maps_contract_to_safe_operations(self):
        plan = light_effects.build_light_effects_plan(
            self._contract(),
            {"render_profile": "light_effects", "effects_enabled": True},
        )
        operation_types = [item["operation"] for item in plan["items"]]
        self.assertIn("grade", operation_types)
        self.assertIn("kenburns", operation_types)
        self.assertIn("title_card", operation_types)
        self.assertIn("xfade", operation_types)
        self.assertEqual(plan["items"][0]["backend"], "ffmpeg")
        self.assertEqual(plan["status"], "planned")

    def test_write_light_effects_artifacts(self):
        with tempfile.TemporaryDirectory() as d:
            result = light_effects.write_light_effects_artifacts(
                self._contract(),
                {"render_profile": "light_effects", "effects_enabled": True},
                d,
            )
            plan = json.loads(Path(result["plan"]).read_text(encoding="utf-8"))
            manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))

        self.assertTrue(result["ok"])
        self.assertEqual(plan["artifact_role"], "light_effects_plan")
        self.assertEqual(manifest["artifact_role"], "light_effects_manifest")
        self.assertEqual(manifest["light_effects_plan"], result["plan"])

    def test_baseline_review_exposes_plan_only_effect_gaps(self):
        plan = light_effects.build_light_effects_plan(
            self._contract(),
            {"render_profile": "light_effects", "effects_enabled": True},
        )
        review = light_effects.build_light_effects_baseline_review(
            plan,
            {"render_outputs": []},
            final_video="final.mp4",
            audit_paths={"keyframe_grid": "keyframe_grid.jpg"},
        )

        self.assertEqual(review["artifact_role"], "light_effects_baseline_review")
        self.assertEqual(review["status"], "gaps_found")
        self.assertEqual(review["metrics"]["planned_count"], len(plan["items"]))
        self.assertEqual(review["metrics"]["rendered_count"], 0)
        self.assertEqual(review["metrics"]["coverage_ratio"], 0.0)
        self.assertTrue(all(gap["reason"] == "no_render_output" for gap in review["gaps"]))
        self.assertTrue(review["evidence"]["final_video_present"])
        self.assertTrue(review["evidence"]["keyframe_review_ready"])

    def test_baseline_review_passes_when_all_effects_have_render_outputs_and_evidence(self):
        plan = {
            "items": [
                {"id": "seg1_grade_1", "segment": 1, "operation": "grade"},
                {"id": "seg1_title_card_2", "segment": 1, "operation": "title_card"},
            ],
        }
        manifest = {
            "render_outputs": [
                {"effect_id": "seg1_grade_1", "status": "rendered", "path": "grade.mp4"},
                {"effect_id": "seg1_title_card_2", "status": "rendered", "path": "title.ass"},
            ],
        }
        review = light_effects.build_light_effects_baseline_review(
            plan,
            manifest,
            final_video="final.mp4",
            audit_paths={"keyframe_grid": "grid.jpg", "visual_audit": "visual_audit.json"},
        )

        self.assertEqual(review["status"], "pass")
        self.assertEqual(review["metrics"]["coverage_ratio"], 1.0)
        self.assertEqual(review["gaps"], [])

    def test_motion_graphics_outputs_resolve_matching_text_effect_gaps(self):
        contract = self._contract()
        contract["segments"][1]["text_layer"] = {
            "label": "Grinding",
            "reason": "mark the process chapter",
        }
        plan = light_effects.build_light_effects_plan(
            contract,
            {"render_profile": "light_effects", "effects_enabled": True},
        )
        manifest = {"render_outputs": []}
        motion_outputs = [
            {"effect_id": "seg1_title_sequence", "segment": 1,
             "effect_type": "title_sequence", "status": "composited", "path": "title.ass"},
            {"effect_id": "seg2_chapter_card", "segment": 2,
             "effect_type": "chapter_card", "status": "composited", "path": "label.ass"},
        ]

        light_effects.record_motion_graphics_outputs(plan, manifest, motion_outputs)
        review = light_effects.build_light_effects_baseline_review(plan, manifest)

        self.assertEqual(review["metrics"]["rendered_count"], 2)
        self.assertEqual(review["metrics"]["gap_count"], len(plan["items"]) - 2)
        rendered_ops = {item["operation"] for item in manifest["render_outputs"]}
        self.assertEqual(rendered_ops, {"title_card"})

    def test_plan_does_not_mislabel_hold_video_or_direct_cut_as_effects(self):
        contract = {
            "segments": [{
                "segment": 1,
                "visual_style": {"pace": "hold", "transition": "direct_cut"},
                "material_fit": {"media": "video"},
            }, {
                "segment": 2,
                "visual_style": {"pace": "fast", "layout": "montage", "transition": "beat_cut"},
                "material_fit": {"media": "video"},
            }],
        }

        plan = light_effects.build_light_effects_plan(
            contract,
            {"render_profile": "light_effects", "effects_enabled": True},
        )

        self.assertEqual(plan["items"], [])

    def test_mv_photo_render_output_resolves_matching_kenburns_gap(self):
        contract = {
            "segments": [{
                "segment": 1,
                "visual_style": {"motion": "zoom-in"},
                "material_fit": {"media": "photo"},
            }],
        }
        plan = light_effects.build_light_effects_plan(
            contract,
            {"render_profile": "light_effects", "effects_enabled": True},
        )
        manifest = {"render_outputs": []}

        light_effects.record_mv_render_outputs(
            plan,
            manifest,
            [{"segment": 1, "is_photo": True, "kenburns": True, "slot_index": 0}],
            final_video="final.mp4",
        )

        self.assertEqual(manifest["render_outputs"], [{
            "effect_id": "seg1_kenburns_1",
            "segment": 1,
            "operation": "kenburns",
            "status": "rendered",
            "path": "final.mp4",
            "renderer": "mv_cut.photo_zoompan",
            "source_slot_index": 0,
        }])

    def test_mv_xfade_render_output_resolves_explicit_transition_gap(self):
        contract = {
            "segments": [{
                "segment": 1,
                "visual_style": {"transition": "direct_cut"},
                "material_fit": {"media": "video"},
            }, {
                "segment": 2,
                "visual_style": {"transition": "xfade"},
                "material_fit": {"media": "video"},
            }],
        }
        plan = light_effects.build_light_effects_plan(
            contract,
            {"render_profile": "light_effects", "effects_enabled": True},
        )
        manifest = {"render_outputs": []}

        light_effects.record_mv_render_outputs(
            plan,
            manifest,
            [
                {"segment": 1, "slot_index": 0},
                {"segment": 2, "slot_index": 1, "transition": "xfade", "transition_duration": 0.5},
            ],
            final_video="final.mp4",
        )

        self.assertEqual(manifest["render_outputs"][0]["operation"], "xfade")
        self.assertEqual(manifest["render_outputs"][0]["renderer"], "mv_cut.ffmpeg_xfade")
        self.assertEqual(manifest["render_outputs"][0]["transition_duration"], 0.5)

    def test_video_tools_light_effects_plan_cli(self):
        with tempfile.TemporaryDirectory() as d:
            workdir = Path(d)
            contract_path = workdir / "segment_contract.json"
            profile_path = workdir / "build_profile.json"
            out_dir = workdir / "build"
            contract_path.write_text(json.dumps(self._contract()), encoding="utf-8")
            profile_path.write_text(json.dumps({
                "render_profile": "light_effects",
                "effects_enabled": True,
            }), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "light-effects-plan",
                    str(contract_path),
                    "--build-profile",
                    str(profile_path),
                    "--out-dir",
                    str(out_dir),
                ],
                cwd=Path(__file__).resolve().parent.parent,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads((out_dir / "light_effects_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["artifact_role"], "light_effects_plan")
            self.assertEqual(plan["status"], "planned")


if __name__ == "__main__":
    unittest.main()
