import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.video_intent_planner import plan_video_intent


class VideoIntentPlannerTest(unittest.TestCase):
    def test_existing_material_enters_material_first_for_ambiguity_reduction(self):
        intent = plan_video_intent(
            {
                "request": "teaching video with existing class and screen-recording material",
                "video_type": "teaching",
                "audience": "new students",
                "goal": "teach clearly",
                "target_length": "5 minutes",
                "material_availability": "existing",
                "material_quality": "enough usable screen recordings",
                "tone": "clear instructional",
            }
        )

        self.assertEqual(intent["artifact_role"], "video_intent")
        self.assertEqual(intent["stage"], "Video Intent Planner")
        self.assertEqual(intent["video_type"], "teaching")
        self.assertEqual(intent["input_state"], "material_available")
        self.assertEqual(intent["entry_path"], "material-first")
        self.assertEqual(intent["route"], "material-first")
        self.assertEqual(intent["legacy_route"], "existing-material-first")
        self.assertEqual(intent["handoff_to"], "material_map_lifecycle")
        self.assertEqual(intent["gap_strategy"], "pending_material_delta")
        self.assertEqual(intent["material_contract"]["artifact_role"], "stage0_material_intent")
        self.assertEqual(intent["material_contract"]["first_action"], "material_map_quick_inventory")
        self.assertEqual(intent["handoff_packet"]["owner"], "material_map_lifecycle")
        self.assertEqual(intent["handoff_packet"]["first_action"], "material_map_quick_inventory")
        self.assertIn("project_material_map.json", intent["handoff_packet"]["expected_outputs"])
        self.assertIn("material_delta.json", intent["handoff_packet"]["expected_outputs"])
        self.assertIn("teaching-structure-planner", intent["later_planner"])
        self.assertEqual(intent["required_followup_questions"], [])
        self.assertEqual(intent["soundtrack_contract"]["music_role"], "unsure")
        self.assertEqual(intent["effect_policy"]["activation"], "none")
        self.assertEqual(intent["subtitle_voiceover_contract"]["artifact_role"], "stage0_subtitle_voiceover_intent")
        self.assertEqual(intent["subtitle_voiceover_contract"]["language"], "unknown")
        self.assertEqual(intent["subtitle_voiceover_contract"]["subtitle_required"], True)
        self.assertEqual(intent["subtitle_voiceover_contract"]["handoff_to"], "subtitle-director")
        self.assertEqual(intent["material_contract"]["contract_status"], "required")
        self.assertEqual(intent["soundtrack_contract"]["contract_status"], "optional")
        self.assertEqual(intent["effect_policy"]["contract_status"], "not_applicable")
        self.assertEqual(intent["subtitle_voiceover_contract"]["contract_status"], "required")
        self.assertIs(intent["stage0_child_contracts"]["material"], intent["material_contract"])
        self.assertIs(intent["stage0_child_contracts"]["soundtrack"], intent["soundtrack_contract"])
        self.assertIs(intent["stage0_child_contracts"]["effect"], intent["effect_policy"])
        self.assertIs(intent["stage0_child_contracts"]["subtitle_voiceover"], intent["subtitle_voiceover_contract"])

    def test_stage0_child_contracts_use_gate_status_vocabulary(self):
        intent = plan_video_intent(
            {
                "request": "make a no-material story video with a warm opening effect and voiceover",
                "video_type": "storybook",
                "audience": "children",
                "goal": "tell a gentle story",
                "target_length": "90 seconds",
                "material_availability": "none",
                "text_availability": "brief",
                "generation_allowed": True,
                "voiceover_required": True,
            }
        )

        allowed = {"required", "optional", "deferred", "not_applicable"}
        contracts = intent["stage0_child_contracts"]
        for key in ("material", "soundtrack", "effect", "subtitle_voiceover"):
            self.assertIn(contracts[key]["contract_status"], allowed, key)
        self.assertEqual(contracts["material"]["contract_status"], "deferred")
        self.assertEqual(contracts["subtitle_voiceover"]["contract_status"], "required")

    def test_existing_material_defaults_to_all_material_quick_inventory_scan(self):
        intent = plan_video_intent(
            {
                "request": "剪一支養成班精華影片，我有一批素材但還沒整理",
                "video_type": "graduation-event",
                "audience": "學員和教官",
                "goal": "先看素材再決定剪輯方向",
                "target_length": "3 minutes",
                "material_availability": "existing",
            }
        )

        scan = intent["material_scan_decision"]
        self.assertEqual(scan["artifact_role"], "stage0_material_scan_decision")
        self.assertTrue(scan["needed"])
        self.assertEqual(scan["default_scope"], "all_materials")
        self.assertIsNone(scan["user_scope"])
        self.assertEqual(scan["scan_depth"], "quick_inventory_first")
        self.assertEqual(scan["first_action"], "material_map_quick_inventory")
        self.assertEqual(scan["followup_question"], "要先掃全部素材，還是只掃指定資料夾 / 檔案？")
        self.assertEqual(intent["material_contract"]["scan_decision"]["scan_depth"], "quick_inventory_first")

    def test_existing_material_respects_user_specified_scan_scope(self):
        intent = plan_video_intent(
            {
                "request": "請只先看主任勉勵資料夾和合照，不要先掃全部素材",
                "video_type": "graduation-event",
                "audience": "學員",
                "goal": "剪一段結尾",
                "target_length": "60 seconds",
                "material_availability": "existing",
                "material_scope": "主任勉勵資料夾; 合照",
            }
        )

        scan = intent["material_scan_decision"]
        self.assertTrue(scan["needed"])
        self.assertEqual(scan["default_scope"], "user_specified")
        self.assertEqual(scan["user_scope"], "主任勉勵資料夾; 合照")
        self.assertEqual(scan["scan_depth"], "quick_inventory_first")
        self.assertIn("user specified", scan["reason"])

    def test_zero_material_with_text_or_story_enters_structure_first(self):
        intent = plan_video_intent(
            {
                "request": "children storybook video with no images but a story idea",
                "video_type": "storybook",
                "audience": "children",
                "goal": "tell a gentle bedtime story",
                "target_length": "3 minutes",
                "material_availability": "none",
                "text_availability": "brief",
                "generation_allowed": True,
                "tone": "warm story-driven",
            }
        )

        self.assertEqual(intent["input_state"], "text_available")
        self.assertEqual(intent["entry_path"], "structure-first")
        self.assertEqual(intent["route"], "structure-first")
        self.assertEqual(intent["legacy_route"], "story-first")
        self.assertEqual(intent["handoff_to"], "upstream_structure_route")
        self.assertEqual(intent["handoff_packet"]["owner"], "upstream_structure_route")
        self.assertEqual(intent["handoff_packet"]["first_action"], "story_soul_blueprint")
        self.assertEqual(intent["material_contract"]["first_action"], "derive_material_needs_after_structure")
        self.assertTrue(intent["needs_generated_material_fallback"])
        self.assertIn("generated material fallback", " ".join(intent["next_steps"]))

    def test_partial_material_still_enters_material_first_not_stage_zero_hybrid(self):
        intent = plan_video_intent(
            {
                "request": "graduation event recap with partial material",
                "video_type": "graduation-event",
                "audience": "classmates and instructors",
                "goal": "commemorate the training journey",
                "target_length": "4 minutes",
                "material_availability": "partial",
                "material_quality": "some gaps",
                "tone": "energetic and warm",
            }
        )

        self.assertEqual(intent["input_state"], "material_available")
        self.assertEqual(intent["entry_path"], "material-first")
        self.assertEqual(intent["route"], "material-first")
        self.assertEqual(intent["legacy_route"], "hybrid")
        self.assertEqual(intent["handoff_to"], "material_map_lifecycle")
        self.assertEqual(intent["gap_strategy"], "pending_material_delta")
        self.assertTrue(intent["needs_material_map_first"])
        self.assertIn("event-recap-planner", intent["later_planner"])

    def test_idea_only_without_type_or_audience_needs_context(self):
        intent = plan_video_intent({"request": "make me a video"})

        self.assertEqual(intent["input_state"], "unknown")
        self.assertEqual(intent["entry_path"], "needs-context")
        self.assertIsNone(intent["legacy_route"])
        self.assertEqual(intent["handoff_to"], "ask_followup")
        self.assertEqual(intent["handoff_packet"]["owner"], "Video Intent Planner")
        self.assertEqual(intent["handoff_packet"]["first_action"], "ask_followup_questions")
        self.assertGreaterEqual(len(intent["required_followup_questions"]), 4)
        question_text = " ".join(intent["required_followup_questions"]).lower()
        self.assertIn("material", question_text)
        self.assertIn("audience", question_text)

    def test_effect_only_request_keeps_stage0_schema_and_adds_effect_hint(self):
        intent = plan_video_intent(
            {
                "request": "我只想做一個開場特效和轉場效果",
                "video_type": "event recap",
                "audience": "students",
                "goal": "make the opening stronger",
                "target_length": "10 seconds",
                "material_availability": "none",
                "generation_allowed": True,
                "tone": "cinematic",
            }
        )

        self.assertIn(intent["entry_path"], {"structure-first", "needs-context"})
        self.assertEqual(intent["semantic_route_hint"], "effect-factory")
        self.assertEqual(intent["effect_policy"]["handoff_to"], "video-effect-factory")
        self.assertTrue(intent["effect_policy"]["required_now"])

    def test_generation_allowed_no_material_loose_idea_can_enter_structure_first(self):
        intent = plan_video_intent(
            {
                "request": "做一支 90 秒兒童故事，沒有素材，可以生成素材",
                "video_type": "storybook",
                "audience": "children",
                "goal": "tell a gentle short story",
                "target_length": "90 seconds",
                "material_availability": "none",
                "generation_allowed": True,
                "tone": "warm",
            }
        )

        self.assertEqual(intent["entry_path"], "structure-first")
        self.assertTrue(intent["needs_generated_material_fallback"])

    def test_stage0_records_mixed_song_and_bgm_soundtrack_contract(self):
        intent = plan_video_intent(
            {
                "request": "training recap with existing footage, warm story first half and hot-blooded MV with a pop song feeling later",
                "video_type": "graduation-event",
                "audience": "students and instructors",
                "goal": "make a memorable graduation recap",
                "target_length": "5 minutes",
                "material_availability": "existing",
                "style_direction": "first half warm story, second half MV with song and background music sections",
            }
        )

        soundtrack = intent["soundtrack_contract"]
        self.assertEqual(soundtrack["artifact_role"], "stage0_soundtrack_intent")
        self.assertEqual(soundtrack["status"], "requested")
        self.assertEqual(soundtrack["music_role"], "mixed")
        self.assertEqual(soundtrack["vocal_policy"], "section_dependent")
        self.assertEqual(soundtrack["section_strategy"], "section_based")
        self.assertEqual(soundtrack["handoff_to"], "soundtrack-arranger")
        self.assertIn("vocals/songs allowed", " ".join(soundtrack["required_followup_questions"]))
        self.assertEqual(soundtrack["energy_intent"], "warm_to_high")
        self.assertEqual(soundtrack["speech_preservation"], "preserve_if_detected")
        self.assertEqual(soundtrack["fallback_policy"]["provider_fallback"], ["jamendo_song", "pixabay_music", "manual_import", "reference_only"])
        self.assertEqual(soundtrack["fallback_policy"]["role_fallback"], "song_to_bgm_requires_review")
        self.assertEqual(soundtrack["fallback_policy"]["brownfield_fallback"], "workbench_replace_or_retime_after_review")

    def test_stage0_records_speech_preservation_when_speech_is_requested(self):
        intent = plan_video_intent(
            {
                "request": "training recap with existing footage, keep director speech clear and use soft background music",
                "video_type": "graduation-event",
                "audience": "students",
                "goal": "warm recap",
                "target_length": "4 minutes",
                "material_availability": "existing",
                "style_direction": "soft background music under speech",
            }
        )

        soundtrack = intent["soundtrack_contract"]
        self.assertEqual(soundtrack["music_role"], "bgm")
        self.assertEqual(soundtrack["speech_preservation"], "required")
        self.assertEqual(soundtrack["ducking_policy"], "duck_under_voice")
        comms = intent["communication_intent"]
        self.assertEqual(comms["original_audio_policy"], "preserve_speech")
        self.assertEqual(comms["music_policy"], "bgm")
        self.assertEqual(comms["speech_priority"], "high")
        self.assertIn("audio_director", comms["handoff_to"])

    def test_stage0_chinese_preserve_source_speech_under_bgm(self):
        intent = plan_video_intent(
            {
                "request": "我有一段訪談影片，請保留原聲講話，下面加背景音樂，不要蓋過人聲",
                "video_type": "event recap",
                "audience": "同事",
                "goal": "剪成精華",
                "target_length": "60 seconds",
                "material_availability": "existing",
            }
        )

        soundtrack = intent["soundtrack_contract"]
        self.assertEqual(soundtrack["music_role"], "bgm")
        self.assertEqual(soundtrack["speech_preservation"], "required")
        self.assertEqual(soundtrack["ducking_policy"], "duck_under_voice")
        comms = intent["communication_intent"]
        self.assertEqual(comms["original_audio_policy"], "preserve_speech")
        self.assertEqual(comms["music_policy"], "bgm")
        self.assertEqual(comms["speech_priority"], "high")

    def test_stage0_replaces_source_audio_for_music_led_no_speech_recap(self):
        intent = plan_video_intent(
            {
                "request": "make a 60 second highlight reel from one clip, no speech, energetic music only",
                "video_type": "event recap",
                "audience": "friends",
                "goal": "fast visual highlight",
                "target_length": "60 seconds",
                "material_availability": "existing",
                "style_direction": "MV rhythm with background music",
            }
        )

        comms = intent["communication_intent"]
        self.assertEqual(comms["voiceover_policy"], "none")
        self.assertEqual(comms["subtitle_policy"], "optional")
        self.assertEqual(comms["original_audio_policy"], "replace_with_music")
        self.assertEqual(comms["music_policy"], "bgm")
        self.assertEqual(comms["speech_priority"], "low")

    def test_stage0_records_mixed_source_audio_policy_for_speech_then_mv(self):
        intent = plan_video_intent(
            {
                "request": "training recap: first preserve the instructor speech, later cut an MV montage with music",
                "video_type": "graduation-event",
                "audience": "students",
                "goal": "ceremony and memory",
                "target_length": "5 minutes",
                "material_availability": "existing",
                "style_direction": "speech first, MV with music later",
            }
        )

        comms = intent["communication_intent"]
        self.assertEqual(comms["original_audio_policy"], "mixed")
        self.assertEqual(comms["music_policy"], "bgm")
        self.assertEqual(comms["speech_priority"], "high")
        self.assertEqual(comms["time_authority"], "video_sections")

    def test_stage0_records_instrumental_bgm_preference(self):
        intent = plan_video_intent(
            {
                "request": "make a documentary recap with existing footage and instrumental background music only",
                "video_type": "graduation-event",
                "audience": "family",
                "goal": "warm documentary memory",
                "target_length": "3 minutes",
                "material_availability": "existing",
                "music_role": "bgm",
                "style_direction": "instrumental no vocals",
            }
        )

        soundtrack = intent["soundtrack_contract"]
        self.assertEqual(soundtrack["music_role"], "bgm")
        self.assertEqual(soundtrack["vocal_policy"], "instrumental_preferred")
        self.assertEqual(soundtrack["handoff_to"], "soundtrack-arranger")

    def test_whole_video_effect_words_are_deferred_not_launched_from_stage0(self):
        intent = plan_video_intent(
            {
                "request": "make a training recap from existing footage with warm transitions and a highlight overlay",
                "video_type": "graduation-event",
                "audience": "students",
                "goal": "emotional recap",
                "target_length": "4 minutes",
                "material_availability": "existing",
            }
        )

        policy = intent["effect_policy"]
        self.assertEqual(policy["artifact_role"], "stage0_effect_policy")
        self.assertEqual(policy["status"], "requested")
        self.assertEqual(policy["activation"], "defer_to_brownfield_or_segment_review")
        self.assertFalse(policy["required_now"])
        self.assertEqual(policy["handoff_to"], "video-effect-factory_when_segment_requires_effect")

    def test_chinese_whole_video_with_effect_music_and_subtitle_stays_mainline(self):
        intent = plan_video_intent(
            {
                "request": "\u6211\u6709\u990a\u6210\u73ed\u7d20\u6750\uff0c\u60f3\u526a\u4e00\u652f5\u5206\u9418\u7d50\u8a13\u56de\u9867\u5f71\u7247\uff0c\u8981\u6709\u97f3\u6a02\u3001\u5b57\u5e55\u3001\u958b\u5834\u7279\u6548\u548c\u8f49\u5834",
                "video_type": "graduation-event",
                "audience": "\u5b78\u54e1\u548c\u6559\u5b98",
                "goal": "\u505a\u6210\u5b8c\u6574\u7d50\u8a13\u56de\u9867",
                "target_length": "5\u5206\u9418",
                "material_availability": "existing",
            }
        )

        self.assertEqual(intent["entry_path"], "material-first")
        self.assertIsNone(intent["semantic_route_hint"])
        self.assertEqual(intent["soundtrack_contract"]["handoff_to"], "soundtrack-arranger")
        self.assertEqual(intent["subtitle_voiceover_contract"]["handoff_to"], "subtitle-director")
        policy = intent["effect_policy"]
        self.assertEqual(policy["status"], "requested")
        self.assertEqual(policy["activation"], "defer_to_brownfield_or_segment_review")
        self.assertFalse(policy["required_now"])
        self.assertEqual(policy["handoff_to"], "video-effect-factory_when_segment_requires_effect")

    def test_chinese_effect_only_opening_can_still_route_to_effect_factory(self):
        intent = plan_video_intent(
            {
                "request": "\u53ea\u505a\u4e00\u500b10\u79d2\u958b\u5834\u7279\u6548\uff0c\u7d50\u8a13\u5100\u5f0f\u611f",
                "video_type": "event recap",
                "audience": "\u5b78\u54e1",
                "goal": "\u5f37\u5316\u958b\u5834",
                "target_length": "10\u79d2",
                "material_availability": "none",
                "generation_allowed": True,
                "tone": "cinematic",
            }
        )

        self.assertEqual(intent["semantic_route_hint"], "effect-factory")
        self.assertTrue(intent["effect_policy"]["required_now"])
        self.assertEqual(intent["effect_policy"]["handoff_to"], "video-effect-factory")

    def test_stage0_records_voiceover_and_subtitle_language_intent(self):
        intent = plan_video_intent(
            {
                "request": "make a Chinese training recap with subtitles and voiceover narration",
                "video_type": "graduation-event",
                "audience": "students and family",
                "goal": "explain the training journey clearly",
                "target_length": "5 minutes",
                "material_availability": "existing",
                "language": "zh-TW",
                "voiceover_required": True,
                "subtitle_required": True,
            }
        )

        contract = intent["subtitle_voiceover_contract"]
        self.assertEqual(contract["artifact_role"], "stage0_subtitle_voiceover_intent")
        self.assertEqual(contract["status"], "requested")
        self.assertEqual(contract["language"], "zh-TW")
        self.assertTrue(contract["subtitle_required"])
        self.assertTrue(contract["voiceover_required"])
        self.assertEqual(contract["narration_policy"], "required")
        self.assertEqual(contract["handoff_to"], "subtitle-director+audio-director")
        self.assertEqual(contract["preferred_provider"], "voxcpm")
        self.assertEqual(contract["fallback_provider"], "legacy_tts")
        self.assertFalse(contract["fallback_allowed"])
        self.assertEqual(contract["provider_runtime"], "local")

    def test_chinese_existing_single_clip_enters_material_first(self):
        intent = plan_video_intent(
            {
                "request": "我有一支5分鐘影片，想剪成精華短片",
                "audience": "家人",
                "goal": "保留亮點",
                "target_length": "60 seconds",
                "tone": "溫馨",
            }
        )

        self.assertEqual(intent["input_state"], "material_available")
        self.assertEqual(intent["material_availability"], "existing")
        self.assertEqual(intent["entry_path"], "material-first")
        self.assertEqual(intent["soundtrack_contract"]["energy_intent"], "warm")

    def test_chinese_photos_and_videos_recap_enters_material_first(self):
        intent = plan_video_intent(
            {
                "request": "我有一些照片和影片想做結訓回顧，後半段偏MV熱血",
                "audience": "學員和教官",
                "goal": "回顧成長",
                "target_length": "5 minutes",
            }
        )

        self.assertEqual(intent["video_type"], "graduation-event")
        self.assertEqual(intent["material_availability"], "existing")
        self.assertEqual(intent["entry_path"], "material-first")
        self.assertEqual(intent["soundtrack_contract"]["music_role"], "bgm")
        self.assertEqual(intent["soundtrack_contract"]["energy_intent"], "high")

    def test_chinese_no_material_story_enters_structure_first(self):
        intent = plan_video_intent(
            {
                "request": "我想做灰姑娘童話故事短篇，沒有素材",
                "audience": "兒童",
                "goal": "說一個睡前故事",
                "target_length": "90 seconds",
                "tone": "日式可愛",
                "generation_allowed": True,
            }
        )

        self.assertEqual(intent["input_state"], "text_available")
        self.assertEqual(intent["material_availability"], "none")
        self.assertEqual(intent["entry_path"], "structure-first")
        self.assertTrue(intent["needs_generated_material_fallback"])

    def test_chinese_article_without_media_enters_structure_first(self):
        intent = plan_video_intent(
            {
                "request": "我有一篇文章想轉成影片，沒有圖片或影片",
                "audience": "一般觀眾",
                "goal": "清楚傳達文章內容",
                "target_length": "2 minutes",
                "tone": "紀錄感",
            }
        )

        self.assertEqual(intent["input_state"], "text_available")
        self.assertEqual(intent["material_availability"], "none")
        self.assertEqual(intent["text_availability"], "brief")
        self.assertEqual(intent["entry_path"], "structure-first")

    def test_chinese_vague_video_still_needs_context(self):
        intent = plan_video_intent({"request": "幫我做一支影片"})

        self.assertEqual(intent["input_state"], "unknown")
        self.assertEqual(intent["entry_path"], "needs-context")
        self.assertGreaterEqual(len(intent["required_followup_questions"]), 4)


class VideoIntentPlannerCliTest(unittest.TestCase):
    def test_cli_writes_video_intent_json(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            brief = root / "brief.json"
            out = root / "video_intent.json"
            brief.write_text(
                json.dumps(
                    {
                        "request": "teaching video with existing material",
                        "video_type": "teaching",
                        "audience": "beginners",
                        "goal": "teach the workflow",
                        "target_length": "6 minutes",
                        "material_availability": "existing",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "video-intent-plan",
                    str(brief),
                    "--out",
                    str(out),
                ],
                check=True,
                cwd=Path(__file__).resolve().parents[1],
                stdout=subprocess.DEVNULL,
            )

            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["artifact_role"], "video_intent")
            self.assertEqual(payload["entry_path"], "material-first")


if __name__ == "__main__":
    unittest.main()
