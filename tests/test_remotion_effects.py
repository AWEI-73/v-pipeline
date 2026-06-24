import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.tool_command_catalog import build_command_manifest, build_workflow_manifest


def _effect_revision_request():
    return {
        "artifact_role": "effect_revision_request",
        "version": 1,
        "status": "pending",
        "summary": {"request_count": 2},
        "requests": [{
            "request_id": "fxrev_page",
            "effect_id": "fxintent_2_external_effect_1",
            "source_effect_id": "fx_page_turn",
            "segment": 2,
            "operation": "external_effect",
            "route": "route_to_node14_or_remotion_adapter",
            "reason": "remotion-only page turn did not render",
            "status": "pending",
        }, {
            "request_id": "fxrev_lower",
            "effect_id": "seg1_lower_third_1",
            "source_effect_id": "fx_lower",
            "segment": 1,
            "operation": "lower_third",
            "route": "implement_or_wire_effect_recipe",
            "reason": "missing ffmpeg lower third recipe",
            "status": "pending",
        }],
    }


def _effect_intent_plan():
    return {
        "artifact_role": "effect_intent_plan",
        "version": 1,
        "effects": [{
            "effect_id": "fx_page_turn",
            "role": "chapter_transition",
            "intent": "像實習報告翻頁進入下一段訓練回憶",
            "intensity": "medium",
            "target": {"beat_id": "b02", "segment_id": "2"},
            "visual_language": ["paper texture", "warm glow", "page turn"],
            "required_for_story": True,
            "must_preserve_proof": False,
            "allowed_backends": ["remotion_preview", "remotion_render"],
            "fallback": "simple fade",
        }, {
            "effect_id": "fx_lower",
            "role": "lower_third",
            "intent": "主任勉勵",
            "intensity": "low",
            "target": {"beat_id": "b01", "segment_id": "1"},
            "visual_language": ["clean lower third"],
            "required_for_story": False,
            "must_preserve_proof": True,
            "allowed_backends": ["ffmpeg_light_effects"],
            "fallback": "none",
        }],
    }


def _timeline():
    return {
        "clips": [
            {"segment": 1, "timeline_in_sec": 0.0, "timeline_out_sec": 2.5},
            {"segment": 2, "timeline_in_sec": 2.5, "timeline_out_sec": 6.25},
            {"segment": 2, "timeline_in_sec": 6.25, "timeline_out_sec": 7.0},
        ]
    }


class RemotionPromptPackTest(unittest.TestCase):
    def test_build_prompt_pack_only_for_remotion_adapter_requests(self):
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        pack = build_remotion_prompt_pack(
            _effect_revision_request(),
            _effect_intent_plan(),
            timeline=_timeline(),
            output_dir="effects/remotion",
        )

        self.assertEqual(pack["artifact_role"], "remotion_prompt_pack")
        self.assertEqual(pack["version"], 1)
        self.assertEqual(pack["status"], "pending")
        self.assertEqual(pack["summary"]["job_count"], 1)
        job = pack["jobs"][0]
        self.assertEqual(job["job_id"], "rm_fx_page_turn")
        self.assertEqual(job["source_effect_id"], "fx_page_turn")
        self.assertEqual(job["component_family"], "page_turn_transition")
        self.assertEqual(job["timing"], {"start_sec": 2.5, "duration_sec": 4.5})
        self.assertIn("實習報告翻頁", job["prompt"])
        self.assertEqual(job["output"]["type"], "overlay_video")
        self.assertTrue(job["output"]["alpha"])
        self.assertTrue(job["output"]["target_file"].endswith("rm_fx_page_turn.mov"))
        self.assertEqual(job["acceptance"]["must_match_duration_sec"], 4.5)
        self.assertNotIn("fx_lower", json.dumps(pack, ensure_ascii=False))

    def test_prompt_pack_uses_segment_timeline_duration_entries(self):
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        request = _effect_revision_request()
        request["requests"][0]["segment"] = "seg_opening_min"
        timeline = {
            "artifact_role": "timeline_build",
            "version": 1,
            "segments": [{
                "segment_id": "seg_opening_min",
                "start_sec": 12.0,
                "duration_sec": 4.0,
                "effect_id": "fx_page_turn",
            }],
        }

        pack = build_remotion_prompt_pack(
            request,
            _effect_intent_plan(),
            timeline=timeline,
            output_dir="effects/remotion",
        )

        job = pack["jobs"][0]
        self.assertEqual(job["timing"], {"start_sec": 12.0, "duration_sec": 4.0})
        self.assertEqual(job["acceptance"]["must_match_duration_sec"], 4.0)
        self.assertNotIn("timeline_segment_missing", json.dumps(job["diagnostics"]))

    def test_prompt_pack_adds_presentation_parameters_for_remotion_worker(self):
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        pack = build_remotion_prompt_pack(
            _effect_revision_request(),
            _effect_intent_plan(),
            timeline=_timeline(),
            output_dir="effects/remotion",
        )
        job = pack["jobs"][0]

        self.assertIn("display_text", job["props"])
        self.assertLessEqual(len(job["props"]["display_text"]), 24)
        self.assertEqual(job["props"]["presentation"]["text_position"], "bottom_left")
        self.assertEqual(job["props"]["presentation"]["text_scale"], "medium")
        self.assertEqual(job["props"]["presentation"]["effect_strength"], "medium")
        self.assertEqual(job["props"]["presentation"]["safe_area"], "lower_third")

    def test_prompt_pack_preserves_commercial_motion_presentation_parameters(self):
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        plan = _effect_intent_plan()
        plan["effects"][0].update({
            "role": "title_card",
            "template_id": "training_opening_title",
            "display_text": "67TH TRAINING",
            "presentation": {
                "variant": "cinematic_collage_reveal",
                "motion_energy": "high",
                "title_hierarchy": "hero",
                "hero_media_policy": "avoid_title_bearing",
                "thumbnail_density": "balanced",
            },
        })
        pack = build_remotion_prompt_pack(
            _effect_revision_request(),
            plan,
            timeline=_timeline(),
            output_dir="effects/remotion",
        )
        presentation = pack["jobs"][0]["props"]["presentation"]

        self.assertEqual(presentation["variant"], "cinematic_collage_reveal")
        self.assertEqual(presentation["motion_energy"], "high")
        self.assertEqual(presentation["title_hierarchy"], "hero")
        self.assertEqual(presentation["hero_media_policy"], "avoid_title_bearing")
        self.assertEqual(presentation["thumbnail_density"], "balanced")

    def test_prompt_pack_preserves_opening_prompt_parameter_contract(self):
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        plan = _effect_intent_plan()
        plan["effects"][0].update({
            "role": "title_card",
            "template_id": "training_opening_title",
            "display_text": "67TH TRAINING",
            "prompt_parameters": {
                "effect_goal": "formal_training_opening",
                "tone": ["formal", "warm", "memory_recap"],
                "material_strategy": {
                    "hero_source": "reviewed_people_group",
                    "avoid_hero_roles": ["title_card"],
                    "collage_count": 5,
                },
                "motion_grammar": [
                    "collage_depth_reveal",
                    "gold_title_sweep",
                    "slow_parallax",
                    "title_punch",
                ],
                "text_hierarchy": {
                    "primary": "program_title",
                    "secondary": "subtitle",
                },
                "negative_rules": [
                    "do_not_cover_faces",
                    "avoid_party_style_flash",
                ],
            },
        })

        pack = build_remotion_prompt_pack(
            _effect_revision_request(),
            plan,
            timeline=_timeline(),
            output_dir="effects/remotion",
        )
        params = pack["jobs"][0]["props"]["prompt_parameters"]

        self.assertEqual(params["effect_goal"], "formal_training_opening")
        self.assertEqual(params["material_strategy"]["hero_source"], "reviewed_people_group")
        self.assertIn("gold_title_sweep", params["motion_grammar"])
        self.assertIn("do_not_cover_faces", params["negative_rules"])

    def test_prompt_pack_preserves_story_to_mv_transition_prompt_parameter_contract(self):
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        plan = _effect_intent_plan()
        plan["effects"][0].update({
            "role": "chapter_transition",
            "template_id": "film_strip_transition_card",
            "display_text": "故事開始加速",
            "subtitle_text": "從故事段進入節奏蒙太奇",
            "prompt_parameters": {
                "effect_goal": "story_half_to_mv_half_transition",
                "transition_strength": "impact",
                "phase_labels": ["STORY", "MONTAGE"],
                "cut_point": "midpoint_impact",
                "material_strategy": {
                    "thumbnail_source": "reviewed_stills",
                    "thumbnail_density": "balanced",
                    "reject_low_information_refs": True,
                },
                "motion_grammar": [
                    "film_rail",
                    "thumbnail_acceleration",
                    "flash_wipe",
                    "hard_cut_bars",
                ],
                "negative_rules": [
                    "do_not_read_as_static_chapter_card",
                    "do_not_obscure_proof_footage",
                ],
            },
        })

        pack = build_remotion_prompt_pack(
            _effect_revision_request(),
            plan,
            timeline=_timeline(),
            output_dir="effects/remotion",
        )
        params = pack["jobs"][0]["props"]["prompt_parameters"]

        self.assertEqual(params["transition_strength"], "impact")
        self.assertEqual(params["cut_point"], "midpoint_impact")
        self.assertTrue(params["material_strategy"]["reject_low_information_refs"])
        self.assertIn("thumbnail_acceleration", params["motion_grammar"])

    def test_prompt_pack_preserves_memory_photo_wall_build_spec_contract(self):
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        plan = _effect_intent_plan()
        build_spec = {
            "component": "MemoryPhotoWall",
            "duration_sec": 8,
            "story_function": "emotional_setup",
            "pacing": "slow",
            "density": "low",
            "reveal_mode": "one_by_one",
            "reveal_interval_sec": 1.2,
            "hold_after_full_wall_sec": 2.0,
            "camera_motion": "slow_push_in",
            "caption_mode": "minimal",
            "accent_light": "soft_warm",
        }
        plan["effects"][0].update({
            "role": "title_card",
            "template_id": "memory_photo_wall",
            "display_text": "Training Memory",
            "prompt_parameters": {
                "effect_goal": "brownfield_memory_photo_wall",
                "effect_build_spec": build_spec,
            },
            "collage_media_refs": [
                {"ref_id": "group_photo", "path": "frames/group.jpg", "label": "group"},
                {"ref_id": "training_photo", "path": "frames/training.jpg", "label": "training"},
            ],
        })

        pack = build_remotion_prompt_pack(
            _effect_revision_request(),
            plan,
            timeline=_timeline(),
            output_dir="effects/remotion",
        )
        job = pack["jobs"][0]
        params = job["props"]["prompt_parameters"]

        self.assertEqual(job["props"]["template_id"], "memory_photo_wall")
        self.assertEqual(params["effect_build_spec"]["component"], "MemoryPhotoWall")
        self.assertEqual(params["effect_build_spec"]["duration_sec"], 8)
        self.assertEqual(params["effect_build_spec"]["reveal_mode"], "one_by_one")
        self.assertIn("effect_build_spec:MemoryPhotoWall", job["diagnostics"])
        self.assertIn("MemoryPhotoWall", job["prompt"])

    def test_prompt_pack_preserves_story_to_mv_transition_build_spec_contract(self):
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        plan = _effect_intent_plan()
        build_spec = {
            "component": "StoryToMVTransition",
            "duration_sec": 4,
            "section_from": "story",
            "section_to": "montage",
            "pacing_shift": "slow_to_fast",
            "impact_moment_sec": 2.2,
            "thumbnail_acceleration": "medium",
            "motion_grammar": [
                "film_rail",
                "thumbnail_acceleration",
                "flash_wipe",
                "hard_cut_bars",
            ],
            "phase_labels": ["STORY", "MONTAGE"],
            "light_sweep": "warm",
            "film_strip_motion": "accelerating",
            "caption_mode": "phase_labels",
        }
        plan["effects"][0].update({
            "role": "chapter_transition",
            "template_id": "film_strip_transition_card",
            "display_text": "Story to montage",
            "subtitle_text": "Pacing shift",
            "prompt_parameters": {
                "effect_goal": "story_half_to_mv_half_transition",
                "effect_build_spec": build_spec,
            },
        })

        pack = build_remotion_prompt_pack(
            _effect_revision_request(),
            plan,
            timeline=_timeline(),
            output_dir="effects/remotion",
        )

        job = pack["jobs"][0]
        params = job["props"]["prompt_parameters"]

        self.assertEqual(job["props"]["template_id"], "film_strip_transition_card")
        self.assertEqual(params["effect_build_spec"], build_spec)
        self.assertIn("effect_build_spec:StoryToMVTransition", job["diagnostics"])
        self.assertIn("StoryToMVTransition", job["prompt"])

    def test_prompt_pack_applies_training_template_defaults(self):
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        plan = _effect_intent_plan()
        plan["effects"][0].update({
            "role": "title_card",
            "template_id": "training_opening_title",
            "display_text": "67TH TRAINING",
            "subtitle_text": "ON THE LAST PAGE",
            "presentation": {"text_position": "bottom_center"},
        })
        pack = build_remotion_prompt_pack(
            _effect_revision_request(),
            plan,
            timeline=_timeline(),
            output_dir="effects/remotion",
        )
        job = pack["jobs"][0]

        self.assertEqual(job["component_family"], "title_reveal")
        self.assertEqual(job["props"]["template_id"], "training_opening_title")
        self.assertEqual(job["props"]["subtitle_text"], "ON THE LAST PAGE")
        self.assertEqual(job["props"]["presentation"]["background_style"], "black_collage")
        self.assertEqual(job["props"]["presentation"]["theme"], "training_recap_67")
        self.assertEqual(job["props"]["presentation"]["text_scale"], "hero")
        self.assertEqual(job["props"]["presentation"]["accent_color"], "#ffe100")
        self.assertEqual(job["props"]["presentation"]["text_position"], "bottom_center")

    def test_prompt_pack_carries_training_collage_media_refs(self):
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        plan = _effect_intent_plan()
        plan["effects"][0].update({
            "role": "title_card",
            "template_id": "training_opening_title",
            "display_text": "67TH TRAINING",
            "collage_media_refs": [
                {"ref_id": "opening_01", "path": "frames/opening_01.jpg", "label": "集合"},
                {"ref_id": "training_01", "path": "frames/training_01.jpg", "label": "訓練"},
            ],
        })
        pack = build_remotion_prompt_pack(
            _effect_revision_request(),
            plan,
            timeline=_timeline(),
            output_dir="effects/remotion",
        )
        job = pack["jobs"][0]

        self.assertEqual(job["props"]["collage_media_refs"][0]["path"], "frames/opening_01.jpg")
        self.assertEqual(job["props"]["collage_media_refs"][1]["label"], "訓練")
        self.assertIn("collage media refs: 2", job["prompt"])

    def test_prompt_pack_preserves_collage_review_metadata_for_hero_policy(self):
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        plan = _effect_intent_plan()
        plan["effects"][0].update({
            "role": "title_card",
            "template_id": "training_opening_title",
            "display_text": "67TH TRAINING",
            "collage_media_refs": [
                {
                    "ref_id": "opening_title",
                    "path": "frames/opening_title.jpg",
                    "label": "opening title plate",
                    "contains_title": True,
                    "visual_role": "title_card",
                },
                {
                    "ref_id": "group_photo",
                    "path": "frames/group_photo.jpg",
                    "label": "group photo",
                    "contains_title": False,
                    "visual_role": "people_group",
                },
            ],
        })
        pack = build_remotion_prompt_pack(
            _effect_revision_request(),
            plan,
            timeline=_timeline(),
            output_dir="effects/remotion",
        )
        refs = pack["jobs"][0]["props"]["collage_media_refs"]

        self.assertTrue(refs[0]["contains_title"])
        self.assertEqual(refs[0]["visual_role"], "title_card")
        self.assertFalse(refs[1]["contains_title"])
        self.assertEqual(refs[1]["visual_role"], "people_group")

    def test_prompt_pack_injects_collage_refs_artifact_for_training_opening_template(self):
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        plan = _effect_intent_plan()
        plan["effects"][0].update({
            "role": "title_card",
            "template_id": "training_opening_title",
            "display_text": "67TH TRAINING",
        })
        collage_refs = {
            "artifact_role": "effect_collage_media_refs",
            "version": 1,
            "ok": True,
            "collage_media_refs": [
                {"ref_id": "opening_01", "path": "file:///C:/reviewed/opening.jpg", "label": "opening"}
            ],
        }
        pack = build_remotion_prompt_pack(
            _effect_revision_request(),
            plan,
            timeline=_timeline(),
            output_dir="effects/remotion",
            collage_media_refs=collage_refs,
        )
        job = pack["jobs"][0]

        self.assertEqual(job["props"]["collage_media_refs"][0]["ref_id"], "opening_01")
        self.assertEqual(job["props"]["collage_media_refs"][0]["path"], "file:///C:/reviewed/opening.jpg")
        self.assertEqual(job["diagnostics"], [])

    def test_prompt_pack_keeps_explicit_effect_refs_over_collage_refs_artifact(self):
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        plan = _effect_intent_plan()
        plan["effects"][0].update({
            "role": "title_card",
            "template_id": "training_opening_title",
            "display_text": "67TH TRAINING",
            "collage_media_refs": [
                {"ref_id": "explicit", "path": "file:///C:/explicit.jpg", "label": "explicit"}
            ],
        })
        pack = build_remotion_prompt_pack(
            _effect_revision_request(),
            plan,
            timeline=_timeline(),
            collage_media_refs={
                "artifact_role": "effect_collage_media_refs",
                "version": 1,
                "ok": True,
                "collage_media_refs": [
                    {"ref_id": "artifact", "path": "file:///C:/artifact.jpg", "label": "artifact"}
                ],
            },
        )

        self.assertEqual(pack["jobs"][0]["props"]["collage_media_refs"][0]["ref_id"], "explicit")

    def test_prompt_pack_cli_accepts_collage_refs_artifact(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request = root / "effect_revision_request.json"
            plan_path = root / "effect_intent_plan.json"
            timeline = root / "timeline_build.json"
            collage_refs = root / "effect_collage_media_refs.json"
            out = root / "remotion_prompt_pack.json"
            plan = _effect_intent_plan()
            plan["effects"][0].update({
                "role": "title_card",
                "template_id": "training_opening_title",
                "display_text": "67TH TRAINING",
            })
            request.write_text(json.dumps(_effect_revision_request()), encoding="utf-8")
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            timeline.write_text(json.dumps(_timeline()), encoding="utf-8")
            collage_refs.write_text(json.dumps({
                "artifact_role": "effect_collage_media_refs",
                "version": 1,
                "ok": True,
                "collage_media_refs": [
                    {"ref_id": "opening_01", "path": "file:///C:/reviewed/opening.jpg", "label": "opening"}
                ],
            }), encoding="utf-8")

            proc = subprocess.run([
                sys.executable,
                "video_tools.py",
                "remotion-prompt-pack",
                "--request", str(request),
                "--effect-intent-plan", str(plan_path),
                "--timeline", str(timeline),
                "--collage-refs", str(collage_refs),
                "--out", str(out),
            ], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            written = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(
                written["jobs"][0]["props"]["collage_media_refs"][0]["ref_id"],
                "opening_01",
            )

    def test_prompt_pack_applies_speaker_yellow_bar_template_defaults(self):
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        plan = _effect_intent_plan()
        plan["effects"][0].update({
            "role": "lower_third",
            "template_id": "speaker_subtitle_yellow_bar",
            "display_text": "主任：保持初心，繼續前進。",
            "speaker_name": "主任",
        })
        pack = build_remotion_prompt_pack(
            _effect_revision_request(),
            plan,
            timeline=_timeline(),
            output_dir="effects/remotion",
        )
        job = pack["jobs"][0]

        self.assertEqual(job["component_family"], "lower_third_motion")
        self.assertEqual(job["props"]["template_id"], "speaker_subtitle_yellow_bar")
        self.assertEqual(job["props"]["speaker_name"], "主任")
        self.assertEqual(job["props"]["presentation"]["background_style"], "yellow_subtitle_bar")
        self.assertEqual(job["props"]["presentation"]["text_position"], "bottom_center")
        self.assertEqual(job["props"]["presentation"]["safe_area"], "subtitle_safe")

    def test_prompt_pack_infers_film_strip_template_for_story_to_montage_transition(self):
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        plan = _effect_intent_plan()
        plan["effects"][0].update({
            "role": "chapter_transition",
            "template_id": None,
            "visual_language": ["story to mv", "montage", "film strip"],
            "target": {"segment_id": "2", "section_role": "montage"},
        })
        pack = build_remotion_prompt_pack(
            _effect_revision_request(),
            plan,
            timeline=_timeline(),
            output_dir="effects/remotion",
        )
        job = pack["jobs"][0]

        self.assertEqual(job["props"]["template_id"], "film_strip_transition_card")
        self.assertEqual(job["component_family"], "page_turn_transition")
        self.assertEqual(job["props"]["presentation"]["background_style"], "film_strip")
        self.assertIn("template_inferred:film_strip_transition_card", job["diagnostics"])

    def test_prompt_pack_infers_speaker_subtitle_template_for_speaker_lower_third(self):
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        plan = _effect_intent_plan()
        plan["effects"][0].update({
            "role": "lower_third",
            "display_text": "主任：保持初心。",
            "speaker_name": "主任",
            "visual_language": ["speaker remarks", "readable subtitle"],
        })
        pack = build_remotion_prompt_pack(
            _effect_revision_request(),
            plan,
            timeline=_timeline(),
            output_dir="effects/remotion",
        )
        job = pack["jobs"][0]

        self.assertEqual(job["props"]["template_id"], "speaker_subtitle_yellow_bar")
        self.assertEqual(job["component_family"], "lower_third_motion")
        self.assertEqual(job["props"]["presentation"]["background_style"], "yellow_subtitle_bar")
        self.assertIn("template_inferred:speaker_subtitle_yellow_bar", job["diagnostics"])

    def test_prompt_pack_infers_blurred_side_fill_template_for_vertical_panel_frame(self):
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        plan = _effect_intent_plan()
        plan["effects"][0].update({
            "role": "panel_frame",
            "visual_language": ["vertical footage", "side fill", "proof preserving"],
            "collage_media_refs": [
                {"ref_id": "vertical_01", "path": "frames/vertical.jpg", "label": "vertical"}
            ],
        })
        pack = build_remotion_prompt_pack(
            _effect_revision_request(),
            plan,
            timeline=_timeline(),
            output_dir="effects/remotion",
        )
        job = pack["jobs"][0]

        self.assertEqual(job["props"]["template_id"], "blurred_side_fill")
        self.assertEqual(job["component_family"], "panel_frame_motion")
        self.assertEqual(job["props"]["presentation"]["background_style"], "blurred_side_fill")
        self.assertEqual(job["props"]["collage_media_refs"][0]["ref_id"], "vertical_01")
        self.assertIn("template_inferred:blurred_side_fill", job["diagnostics"])

    def test_prompt_pack_keeps_explicit_template_over_policy_inference(self):
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        plan = _effect_intent_plan()
        plan["effects"][0].update({
            "role": "chapter_transition",
            "template_id": "soft_light_transition",
            "visual_language": ["story to mv", "film strip"],
        })
        pack = build_remotion_prompt_pack(
            _effect_revision_request(),
            plan,
            timeline=_timeline(),
            output_dir="effects/remotion",
        )
        job = pack["jobs"][0]

        self.assertEqual(job["props"]["template_id"], "soft_light_transition")
        self.assertEqual(job["component_family"], "light_leak_overlay")
        self.assertNotIn("template_inferred:film_strip_transition_card", job["diagnostics"])

    def test_prompt_pack_fails_closed_for_unknown_source_effect(self):
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        request = _effect_revision_request()
        request["requests"][0]["source_effect_id"] = "fx_missing"
        with self.assertRaises(ValueError):
            build_remotion_prompt_pack(request, _effect_intent_plan(), timeline=_timeline())

    def test_prompt_pack_does_not_require_timeline_but_marks_timing_unknown(self):
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        pack = build_remotion_prompt_pack(_effect_revision_request(), _effect_intent_plan())
        job = pack["jobs"][0]
        self.assertEqual(job["timing"]["start_sec"], 0.0)
        self.assertEqual(job["timing"]["duration_sec"], 3.0)
        self.assertTrue(job["diagnostics"])

    def test_prompt_pack_cli_writes_artifact(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request = root / "effect_revision_request.json"
            plan = root / "effect_intent_plan.json"
            timeline = root / "timeline_build.json"
            out = root / "remotion_prompt_pack.json"
            request.write_text(json.dumps(_effect_revision_request()), encoding="utf-8")
            plan.write_text(json.dumps(_effect_intent_plan()), encoding="utf-8")
            timeline.write_text(json.dumps(_timeline()), encoding="utf-8")

            proc = subprocess.run([
                sys.executable,
                "video_tools.py",
                "remotion-prompt-pack",
                "--request", str(request),
                "--effect-intent-plan", str(plan),
                "--timeline", str(timeline),
                "--out", str(out),
                "--output-dir", "fx",
            ], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            written = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(written["artifact_role"], "remotion_prompt_pack")
            self.assertEqual(written["jobs"][0]["output"]["target_file"], "fx/rm_fx_page_turn.mov")


class RemotionWorkerOutputsTest(unittest.TestCase):
    def _worker_outputs(self, root):
        preview = root / "preview.mp4"
        rendered = root / "overlay.mov"
        evidence = root / "contact_sheet.jpg"
        preview.write_bytes(b"preview")
        rendered.write_bytes(b"rendered")
        evidence.write_bytes(b"evidence")
        return {
            "artifact_role": "remotion_worker_outputs",
            "version": 1,
            "jobs": [{
                "job_id": "rm_fx_page_turn",
                "source_effect_id": "fx_page_turn",
                "status": "rendered",
                "preview_file": str(preview),
                "rendered_asset": str(rendered),
                "duration_sec": 4.5,
                "backend": "remotion",
                "evidence_refs": [str(evidence)],
            }],
        }

    def test_validate_worker_outputs_accepts_matching_rendered_job(self):
        from video_pipeline_core.remotion_effects import (
            build_remotion_prompt_pack,
            validate_remotion_worker_outputs,
        )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pack = build_remotion_prompt_pack(
                _effect_revision_request(),
                _effect_intent_plan(),
                timeline=_timeline(),
                output_dir=str(root),
            )
            result = validate_remotion_worker_outputs(self._worker_outputs(root), pack)

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["summary"]["rendered_count"], 1)
        self.assertEqual(result["review_artifact"]["status"], "pending_review")
        self.assertEqual(result["review_artifact"]["items"][0]["source_effect_id"], "fx_page_turn")

    def test_validate_worker_outputs_fails_closed_on_missing_file_or_unknown_job(self):
        from video_pipeline_core.remotion_effects import (
            build_remotion_prompt_pack,
            validate_remotion_worker_outputs,
        )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pack = build_remotion_prompt_pack(
                _effect_revision_request(),
                _effect_intent_plan(),
                timeline=_timeline(),
                output_dir=str(root),
            )
            outputs = self._worker_outputs(root)
            outputs["jobs"][0]["rendered_asset"] = str(root / "missing.mov")
            result = validate_remotion_worker_outputs(outputs, pack)
            self.assertFalse(result["ok"])
            self.assertIn("rendered_asset", result["errors"][0])

            outputs = self._worker_outputs(root)
            outputs["jobs"][0]["job_id"] = "rm_unknown"
            result = validate_remotion_worker_outputs(outputs, pack)
            self.assertFalse(result["ok"])
            self.assertIn("unknown job_id", result["errors"][0])

    def test_validate_worker_outputs_requires_review_evidence_refs(self):
        from video_pipeline_core.remotion_effects import (
            build_remotion_prompt_pack,
            validate_remotion_worker_outputs,
        )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pack = build_remotion_prompt_pack(
                _effect_revision_request(),
                _effect_intent_plan(),
                timeline=_timeline(),
                output_dir=str(root),
            )
            outputs = self._worker_outputs(root)
            outputs["jobs"][0].pop("evidence_refs")

            result = validate_remotion_worker_outputs(outputs, pack)

        self.assertFalse(result["ok"])
        self.assertIn("evidence_refs", result["errors"][0])
        self.assertEqual(result["review_artifact"]["summary"]["rendered_count"], 0)

    def test_validate_worker_outputs_cli_writes_review_artifact(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            from video_pipeline_core.remotion_effects import build_remotion_prompt_pack
            pack = build_remotion_prompt_pack(
                _effect_revision_request(),
                _effect_intent_plan(),
                timeline=_timeline(),
                output_dir=str(root),
            )
            pack_path = root / "remotion_prompt_pack.json"
            outputs_path = root / "remotion_worker_outputs.json"
            out_review = root / "remotion_effect_review.json"
            pack_path.write_text(json.dumps(pack), encoding="utf-8")
            outputs_path.write_text(json.dumps(self._worker_outputs(root)), encoding="utf-8")

            proc = subprocess.run([
                sys.executable,
                "video_tools.py",
                "remotion-worker-outputs",
                "--prompt-pack", str(pack_path),
                "--worker-outputs", str(outputs_path),
                "--out-review", str(out_review),
            ], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            review = json.loads(out_review.read_text(encoding="utf-8"))
            self.assertEqual(review["artifact_role"], "remotion_effect_review")
            self.assertEqual(review["status"], "pending_review")

    def test_command_catalog_exposes_remotion_effect_adapter_steps(self):
        commands = [
            "effect-revision-request",
            "effect-revision-draft",
            "effect-collage-refs",
            "remotion-prompt-pack",
            "remotion-worker-outputs",
            "effect-render-verification",
            "remotion-composite-draft",
        ]
        manifest = build_command_manifest(commands)
        workflow = build_workflow_manifest(commands)

        self.assertEqual(manifest["commands"]["remotion-prompt-pack"]["group"], "contract")
        self.assertIn("remotion_effect_adapter", workflow["workflows"])
        self.assertEqual([
            item for item in workflow["missing_commands"]
            if item["workflow"] == "remotion_effect_adapter"
        ], [])


class RemotionWorkerSmokeTest(unittest.TestCase):
    def test_worker_smoke_runs_injected_command_and_writes_outputs(self):
        from video_pipeline_core.remotion_effects import (
            build_remotion_prompt_pack,
            run_remotion_worker_smoke,
            validate_remotion_worker_outputs,
        )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pack = build_remotion_prompt_pack(
                _effect_revision_request(),
                _effect_intent_plan(),
                timeline=_timeline(),
                output_dir=str(root / "renders"),
            )

            def fake_renderer(job, preview_file, rendered_asset):
                Path(preview_file).write_bytes(b"preview")
                Path(rendered_asset).write_bytes(b"rendered")
                evidence = Path(preview_file).with_suffix(".contact_sheet.jpg")
                evidence.write_bytes(b"evidence")
                return {
                    "ok": True,
                    "backend": "fake-remotion",
                    "command": ["fake"],
                    "evidence_refs": [str(evidence)],
                }

            outputs = run_remotion_worker_smoke(pack, root / "renders", renderer=fake_renderer)

            self.assertEqual(outputs["artifact_role"], "remotion_worker_outputs")
            self.assertEqual(outputs["summary"]["rendered_count"], 1)
            self.assertEqual(outputs["jobs"][0]["status"], "rendered")
            result = validate_remotion_worker_outputs(outputs, pack)
            self.assertTrue(result["ok"], result)

    def test_worker_smoke_records_failure_without_claiming_rendered(self):
        from video_pipeline_core.remotion_effects import (
            build_remotion_prompt_pack,
            run_remotion_worker_smoke,
        )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pack = build_remotion_prompt_pack(
                _effect_revision_request(),
                _effect_intent_plan(),
                timeline=_timeline(),
                output_dir=str(root / "renders"),
            )

            def failing_renderer(job, preview_file, rendered_asset):
                return {"ok": False, "error": "remotion unavailable"}

            outputs = run_remotion_worker_smoke(pack, root / "renders", renderer=failing_renderer)

            self.assertEqual(outputs["jobs"][0]["status"], "failed")
            self.assertEqual(outputs["summary"]["rendered_count"], 0)
            self.assertIn("remotion unavailable", outputs["jobs"][0]["error"])

    def test_worker_smoke_cli_writes_worker_outputs_with_dry_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            from video_pipeline_core.remotion_effects import build_remotion_prompt_pack
            pack = build_remotion_prompt_pack(
                _effect_revision_request(),
                _effect_intent_plan(),
                timeline=_timeline(),
                output_dir=str(root / "renders"),
            )
            pack_path = root / "remotion_prompt_pack.json"
            out = root / "remotion_worker_outputs.json"
            pack_path.write_text(json.dumps(pack), encoding="utf-8")

            proc = subprocess.run([
                sys.executable,
                "video_tools.py",
                "remotion-worker-smoke",
                "--prompt-pack", str(pack_path),
                "--out-dir", str(root / "renders"),
                "--out-worker-outputs", str(out),
                "--dry-run",
            ], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            written = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(written["artifact_role"], "remotion_worker_outputs")
            self.assertEqual(written["jobs"][0]["status"], "rendered")

    def test_worker_smoke_avoids_nested_paths_when_prompt_pack_uses_output_dir(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            from video_pipeline_core.remotion_effects import build_remotion_prompt_pack, run_remotion_worker_smoke

            pack = build_remotion_prompt_pack(
                _effect_revision_request(),
                _effect_intent_plan(),
                timeline=_timeline(),
                output_dir="remotion_effects",
            )
            outputs = run_remotion_worker_smoke(pack, root / "remotion_effects")
            job = outputs["jobs"][0]

            self.assertEqual(Path(job["preview_file"]).parent, root / "remotion_effects")
            self.assertEqual(Path(job["rendered_asset"]).parent, root / "remotion_effects")
            self.assertNotIn(
                "remotion_effects/remotion_effects",
                Path(job["rendered_asset"]).as_posix(),
            )

    def test_worker_smoke_dry_run_records_evidence_refs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            from video_pipeline_core.remotion_effects import build_remotion_prompt_pack, run_remotion_worker_smoke

            pack = build_remotion_prompt_pack(
                _effect_revision_request(),
                _effect_intent_plan(),
                timeline=_timeline(),
                output_dir="remotion_effects",
            )
            outputs = run_remotion_worker_smoke(pack, root / "remotion_effects")
            job = outputs["jobs"][0]

            self.assertIn("evidence_refs", job)
            self.assertTrue(job["evidence_refs"])
            for ref in job["evidence_refs"]:
                self.assertTrue(Path(ref).is_file(), ref)


class RemotionCompositeDraftTest(unittest.TestCase):
    def _accepted_review(self, root):
        rendered = root / "overlay.mov"
        preview = root / "preview.mp4"
        rendered.write_bytes(b"rendered")
        preview.write_bytes(b"preview")
        return {
            "artifact_role": "remotion_effect_review",
            "version": 1,
            "status": "accepted",
            "items": [{
                "job_id": "rm_fx_page_turn",
                "source_effect_id": "fx_page_turn",
                "effect_id": "fxintent_2_external_effect_1",
                "status": "accepted",
                "review": {"decision": "accept", "reviewer": "editor", "reason": "fits hook"},
                "preview_file": str(preview),
                "rendered_asset": str(rendered),
                "duration_sec": 1.0,
                "timing": {"start_sec": 0.5, "duration_sec": 1.0},
            }],
        }

    def test_composite_refuses_pending_review_items(self):
        from video_pipeline_core.remotion_effects import composite_accepted_remotion_effects

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "base.mp4"
            base.write_bytes(b"base")
            review = self._accepted_review(root)
            review["items"][0]["status"] = "pending_review"
            with self.assertRaises(ValueError):
                composite_accepted_remotion_effects(review, base, root / "draft.mp4")

    def test_composite_refuses_protected_final_output(self):
        from video_pipeline_core.remotion_effects import composite_accepted_remotion_effects

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "base.mp4"
            base.write_bytes(b"base")
            with self.assertRaises(ValueError):
                composite_accepted_remotion_effects(self._accepted_review(root), base, root / "final.mp4")

    def test_composite_builds_ffmpeg_overlay_command_with_accepted_items(self):
        from video_pipeline_core.remotion_effects import composite_accepted_remotion_effects

        calls = []

        def fake_runner(cmd, stdout=None, stderr=None, text=None):
            calls.append(cmd)
            Path(cmd[-1]).write_bytes(b"draft")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "base.mp4"
            base.write_bytes(b"base")
            out = root / "remotion_composite_draft.mp4"
            result = composite_accepted_remotion_effects(
                self._accepted_review(root),
                base,
                out,
                ffmpeg="ffmpeg",
                runner=fake_runner,
            )
            self.assertTrue(out.is_file())

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["applied_count"], 1)
        self.assertIn("overlay=", " ".join(calls[0]))

    def test_composite_cli_writes_draft_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "base.mp4"
            base.write_bytes(b"base")
            review = self._accepted_review(root)
            review_path = root / "remotion_effect_review.json"
            out = root / "remotion_composite_draft.mp4"
            report = root / "remotion_composite_report.json"
            review_path.write_text(json.dumps(review), encoding="utf-8")

            proc = subprocess.run([
                sys.executable,
                "video_tools.py",
                "remotion-composite-draft",
                "--review", str(review_path),
                "--base-video", str(base),
                "--out", str(out),
                "--report-out", str(report),
                "--dry-run",
            ], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            written = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(written["artifact_role"], "remotion_composite_draft_report")
            self.assertEqual(written["status"], "dry_run")


class RemotionAdapterE2ETest(unittest.TestCase):
    def test_prompt_worker_review_acceptance_to_noncanonical_draft(self):
        from video_pipeline_core.remotion_effects import (
            build_remotion_prompt_pack,
            composite_accepted_remotion_effects,
            run_remotion_worker_smoke,
            validate_remotion_worker_outputs,
        )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            canonical_final = root / "final.mp4"
            canonical_final.write_bytes(b"canonical final")

            pack = build_remotion_prompt_pack(
                _effect_revision_request(),
                _effect_intent_plan(),
                timeline=_timeline(),
                output_dir=str(root / "renders"),
            )
            outputs = run_remotion_worker_smoke(pack, root / "worker", renderer=None)
            review_result = validate_remotion_worker_outputs(outputs, pack)
            self.assertTrue(review_result["ok"], review_result)
            self.assertEqual(review_result["review_artifact"]["status"], "pending_review")

            review = review_result["review_artifact"]
            review["status"] = "accepted"
            for item in review["items"]:
                item["status"] = "accepted"
                item["review"] = {
                    "decision": "accept",
                    "reviewer": "codex-e2e",
                    "reason": "adapter output is ready for draft review",
                }

            draft = root / "remotion_composite_draft.mp4"
            report = composite_accepted_remotion_effects(
                review,
                canonical_final,
                draft,
                dry_run=True,
            )

            self.assertEqual(pack["summary"]["job_count"], 1)
            self.assertEqual(outputs["summary"]["rendered_count"], 1)
            self.assertTrue(draft.is_file())
            self.assertEqual(canonical_final.read_bytes(), b"canonical final")
            self.assertEqual(report["artifact_role"], "remotion_composite_draft_report")
            self.assertEqual(report["status"], "dry_run")
            self.assertEqual(report["applied_count"], 1)
            self.assertEqual(
                report["next_action"],
                "workbench_review_remotion_composite_draft",
            )
            self.assertIn("non-canonical draft", report["note"])


if __name__ == "__main__":
    unittest.main()
