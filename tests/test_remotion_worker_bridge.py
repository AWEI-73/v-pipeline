import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _job(target_file="rendered.mov", preview_file="preview.mp4"):
    return {
        "job_id": "rm_fx4e_opening_glow",
        "source_effect_id": "fx_opening_glow",
        "component_family": "light_leak_overlay",
        "prompt": "warm opening glow",
        "props": {
            "intent": "add a warm cinematic glow to the opening",
            "visual_language": ["warm glow", "soft sweep"],
            "intensity": "medium",
            "duration_sec": 1.2,
            "display_text": "開場回顧",
            "presentation": {
                "text_position": "bottom_left",
                "text_scale": "large",
                "effect_strength": "subtle",
                "safe_area": "lower_third",
                "theme": "training_recap_67",
                "accent_color": "#ffd400",
                "text_color": "#ffffff",
                "background_style": "white_blue_label",
            },
        },
        "timing": {"start_sec": 0.0, "duration_sec": 1.2},
        "output": {
            "type": "overlay_video",
            "alpha": True,
            "target_file": target_file,
            "preview_file": preview_file,
        },
    }


def _training_opening_job(target_file="rendered.mov", preview_file="preview.mp4"):
    job = _job(target_file, preview_file)
    job["component_family"] = "title_reveal"
    job["props"].update({
        "template_id": "training_opening_title",
        "display_text": "67TH TRAINING",
        "subtitle_text": "ON THE LAST PAGE",
        "presentation": {
            "theme": "training_recap_67",
            "background_style": "black_collage",
            "text_position": "bottom_left",
            "text_scale": "hero",
            "effect_strength": "emphasis",
            "safe_area": "title_safe",
            "accent_color": "#ffe100",
            "text_color": "#ffe100",
        },
        "collage_media_refs": [
            {"ref_id": "opening_01", "path": "C:/tmp/opening_01.jpg", "label": "集合"},
            {"ref_id": "training_01", "path": "C:/tmp/training_01.jpg", "label": "訓練"},
        ],
    })
    return job


def _speaker_yellow_bar_job(target_file="rendered.mov", preview_file="preview.mp4"):
    job = _job(target_file, preview_file)
    job["component_family"] = "lower_third_motion"
    job["props"].update({
        "template_id": "speaker_subtitle_yellow_bar",
        "display_text": "主任：保持初心，繼續前進。",
        "speaker_name": "主任",
        "presentation": {
            "theme": "training_recap_67",
            "background_style": "yellow_subtitle_bar",
            "text_position": "bottom_center",
            "text_scale": "medium",
            "effect_strength": "subtle",
            "safe_area": "subtitle_safe",
            "accent_color": "#ffe100",
            "text_color": "#101010",
        },
    })
    return job


def _module_label_job(target_file="rendered.mov", preview_file="preview.mp4"):
    job = _job(target_file, preview_file)
    job["component_family"] = "lower_third_motion"
    job["props"].update({
        "template_id": "module_label_white_blue",
        "display_text": "單元一：基礎訓練",
        "subtitle_text": "安全、紀律、默契",
        "presentation": {
            "theme": "training_recap_67",
            "background_style": "white_blue_label",
            "text_position": "bottom_left",
            "text_scale": "medium",
            "effect_strength": "subtle",
            "safe_area": "lower_third",
            "accent_color": "#1952b2",
            "text_color": "#1952b2",
        },
    })
    return job


def _profile_memory_card_job(target_file="rendered.mov", preview_file="preview.mp4"):
    job = _job(target_file, preview_file)
    job["component_family"] = "title_reveal"
    job["props"].update({
        "template_id": "profile_memory_card",
        "display_text": "第三組",
        "subtitle_text": "從陌生到並肩完成任務",
        "presentation": {
            "theme": "training_recap_67",
            "background_style": "clean_profile_card",
            "text_position": "bottom_left",
            "text_scale": "large",
            "effect_strength": "medium",
            "safe_area": "title_safe",
            "accent_color": "#ffe100",
            "text_color": "#ffffff",
        },
        "collage_media_refs": [
            {"ref_id": "team_01", "path": "C:/tmp/team_01.jpg", "label": "team"},
        ],
    })
    return job


def _film_strip_job(target_file="rendered.mov", preview_file="preview.mp4"):
    job = _job(target_file, preview_file)
    job["component_family"] = "page_turn_transition"
    job["props"].update({
        "template_id": "film_strip_transition_card",
        "display_text": "故事開始加速",
        "subtitle_text": "從回憶進入節奏段落",
        "presentation": {
            "theme": "training_recap_67",
            "background_style": "film_strip",
            "text_position": "bottom_left",
            "text_scale": "large",
            "effect_strength": "medium",
            "safe_area": "title_safe",
            "accent_color": "#ffe100",
            "text_color": "#ffffff",
        },
    })
    return job


def _story_to_mv_build_spec_job(target_file="rendered.mov", preview_file="preview.mp4"):
    job = _film_strip_job(target_file, preview_file)
    job["timing"]["duration_sec"] = 4.0
    job["props"]["duration_sec"] = 4.0
    job["props"]["display_text"] = "Story to montage"
    job["props"]["subtitle_text"] = "Pacing shift"
    job["props"]["prompt_parameters"] = {
        "effect_goal": "story_half_to_mv_half_transition",
        "effect_build_spec": {
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
        },
    }
    return job


def _clean_quote_job(target_file="rendered.mov", preview_file="preview.mp4"):
    job = _job(target_file, preview_file)
    job["component_family"] = "title_reveal"
    job["props"].update({
        "template_id": "clean_white_quote_card",
        "display_text": "每一次集合，都是下一次出發",
        "subtitle_text": "67期養成班",
        "presentation": {
            "theme": "training_recap_67",
            "background_style": "clean_white_quote",
            "text_position": "bottom_center",
            "text_scale": "large",
            "effect_strength": "subtle",
            "safe_area": "title_safe",
            "accent_color": "#1e5bb8",
            "text_color": "#111111",
        },
    })
    return job


def _memory_photo_wall_job(target_file="rendered.mov", preview_file="preview.mp4"):
    job = _job(target_file, preview_file)
    job["component_family"] = "title_reveal"
    job["timing"]["duration_sec"] = 8.0
    job["props"].update({
        "template_id": "memory_photo_wall",
        "display_text": "Training Memory",
        "subtitle_text": "one by one reveal",
        "duration_sec": 8.0,
        "presentation": {
            "theme": "training_recap_67",
            "background_style": "memory_photo_wall",
            "text_position": "bottom_left",
            "text_scale": "large",
            "effect_strength": "subtle",
            "safe_area": "title_safe",
            "accent_color": "#ffd36a",
            "text_color": "#ffffff",
        },
        "prompt_parameters": {
            "effect_goal": "brownfield_memory_photo_wall",
            "effect_build_spec": {
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
            },
        },
        "collage_media_refs": [
            {"ref_id": "group_photo", "path": "C:/tmp/group.jpg", "label": "group"},
            {"ref_id": "training_photo", "path": "C:/tmp/training.jpg", "label": "training"},
            {"ref_id": "mentor_photo", "path": "C:/tmp/mentor.jpg", "label": "mentor"},
        ],
    })
    return job


def _soft_light_transition_job(target_file="rendered.mov", preview_file="preview.mp4"):
    job = _job(target_file, preview_file)
    job["component_family"] = "light_leak_overlay"
    job["props"].update({
        "template_id": "soft_light_transition",
        "display_text": "下一段旅程",
        "presentation": {
            "theme": "training_recap_67",
            "background_style": "transparent",
            "text_position": "bottom_left",
            "text_scale": "small",
            "effect_strength": "subtle",
            "safe_area": "none",
            "accent_color": "#ffe6a6",
            "text_color": "#ffffff",
        },
    })
    return job


def _highlight_warm_glow_job(target_file="rendered.mov", preview_file="preview.mp4"):
    job = _job(target_file, preview_file)
    job["component_family"] = "overlay_motion"
    job["props"].update({
        "template_id": "highlight_warm_glow",
        "display_text": "關鍵時刻",
        "presentation": {
            "theme": "training_recap_67",
            "background_style": "transparent",
            "text_position": "bottom_left",
            "text_scale": "small",
            "effect_strength": "medium",
            "safe_area": "none",
            "accent_color": "#ffd36a",
            "text_color": "#ffffff",
        },
    })
    return job


def _blurred_side_fill_job(target_file="rendered.mov", preview_file="preview.mp4"):
    job = _job(target_file, preview_file)
    job["component_family"] = "panel_frame_motion"
    job["props"].update({
        "template_id": "blurred_side_fill",
        "display_text": "直式素材補滿",
        "presentation": {
            "theme": "training_recap_67",
            "background_style": "blurred_side_fill",
            "text_position": "bottom_left",
            "text_scale": "small",
            "effect_strength": "subtle",
            "safe_area": "none",
            "accent_color": "#ffffff",
            "text_color": "#ffffff",
        },
        "collage_media_refs": [
            {"ref_id": "vertical_01", "path": "C:/tmp/vertical_01.jpg", "label": "vertical"},
        ],
    })
    return job


class RemotionWorkerBridgeTest(unittest.TestCase):
    def test_write_entry_only_creates_remotion_entry_and_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            rendered = root / "rendered.mov"
            project = root / "remotion_project"
            job_path.write_text(json.dumps(_job(str(rendered), str(preview))), encoding="utf-8")

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(rendered),
                "--project-root", str(project),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["status"], "entry_written")
            entry = Path(payload["entry"])
            self.assertTrue(entry.is_file())
            text = entry.read_text(encoding="utf-8")
            self.assertIn("HermesEffectOverlay", text)
            self.assertIn("registerRoot", text)
            self.assertIn("warm opening glow", text)
            self.assertIn("showTextInRender", text)
            self.assertIn("preview || JOB.showTextInRender", text)
            self.assertIn("開場回顧", text)
            self.assertIn("textScale", text)
            self.assertIn("effectStrength", text)
            self.assertIn("training_recap_67", text)
            self.assertIn("white_blue_label", text)
            self.assertIn("accentColor", text)
            self.assertEqual(payload["rendered_asset"], str(rendered))
            self.assertEqual(payload["preview_file"], str(preview))
            self.assertIn("--codec=prores", " ".join(payload["render_command"]))

    def test_training_opening_template_writes_black_collage_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            rendered = root / "rendered.mov"
            project = root / "remotion_project"
            job_path.write_text(
                json.dumps(_training_opening_job(str(rendered), str(preview))),
                encoding="utf-8",
            )

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(rendered),
                "--project-root", str(project),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            entry = Path(payload["entry"])
            text = entry.read_text(encoding="utf-8")
            self.assertIn("black_collage", text)
            self.assertIn("collageSlots", text)
            self.assertIn("collageMediaRefs", text)
            self.assertIn("C:/tmp/opening_01.jpg", text)
            self.assertIn("subtitle", text)
            self.assertIn("ON THE LAST PAGE", text)
            self.assertIn("#ffe100", text)

    def test_visual_technique_plan_drives_sakura_particle_layer(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            rendered = root / "rendered.mov"
            project = root / "remotion_project"
            job = _training_opening_job(str(rendered), str(preview))
            job["props"]["prompt_parameters"] = {
                "visual_technique_plan": {
                    "artifact_role": "visual_technique_plan",
                    "version": 1,
                    "style_family": "japanese_sakura",
                    "effect_role": "opening_title",
                    "render_strategy": ["remotion_react_particles", "remotion_canvas_particles"],
                    "visual_primitives": ["sakura", "petals", "soft_bloom"],
                    "motion_primitives": ["drift", "fall", "parallax"],
                    "controls": {
                        "petal_count": 36,
                        "wind_strength": 0.42,
                        "fall_speed": 0.31,
                        "depth_layers": 4,
                    },
                },
                "motion_grammar": ["drift", "fall", "parallax"],
            }
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(rendered),
                "--project-root", str(project),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            text = Path(payload["entry"]).read_text(encoding="utf-8")
            self.assertIn("visualTechnique", text)
            self.assertIn("isJapaneseSakuraTechnique", text)
            self.assertIn("sakuraPetals", text)
            self.assertIn("sakuraWindStrength", text)
            self.assertIn("sakuraFallSpeed", text)
            self.assertIn("sakuraDepthLayers", text)
            self.assertIn("visualTechniqueSakuraLayer", text)
            self.assertIn("sakuraPetal", text)
            self.assertIn("japanese_sakura", text)
            self.assertIn("petal_count", text)

    def test_visual_technique_plan_drives_warm_legacy_fire_photo_closing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sample = root / "group_photo.jpg"
            sample.write_bytes(b"fake-jpeg-bytes")
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            rendered = root / "rendered.mov"
            project = root / "remotion_project"
            job = _training_opening_job(str(rendered), str(preview))
            job["props"]["template_id"] = "training_closing_title"
            job["props"]["display_text"] = "Next Stage"
            job["props"]["subtitle_text"] = "Carry the spirit forward"
            job["props"]["collage_media_refs"] = [
                {"ref_id": "group_photo", "path": str(sample), "label": "group photo", "visual_role": "group_photo"}
            ]
            job["props"]["prompt_parameters"] = {
                "visual_technique_plan": {
                    "artifact_role": "visual_technique_plan",
                    "version": 1,
                    "style_family": "warm_legacy_fire",
                    "effect_role": "closing_title",
                    "material_use": {
                        "background_source": "group_photo",
                        "background_treatment": "soft_dimmed_memory_plate",
                        "preserve_people_visibility": True,
                    },
                    "visual_primitives": [
                        "soft_ember_particles",
                        "afterglow_warm_light",
                        "dimmed_group_photo_background",
                    ],
                    "motion_primitives": ["slow_rise", "gentle_drift", "long_fade_out", "very_slow_push_in"],
                    "controls": {
                        "ember_density": "low",
                        "glow_strength": "soft",
                        "photo_dim_strength": "medium",
                        "subtitle_readability": "high",
                    },
                },
                "motion_grammar": ["slow_rise", "gentle_drift", "long_fade_out"],
            }
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(rendered),
                "--project-root", str(project),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            text = Path(payload["entry"]).read_text(encoding="utf-8")
            self.assertIn("isWarmLegacyFireTechnique", text)
            self.assertIn("warmLegacyPhotoBackground", text)
            self.assertIn("warmLegacyEmbers", text)
            self.assertIn("warmLegacyAfterglow", text)
            self.assertIn("photoDimStrength", text)
            self.assertIn("subtitleReadability", text)
            self.assertIn("data:image/jpeg;base64,", text)

    def test_warm_legacy_fire_overrides_clean_quote_template_background(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sample = root / "group_photo.jpg"
            sample.write_bytes(b"fake-jpeg-bytes")
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            rendered = root / "rendered.mov"
            project = root / "remotion_project"
            job = _clean_quote_job(str(rendered), str(preview))
            job["props"]["collage_media_refs"] = [
                {"ref_id": "group_photo", "path": str(sample), "label": "group photo", "visual_role": "group_photo"}
            ]
            job["props"]["prompt_parameters"] = {
                "visual_technique_plan": {
                    "artifact_role": "visual_technique_plan",
                    "version": 1,
                    "style_family": "warm_legacy_fire",
                    "effect_role": "closing_title",
                    "material_use": {"background_source": "group_photo"},
                    "controls": {
                        "ember_density": "low",
                        "photo_dim_strength": "medium",
                        "subtitle_readability": "high",
                    },
                },
            }
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(rendered),
                "--project-root", str(project),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            text = Path(payload["entry"]).read_text(encoding="utf-8")
            self.assertIn('const isCleanWhiteQuote = !isWarmLegacyFireTechnique &&', text)
            self.assertIn("warmLegacyPhotoBackground", text)
            self.assertIn("clean_white_quote_card", text)

    def test_training_opening_template_writes_cinematic_commercial_layers(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            rendered = root / "rendered.mov"
            project = root / "remotion_project"
            job = _training_opening_job(str(rendered), str(preview))
            job["props"]["presentation"]["variant"] = "cinematic_collage_reveal"
            job["props"]["presentation"]["motion_energy"] = "high"
            job["props"]["presentation"]["hero_media_policy"] = "avoid_title_bearing"
            job["props"]["presentation"]["title_hierarchy"] = "hero"
            job["props"]["prompt_parameters"] = {
                "effect_goal": "formal_training_opening",
                "material_strategy": {
                    "hero_source": "reviewed_people_group",
                    "avoid_hero_roles": ["title_card"],
                },
            }
            job["props"]["collage_media_refs"][0]["contains_title"] = True
            job["props"]["collage_media_refs"][0]["visual_role"] = "title_card"
            job["props"]["collage_media_refs"][1]["contains_title"] = False
            job["props"]["collage_media_refs"][1]["visual_role"] = "people_group"
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(rendered),
                "--project-root", str(project),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            text = Path(payload["entry"]).read_text(encoding="utf-8")
            self.assertIn("cinematic_collage_reveal", text)
            self.assertIn("commercialOpeningPlate", text)
            self.assertIn("cinematicDepthVignette", text)
            self.assertIn("scanlineTexture", text)
            self.assertIn("goldTitleSweep", text)
            self.assertIn("collageDepthShadow", text)
            self.assertIn("commercialCollageSlots", text)
            self.assertIn("heroCollageSlot", text)
            self.assertIn("commercialTitleScale", text)
            self.assertIn("cinematicTitleUnderline", text)
            self.assertIn("cinematicSubtitleLine", text)
            self.assertIn("motionEnergy", text)
            self.assertIn("heroMediaPolicy", text)
            self.assertIn("orderedCollageMediaRefs", text)
            self.assertIn("promptHeroSource", text)
            self.assertIn("promptAvoidHeroRoles", text)
            self.assertIn("reviewed_people_group", text)
            self.assertIn("containsTitle", text)
            self.assertNotIn("{JOB.visual}", text)

    def test_opening_motion_grammar_controls_cinematic_opening_layers(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            rendered = root / "rendered.mov"
            project = root / "remotion_project"
            job = _training_opening_job(str(rendered), str(preview))
            job["props"]["presentation"]["variant"] = "cinematic_collage_reveal"
            job["props"]["prompt_parameters"] = {
                "effect_goal": "formal_training_opening",
                "motion_grammar": ["collage_depth_reveal"],
            }
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(rendered),
                "--project-root", str(project),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            text = Path(payload["entry"]).read_text(encoding="utf-8")
            self.assertIn("const enableCollageDepthReveal = usesMotionGrammar(\"collage_depth_reveal\")", text)
            self.assertIn("const enableGoldTitleSweep = usesMotionGrammar(\"gold_title_sweep\")", text)
            self.assertIn("const enableTitlePunch = usesMotionGrammar(\"title_punch\")", text)
            self.assertIn("isCinematicOpening && enableCollageDepthReveal", text)
            self.assertIn("isCinematicOpening && enableGoldTitleSweep", text)
            self.assertIn("enableTitlePunch ? titleImpactPulse : 1", text)

    def test_speaker_subtitle_template_writes_yellow_bar_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            rendered = root / "rendered.mov"
            project = root / "remotion_project"
            job_path.write_text(
                json.dumps(_speaker_yellow_bar_job(str(rendered), str(preview))),
                encoding="utf-8",
            )

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(rendered),
                "--project-root", str(project),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            text = Path(payload["entry"]).read_text(encoding="utf-8")
            self.assertIn("yellow_subtitle_bar", text)
            self.assertIn("isYellowSubtitleBar", text)
            self.assertIn("speakerName", text)
            self.assertIn("主任", text)
            self.assertIn("主任：保持初心，繼續前進。", text)

    def test_module_label_template_writes_white_blue_module_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            rendered = root / "rendered.mov"
            project = root / "remotion_project"
            job_path.write_text(
                json.dumps(_module_label_job(str(rendered), str(preview)), ensure_ascii=False),
                encoding="utf-8",
            )

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(rendered),
                "--project-root", str(project),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            text = Path(payload["entry"]).read_text(encoding="utf-8")
            self.assertIn("module_label_white_blue", text)
            self.assertIn("isModuleLabelWhiteBlue", text)
            self.assertIn("moduleAccentBlock", text)
            self.assertIn("單元一：基礎訓練", text)
            self.assertIn("#1952b2", text)

    def test_profile_memory_card_template_writes_profile_card_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sample = root / "team_01.jpg"
            sample.write_bytes(b"fake-jpeg-bytes")
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            rendered = root / "rendered.mov"
            project = root / "remotion_project"
            job = _profile_memory_card_job(str(rendered), str(preview))
            job["props"]["collage_media_refs"][0]["path"] = str(sample)
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(rendered),
                "--project-root", str(project),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            text = Path(payload["entry"]).read_text(encoding="utf-8")
            self.assertIn("clean_profile_card", text)
            self.assertIn("isProfileMemoryCard", text)
            self.assertIn("profilePhotoFrame", text)
            self.assertIn("data:image/jpeg;base64,", text)
            self.assertIn("第三組", text)

    def test_soft_light_transition_template_writes_light_sweep_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            rendered = root / "rendered.mov"
            project = root / "remotion_project"
            job_path.write_text(
                json.dumps(_soft_light_transition_job(str(rendered), str(preview)), ensure_ascii=False),
                encoding="utf-8",
            )

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(rendered),
                "--project-root", str(project),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            text = Path(payload["entry"]).read_text(encoding="utf-8")
            self.assertIn("soft_light_transition", text)
            self.assertIn("isSoftLightTransition", text)
            self.assertIn("softLightSweep", text)
            self.assertIn("#ffe6a6", text)

    def test_highlight_warm_glow_template_writes_focus_glow_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            rendered = root / "rendered.mov"
            project = root / "remotion_project"
            job_path.write_text(
                json.dumps(_highlight_warm_glow_job(str(rendered), str(preview)), ensure_ascii=False),
                encoding="utf-8",
            )

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(rendered),
                "--project-root", str(project),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            text = Path(payload["entry"]).read_text(encoding="utf-8")
            self.assertIn("highlight_warm_glow", text)
            self.assertIn("isHighlightWarmGlow", text)
            self.assertIn("focusGlowRing", text)
            self.assertIn("#ffd36a", text)

    def test_blurred_side_fill_template_writes_panel_frame_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sample = root / "vertical_01.jpg"
            sample.write_bytes(b"fake-jpeg-bytes")
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            rendered = root / "rendered.mov"
            project = root / "remotion_project"
            job = _blurred_side_fill_job(str(rendered), str(preview))
            job["props"]["collage_media_refs"][0]["path"] = str(sample)
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(rendered),
                "--project-root", str(project),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            text = Path(payload["entry"]).read_text(encoding="utf-8")
            self.assertIn("blurred_side_fill", text)
            self.assertIn("isBlurredSideFill", text)
            self.assertIn("sideFillFrame", text)
            self.assertIn("data:image/jpeg;base64,", text)

    def test_bridge_embeds_repo_relative_media_refs(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as media_temp, tempfile.TemporaryDirectory() as job_temp:
            media_root = Path(media_temp)
            job_root = Path(job_temp)
            sample = media_root / "relative_sample.jpg"
            sample.write_bytes(b"repo-relative-jpeg")
            relative_sample = sample.relative_to(ROOT)
            job_path = job_root / "job.json"
            preview = job_root / "preview.mp4"
            rendered = job_root / "rendered.mov"
            project = job_root / "remotion_project"
            job = _blurred_side_fill_job(str(rendered), str(preview))
            job["props"]["collage_media_refs"][0]["path"] = str(relative_sample)
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(rendered),
                "--project-root", str(project),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            text = Path(payload["entry"]).read_text(encoding="utf-8")
            self.assertIn("data:image/jpeg;base64,", text)

    def test_film_strip_transition_template_writes_film_strip_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            rendered = root / "rendered.mov"
            project = root / "remotion_project"
            job_path.write_text(
                json.dumps(_film_strip_job(str(rendered), str(preview)), ensure_ascii=False),
                encoding="utf-8",
            )

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(rendered),
                "--project-root", str(project),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            text = Path(payload["entry"]).read_text(encoding="utf-8")
            self.assertIn("film_strip", text)
            self.assertIn("isFilmStripCard", text)
            self.assertIn("filmStripHoles", text)
            self.assertIn("故事開始加速", text)
            self.assertIn("從回憶進入節奏段落", text)

    def test_film_strip_transition_template_writes_story_to_mv_commercial_layers(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sample = root / "transition_thumb.jpg"
            sample.write_bytes(b"fake-jpeg-bytes")
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            rendered = root / "rendered.mov"
            project = root / "remotion_project"
            job = _film_strip_job(str(rendered), str(preview))
            job["props"]["presentation"]["variant"] = "story_to_mv_film_transition"
            job["props"]["prompt_parameters"] = {
                "effect_goal": "story_half_to_mv_half_transition",
                "transition_strength": "impact",
                "motion_grammar": ["film_rail", "thumbnail_acceleration", "hard_cut_bars"],
                "negative_rules": ["do_not_read_as_static_chapter_card"],
            }
            job["props"]["collage_media_refs"] = [
                {"ref_id": "story_01", "path": str(sample), "label": "story"},
            ]
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(rendered),
                "--project-root", str(project),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            text = Path(payload["entry"]).read_text(encoding="utf-8")
            self.assertIn("story_to_mv_film_transition", text)
            self.assertIn("commercialFilmGate", text)
            self.assertIn("filmThumbnailRail", text)
            self.assertIn("filmFlashWipe", text)
            self.assertIn("movingSprocketMask", text)
            self.assertIn("commercialFilmRailSlots", text)
            self.assertIn("commercialTransitionTitleBlock", text)
            self.assertIn("suppressStoryToMvBaseText", text)
            self.assertIn("filmCenterFrame", text)
            self.assertIn("storyMvSplitBeam", text)
            self.assertIn("transitionPhaseLabels", text)
            self.assertIn("largeReadablePhaseLabels", text)
            self.assertIn("energyPulseBars", text)
            self.assertIn("transitionTimingRamp", text)
            self.assertIn("titleImpactPulse", text)
            self.assertIn("midpointImpactFrame", text)
            self.assertIn("acceleratingThumbnailRail", text)
            self.assertIn("thumbnailAccelerationCurve", text)
            self.assertIn("transitionStrengthScale", text)
            self.assertIn("promptMotionGrammar", text)
            self.assertIn("hardCutImpactBars", text)
            self.assertIn("commercialImpactShutter", text)
            self.assertIn("impactFlashPlate", text)
            self.assertIn("impactBarsScale", text)
            self.assertIn("thumbnailMotionBlurTrail", text)
            self.assertIn("promptParameters", text)
            self.assertIn("story_half_to_mv_half_transition", text)
            self.assertIn("hard_cut_bars", text)
            self.assertIn("data:image/jpeg;base64,", text)

    def test_story_to_mv_motion_grammar_can_disable_unlisted_transition_layers(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sample = root / "transition_thumb.jpg"
            sample.write_bytes(b"fake-jpeg-bytes")
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            rendered = root / "rendered.mov"
            project = root / "remotion_project"
            job = _film_strip_job(str(rendered), str(preview))
            job["props"]["presentation"]["variant"] = "story_to_mv_film_transition"
            job["props"]["prompt_parameters"] = {
                "effect_goal": "story_half_to_mv_half_transition",
                "transition_strength": "soft",
                "motion_grammar": ["film_rail"],
            }
            job["props"]["collage_media_refs"] = [
                {"ref_id": "story_01", "path": str(sample), "label": "story"},
            ]
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(rendered),
                "--project-root", str(project),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            text = Path(payload["entry"]).read_text(encoding="utf-8")
            self.assertIn("filmThumbnailRail", text)
            self.assertIn("const enableFilmRail = usesMotionGrammar(\"film_rail\")", text)
            self.assertIn("const enableThumbnailAcceleration = usesMotionGrammar(\"thumbnail_acceleration\")", text)
            self.assertIn("const enableFlashWipe = usesMotionGrammar(\"flash_wipe\")", text)
            self.assertIn("const enableHardCutBars = usesMotionGrammar(\"hard_cut_bars\")", text)
            self.assertIn("isStoryToMvFilmTransition && enableFilmRail", text)
            self.assertIn("isStoryToMvFilmTransition && enableThumbnailAcceleration", text)
            self.assertIn("isStoryToMvFilmTransition && enableFlashWipe", text)
            self.assertIn("isStoryToMvFilmTransition && enableHardCutBars", text)

    def test_story_to_mv_build_spec_drives_transition_controls(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sample = root / "transition_thumb.jpg"
            sample.write_bytes(b"fake-jpeg-bytes")
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            rendered = root / "rendered.mov"
            project = root / "remotion_project"
            job = _story_to_mv_build_spec_job(str(rendered), str(preview))
            job["props"]["collage_media_refs"] = [
                {"ref_id": "story_01", "path": str(sample), "label": "story"},
            ]
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(rendered),
                "--project-root", str(project),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            text = Path(payload["entry"]).read_text(encoding="utf-8")
            self.assertIn("StoryToMVTransition", text)
            self.assertIn("isStoryToMvBuildSpec", text)
            self.assertIn("storyToMvPhaseLabels", text)
            self.assertIn("buildSpecMotionGrammar", text)
            self.assertIn("impactMomentFrame", text)
            self.assertIn("thumbnailAccelerationStrength", text)
            self.assertIn("pacingShift", text)
            self.assertIn("slow_to_fast", text)
            self.assertIn("phase_labels", text)
            self.assertIn("isStoryToMvTransition", text)
            self.assertIn("data:image/jpeg;base64,", text)

    def test_clean_quote_template_writes_white_quote_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            rendered = root / "rendered.mov"
            project = root / "remotion_project"
            job_path.write_text(
                json.dumps(_clean_quote_job(str(rendered), str(preview)), ensure_ascii=False),
                encoding="utf-8",
            )

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(rendered),
                "--project-root", str(project),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            text = Path(payload["entry"]).read_text(encoding="utf-8")
            self.assertIn("clean_white_quote", text)
            self.assertIn("isCleanWhiteQuote", text)
            self.assertIn("quoteAccentLine", text)
            self.assertIn("每一次集合，都是下一次出發", text)
            self.assertIn("#111111", text)

    def test_memory_photo_wall_template_writes_sequential_reveal_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            samples = []
            for name in ("group.jpg", "training.jpg", "mentor.jpg"):
                sample = root / name
                sample.write_bytes(b"fake-jpeg-bytes")
                samples.append(sample)
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            rendered = root / "rendered.mov"
            project = root / "remotion_project"
            job = _memory_photo_wall_job(str(rendered), str(preview))
            for ref, sample in zip(job["props"]["collage_media_refs"], samples):
                ref["path"] = str(sample)
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(rendered),
                "--project-root", str(project),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            text = Path(payload["entry"]).read_text(encoding="utf-8")
            self.assertIn("memory_photo_wall", text)
            self.assertIn("isMemoryPhotoWall", text)
            self.assertIn("memoryWallSlots", text)
            self.assertIn("memoryRevealIntervalFrames", text)
            self.assertIn("holdAfterFullWallFrames", text)
            self.assertIn("slowPushInScale", text)
            self.assertIn("minimalCaption", text)
            self.assertIn("reveal_mode", text)
            self.assertIn("one_by_one", text)
            self.assertIn("data:image/jpeg;base64,", text)

    def test_memory_photo_wall_uses_build_spec_material_refs_when_collage_refs_empty(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sample = root / "wall_keyframe.jpg"
            sample.write_bytes(b"fake-jpeg-bytes")
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            rendered = root / "rendered.mov"
            project = root / "remotion_project"
            job = _memory_photo_wall_job(str(rendered), str(preview))
            job["props"]["collage_media_refs"] = []
            job["props"]["prompt_parameters"]["effect_build_spec"]["material_refs"] = [{
                "ref_id": "real_0001",
                "path": str(sample),
                "label": "reviewed keyframe",
                "visual_role": ["opening"],
                "evidence_kind": "material_wall_keyframe",
            }]
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(rendered),
                "--project-root", str(project),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            text = Path(payload["entry"]).read_text(encoding="utf-8")
            self.assertIn("reviewed keyframe", text)
            self.assertIn("data:image/jpeg;base64,", text)

    def test_bridge_refuses_canonical_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            job_path.write_text(json.dumps(_job("final.mp4", str(preview))), encoding="utf-8")

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(root / "final.mp4"),
                "--project-root", str(root / "project"),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("protected canonical", proc.stderr)

    def test_bridge_requires_positive_duration(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bad = _job()
            bad["timing"]["duration_sec"] = 0
            job_path = root / "job.json"
            job_path.write_text(json.dumps(bad), encoding="utf-8")

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(root / "preview.mp4"),
                "--rendered-asset", str(root / "rendered.mov"),
                "--project-root", str(root / "project"),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("duration_sec", proc.stderr)

    def test_bridge_accepts_utf8_sig_job_json(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            rendered = root / "rendered.mov"
            job_path.write_text("\ufeff" + json.dumps(_job(str(rendered), str(preview))), encoding="utf-8")

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(rendered),
                "--project-root", str(root / "project"),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
