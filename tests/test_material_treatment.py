"""Tests for video_pipeline_core.material_treatment.

Covers:
  - Enumeration → photo_stack_beat → n_required = item count
  - Emotional → single_hold → n_required = 1
  - Bridge → quick_cut_bridge → n_required = 2..4
  - Testimony/proof/identity → real_material_only (honesty guard)
  - Explicit material_treatment override
  - section_role fallback (opening→establishing, closing→emotional)
  - editing_policy treatment_defaults_by_pattern override
  - Lane plan co-variation
  - video_primary / collage / stepped_sequence
"""
import math
import unittest

from video_pipeline_core.material_treatment import resolve_treatment, VALID_TREATMENTS


class TestResolveEnumeration(unittest.TestCase):
    """content_pattern=enumeration → photo_stack_beat, n = item count."""

    def test_enumeration_three_items(self):
        seg = {
            "editing_intent": {"content_pattern": "enumeration"},
            "material_treatment": {
                "items": ["Ethiopia", "Colombia", "Guatemala"],
            },
        }
        result = resolve_treatment(seg, beat_count=8)
        self.assertEqual(result["treatment"], "photo_stack_beat")
        self.assertEqual(result["n_required"], 3)

    def test_enumeration_items_clamped_to_beats(self):
        seg = {
            "editing_intent": {"content_pattern": "enumeration"},
            "material_treatment": {
                "items": ["a", "b", "c", "d", "e"],
            },
        }
        result = resolve_treatment(seg, beat_count=3)
        self.assertEqual(result["treatment"], "photo_stack_beat")
        self.assertEqual(result["n_required"], 3)  # clamped

    def test_enumeration_no_items_uses_beat_count(self):
        seg = {
            "editing_intent": {"content_pattern": "enumeration"},
        }
        result = resolve_treatment(seg, beat_count=6)
        self.assertEqual(result["treatment"], "photo_stack_beat")
        self.assertEqual(result["n_required"], 6)


class TestResolveEmotional(unittest.TestCase):
    """content_pattern=emotional → single_hold → n=1."""

    def test_emotional_single_hold(self):
        seg = {
            "editing_intent": {"content_pattern": "emotional"},
        }
        result = resolve_treatment(seg, beat_count=4)
        self.assertEqual(result["treatment"], "single_hold")
        self.assertEqual(result["n_required"], 1)

    def test_emotional_lane_plan(self):
        seg = {"editing_intent": {"content_pattern": "emotional"}}
        result = resolve_treatment(seg, beat_count=4)
        self.assertEqual(result["lane_plan"]["subtitle"], "narrative_card")
        self.assertEqual(result["lane_plan"]["music"], "swell_or_drop")


class TestResolveBridge(unittest.TestCase):
    """content_pattern=bridge → quick_cut_bridge → n = 2..4."""

    def test_bridge_default(self):
        seg = {
            "editing_intent": {"content_pattern": "bridge"},
            "duration_sec": 3.0,
        }
        result = resolve_treatment(seg, beat_count=4)
        self.assertEqual(result["treatment"], "quick_cut_bridge")
        self.assertGreaterEqual(result["n_required"], 2)
        self.assertLessEqual(result["n_required"], 4)

    def test_bridge_short_duration(self):
        seg = {
            "editing_intent": {"content_pattern": "bridge"},
            "duration_sec": 1.5,
        }
        result = resolve_treatment(seg, beat_count=4)
        self.assertEqual(result["treatment"], "quick_cut_bridge")
        self.assertEqual(result["n_required"], 2)  # clamped to min 2

    def test_bridge_long_duration_capped_at_4(self):
        seg = {
            "editing_intent": {"content_pattern": "bridge"},
            "duration_sec": 10.0,
        }
        result = resolve_treatment(seg, beat_count=8)
        self.assertEqual(result["treatment"], "quick_cut_bridge")
        self.assertEqual(result["n_required"], 4)  # capped at max 4

    def test_bridge_custom_policy(self):
        seg = {
            "editing_intent": {"content_pattern": "bridge"},
            "duration_sec": 3.0,
        }
        policy = {"bridge_shot_sec": [0.4, 1.0]}
        result = resolve_treatment(seg, beat_count=4, editing_policy=policy)
        self.assertEqual(result["treatment"], "quick_cut_bridge")
        expected_n = min(4, max(2, math.ceil(3.0 / 1.0)))
        self.assertEqual(result["n_required"], expected_n)


class TestHonestyGuard(unittest.TestCase):
    """testimony/proof/identity → always real_material_only."""

    def test_testimony(self):
        seg = {"editing_intent": {"content_pattern": "testimony"}}
        result = resolve_treatment(seg, beat_count=4)
        self.assertEqual(result["treatment"], "real_material_only")

    def test_proof(self):
        seg = {"editing_intent": {"content_pattern": "proof"}}
        result = resolve_treatment(seg, beat_count=4)
        self.assertEqual(result["treatment"], "real_material_only")

    def test_identity(self):
        seg = {"editing_intent": {"content_pattern": "identity"}}
        result = resolve_treatment(seg, beat_count=4)
        self.assertEqual(result["treatment"], "real_material_only")

    def test_testimony_overrides_explicit_treatment(self):
        """Even with an explicit material_treatment override, honesty guard wins."""
        seg = {
            "editing_intent": {"content_pattern": "testimony"},
            "material_treatment": {"treatment": "photo_stack_beat"},
        }
        result = resolve_treatment(seg, beat_count=4)
        self.assertEqual(result["treatment"], "real_material_only")

    def test_real_material_only_lane(self):
        seg = {"editing_intent": {"content_pattern": "proof"}}
        result = resolve_treatment(seg, beat_count=4)
        self.assertEqual(result["lane_plan"]["subtitle"], "name_super_and_asr")
        self.assertEqual(result["lane_plan"]["music"], "duck_under_speech")


class TestExplicitOverride(unittest.TestCase):
    """Explicit material_treatment.treatment overrides pattern default."""

    def test_override_to_collage(self):
        seg = {
            "editing_intent": {"content_pattern": "enumeration"},
            "material_treatment": {
                "treatment": "collage",
                "items": ["a", "b", "c"],
            },
        }
        result = resolve_treatment(seg, beat_count=4)
        self.assertEqual(result["treatment"], "collage")

    def test_override_to_video_primary(self):
        seg = {
            "editing_intent": {"content_pattern": "emotional"},
            "material_treatment": {"treatment": "video_primary"},
        }
        result = resolve_treatment(seg, beat_count=4)
        self.assertEqual(result["treatment"], "video_primary")
        self.assertEqual(result["n_required"], 1)


class TestSectionRoleFallback(unittest.TestCase):
    """section_role fallback when content_pattern is absent."""

    def test_opening_to_establishing(self):
        seg = {
            "core": {"section_role": "opening"},
        }
        result = resolve_treatment(seg, beat_count=4)
        # opening → establishing → single_hold
        self.assertEqual(result["treatment"], "single_hold")

    def test_closing_to_emotional(self):
        seg = {
            "editing_intent": {"segment_role": "closing"},
        }
        result = resolve_treatment(seg, beat_count=4)
        # closing → emotional → single_hold
        self.assertEqual(result["treatment"], "single_hold")
        self.assertEqual(result["n_required"], 1)

    def test_unknown_role_fallback(self):
        seg = {
            "editing_intent": {"segment_role": "development"},
        }
        result = resolve_treatment(seg, beat_count=4)
        # No fallback for development → ultimate fallback single_hold
        self.assertEqual(result["treatment"], "single_hold")


class TestEditingPolicyOverride(unittest.TestCase):
    """editing_policy.treatment_defaults_by_pattern overrides built-in defaults."""

    def test_policy_override_enumeration(self):
        seg = {"editing_intent": {"content_pattern": "enumeration"}}
        policy = {
            "treatment_defaults_by_pattern": {
                "enumeration": "collage",
            }
        }
        result = resolve_treatment(seg, beat_count=4, editing_policy=policy)
        self.assertEqual(result["treatment"], "collage")


class TestProcess(unittest.TestCase):
    """content_pattern=process → stepped_sequence."""

    def test_process_with_steps(self):
        seg = {
            "editing_intent": {"content_pattern": "process"},
            "material_treatment": {
                "steps": ["grind", "brew", "pour"],
            },
        }
        result = resolve_treatment(seg, beat_count=8)
        self.assertEqual(result["treatment"], "stepped_sequence")
        self.assertEqual(result["n_required"], 3)

    def test_process_no_steps(self):
        seg = {"editing_intent": {"content_pattern": "process"}}
        result = resolve_treatment(seg, beat_count=8)
        self.assertEqual(result["treatment"], "stepped_sequence")
        self.assertEqual(result["n_required"], 1)  # min 1


class TestAction(unittest.TestCase):
    """content_pattern=action → video_primary."""

    def test_action(self):
        seg = {"editing_intent": {"content_pattern": "action"}}
        result = resolve_treatment(seg, beat_count=4)
        self.assertEqual(result["treatment"], "video_primary")
        self.assertEqual(result["n_required"], 1)
        self.assertEqual(result["lane_plan"]["subtitle"], "light_label")


class TestCollage(unittest.TestCase):
    """Collage treatment requires minimum 2."""

    def test_collage_items(self):
        seg = {
            "editing_intent": {"content_pattern": "enumeration"},
            "material_treatment": {
                "treatment": "collage",
                "items": ["a", "b", "c", "d"],
            },
        }
        result = resolve_treatment(seg, beat_count=4)
        self.assertEqual(result["treatment"], "collage")
        self.assertEqual(result["n_required"], 4)

    def test_collage_min_2(self):
        seg = {
            "material_treatment": {
                "treatment": "collage",
                "items": ["a"],
            },
        }
        result = resolve_treatment(seg, beat_count=4)
        self.assertEqual(result["treatment"], "collage")
        self.assertEqual(result["n_required"], 2)  # minimum


class TestReturnShape(unittest.TestCase):
    """Result always has the documented keys."""

    def test_all_keys_present(self):
        seg = {"editing_intent": {"content_pattern": "emotional"}}
        result = resolve_treatment(seg, beat_count=4)
        self.assertIn("treatment", result)
        self.assertIn("n_required", result)
        self.assertIn("lane_plan", result)
        self.assertIn("reason", result)
        self.assertIn(result["treatment"], VALID_TREATMENTS)
        self.assertIsInstance(result["n_required"], int)
        self.assertIsInstance(result["lane_plan"], dict)
        self.assertIn("photo_video", result["lane_plan"])
        self.assertIn("subtitle", result["lane_plan"])
        self.assertIn("music", result["lane_plan"])


class TestPacingConflict(unittest.TestCase):
    """SPEC self-contradiction surfaced: 1-material treatment vs multi-shot pacing
    (the ai-video soul-v3 monotony failure — develop sections marked 'establishing'
    with preferred_shot_sec=[4,8] over ~24s budgets resolved to single_hold)."""

    def test_single_hold_with_multishot_pacing_flags_conflict(self):
        seg = {
            "editing_intent": {"content_pattern": "establishing"},
            "pacing": {"preferred_shot_sec": [4, 8]},
            "duration_sec": 24.0,
        }
        result = resolve_treatment(seg, beat_count=8)
        self.assertEqual(result["treatment"], "single_hold")
        self.assertTrue(result["pacing_conflict"])
        self.assertIn("pacing_conflict", result["reason"])

    def test_short_budget_no_conflict(self):
        seg = {
            "editing_intent": {"content_pattern": "establishing"},
            "pacing": {"preferred_shot_sec": [4, 8]},
            "duration_sec": 6.0,
        }
        result = resolve_treatment(seg, beat_count=8)
        self.assertFalse(result["pacing_conflict"])

    def test_multi_material_treatment_no_conflict(self):
        seg = {
            "editing_intent": {"content_pattern": "enumeration"},
            "material_treatment": {"items": ["a", "b", "c"]},
            "pacing": {"preferred_shot_sec": [4, 8]},
            "duration_sec": 24.0,
        }
        result = resolve_treatment(seg, beat_count=8)
        self.assertFalse(result["pacing_conflict"])

    def test_no_pacing_declared_no_conflict(self):
        seg = {"editing_intent": {"content_pattern": "emotional"}, "duration_sec": 30.0}
        result = resolve_treatment(seg, beat_count=4)
        self.assertFalse(result["pacing_conflict"])

    def test_honesty_guard_path_carries_flag_shape(self):
        seg = {
            "editing_intent": {"content_pattern": "testimony"},
            "pacing": {"preferred_shot_sec": [4, 8]},
            "duration_sec": 24.0,
        }
        result = resolve_treatment(seg, beat_count=8)
        self.assertEqual(result["treatment"], "real_material_only")
        self.assertFalse(result["pacing_conflict"])


if __name__ == "__main__":
    unittest.main()
