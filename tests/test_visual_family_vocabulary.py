import json
import tempfile
import types
import unittest
from pathlib import Path

class VisualFamilyVocabularyTest(unittest.TestCase):
    def setUp(self):
        # Sample valid vocabulary
        self.vocab = {
            "artifact_role": "visual_family_vocabulary",
            "version": 1,
            "project": "mountain-rescue-test",
            "families": [
                {
                    "family": "night_search",
                    "definition": "夜間森林中進行搜索、導航或確認位置的畫面",
                    "aliases": [
                        "night_search_action",
                        "night_search_reaction",
                        "night_search_coordination",
                        "night_search_navigation"
                    ]
                },
                {
                    "family": "running_training",
                    "definition": "跑坡、負重等體能訓練畫面",
                    "aliases": [
                        "running_briefing"
                      ]
                }
            ]
        }
        # Sample valid review
        self.review = {
            "artifact_role": "visual_diversity_review",
            "version": 1,
            "reviewer": "agent-a",
            "at": "2026-06-15T15:30:00+08:00",
            "scenes": [
                {
                    "asset_id": "f0001",
                    "scene_index": 0,
                    "visual_family": "night_search_action",
                    "angle_scale": "wide",
                    "action_family": "night_search",
                    "subject": "search_team"
                },
                {
                    "asset_id": "f0002",
                    "scene_index": 0,
                    "visual_family": "running_training",
                    "angle_scale": "medium",
                    "action_family": "running",
                    "subject": "runners"
                }
            ]
        }

    def _get_module(self):
        from video_pipeline_core import visual_family_vocabulary as vfv
        return vfv

    def test_canonical_family_retained_and_alias_mapped(self):
        vfv = self._get_module()
        normalized = vfv.normalize_visual_diversity_review(self.review, self.vocab)

        # Check that scene 0 (alias "night_search_action") is mapped to "night_search"
        s0 = normalized["scenes"][0]
        self.assertEqual(s0["visual_family"], "night_search")
        self.assertEqual(s0["visual_family_normalization"]["original_family"], "night_search_action")
        self.assertEqual(s0["visual_family_normalization"]["canonical_family"], "night_search")
        self.assertEqual(s0["visual_family_normalization"]["vocabulary_project"], "mountain-rescue-test")

        # Check that scene 1 (canonical "running_training") is retained
        s1 = normalized["scenes"][1]
        self.assertEqual(s1["visual_family"], "running_training")
        self.assertEqual(s1["visual_family_normalization"]["original_family"], "running_training")
        self.assertEqual(s1["visual_family_normalization"]["canonical_family"], "running_training")

    def test_unknown_family_fails_closed(self):
        vfv = self._get_module()
        bad_review = json.loads(json.dumps(self.review))
        bad_review["scenes"][0]["visual_family"] = "unknown_family_tag"

        with self.assertRaises(ValueError):
            vfv.normalize_visual_diversity_review(bad_review, self.vocab)

    def test_duplicate_canonical_family_fails(self):
        vfv = self._get_module()
        bad_vocab = json.loads(json.dumps(self.vocab))
        bad_vocab["families"].append({
            "family": "night_search",
            "definition": "Duplicate family definition",
            "aliases": []
        })
        with self.assertRaises(ValueError):
            vfv.normalize_visual_diversity_review(self.review, bad_vocab)

    def test_duplicate_alias_across_families_fails(self):
        vfv = self._get_module()
        bad_vocab = json.loads(json.dumps(self.vocab))
        bad_vocab["families"][1]["aliases"].append("night_search_action")
        with self.assertRaises(ValueError):
            vfv.normalize_visual_diversity_review(self.review, bad_vocab)

    def test_alias_conflicts_with_canonical_family_fails(self):
        vfv = self._get_module()
        bad_vocab = json.loads(json.dumps(self.vocab))
        bad_vocab["families"][1]["aliases"].append("night_search")
        with self.assertRaises(ValueError):
            vfv.normalize_visual_diversity_review(self.review, bad_vocab)

    def test_malformed_fields_fail(self):
        vfv = self._get_module()
        malformed_vocabs = [
            # family is empty string
            {**self.vocab, "families": [{"family": " ", "definition": "def", "aliases": []}]},
            # family is number
            {**self.vocab, "families": [{"family": 123, "definition": "def", "aliases": []}]},
            # family is bool
            {**self.vocab, "families": [{"family": True, "definition": "def", "aliases": []}]},
            # definition is empty
            {**self.vocab, "families": [{"family": "fam", "definition": "", "aliases": []}]},
            # definition is list
            {**self.vocab, "families": [{"family": "fam", "definition": ["def"], "aliases": []}]},
            # alias is number
            {**self.vocab, "families": [{"family": "fam", "definition": "def", "aliases": [123]}]},
            # alias is empty string
            {**self.vocab, "families": [{"family": "fam", "definition": "def", "aliases": [""]}]},
            # alias is bool
            {**self.vocab, "families": [{"family": "fam", "definition": "def", "aliases": [True]}]}
        ]
        for mv in malformed_vocabs:
            with self.assertRaises(ValueError):
                vfv.normalize_visual_diversity_review(self.review, mv)

    def test_non_visual_diversity_review_fails(self):
        vfv = self._get_module()
        bad_review = json.loads(json.dumps(self.review))
        bad_review["artifact_role"] = "not_a_review"
        with self.assertRaises(ValueError):
            vfv.normalize_visual_diversity_review(bad_review, self.vocab)

    def test_only_visual_family_modified(self):
        vfv = self._get_module()
        normalized = vfv.normalize_visual_diversity_review(self.review, self.vocab)

        orig_s0 = self.review["scenes"][0]
        norm_s0 = normalized["scenes"][0]

        self.assertEqual(norm_s0["asset_id"], orig_s0["asset_id"])
        self.assertEqual(norm_s0["scene_index"], orig_s0["scene_index"])
        self.assertEqual(norm_s0["angle_scale"], orig_s0["angle_scale"])
        self.assertEqual(norm_s0["action_family"], orig_s0["action_family"])
        self.assertEqual(norm_s0["subject"], orig_s0["subject"])

    def test_input_review_is_not_mutated(self):
        vfv = self._get_module()
        orig_copy = json.loads(json.dumps(self.review))
        normalized = vfv.normalize_visual_diversity_review(self.review, self.vocab)
        self.assertEqual(self.review, orig_copy)

    def test_writer_fails_without_modifying_output(self):
        vfv = self._get_module()
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            review_file = d / "review.json"
            vocab_file = d / "vocab.json"
            out_file = d / "out.json"

            # Setup files
            review_file.write_text(json.dumps(self.review), encoding="utf-8")
            vocab_file.write_text(json.dumps(self.vocab), encoding="utf-8")
            out_file.write_text("OLD CONTENT", encoding="utf-8")

            # Try writing with a bad review (triggering failure)
            bad_review = json.loads(json.dumps(self.review))
            bad_review["scenes"][0]["visual_family"] = "unknown_family_tag"
            review_file.write_text(json.dumps(bad_review), encoding="utf-8")

            with self.assertRaises(ValueError):
                vfv.write_normalized_review(str(review_file), str(vocab_file), str(out_file))

            # Verify old content is preserved and not replaced
            self.assertEqual(out_file.read_text(encoding="utf-8"), "OLD CONTENT")

    def test_cli_runs_normalization(self):
        from video_tools import cmd_visual_family_normalize
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            review_file = d / "review.json"
            vocab_file = d / "vocab.json"
            out_file = d / "out.json"

            review_file.write_text(json.dumps(self.review), encoding="utf-8")
            vocab_file.write_text(json.dumps(self.vocab), encoding="utf-8")

            args = types.SimpleNamespace(
                review=str(review_file),
                vocabulary=str(vocab_file),
                out=str(out_file)
            )
            cmd_visual_family_normalize(args)

            written = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertEqual(written["scenes"][0]["visual_family"], "night_search")
            self.assertEqual(written["reviewer"], "agent-a")

    # Hardening unit tests
    def test_version_must_be_strict_int_1(self):
        # A. version=True/"1"/1.0 全 fail。
        vfv = self._get_module()
        for bad_version in (True, "1", 1.0, False, [1]):
            bad_vocab = json.loads(json.dumps(self.vocab))
            bad_vocab["version"] = bad_version
            with self.assertRaises(ValueError):
                vfv.normalize_visual_diversity_review(self.review, bad_vocab)

    def test_empty_families_fails(self):
        # B. empty families fail。
        vfv = self._get_module()
        bad_vocab = json.loads(json.dumps(self.vocab))
        bad_vocab["families"] = []
        with self.assertRaises(ValueError):
            vfv.normalize_visual_diversity_review(self.review, bad_vocab)

    def test_invalid_asset_ids_fail(self):
        # C. asset_id=[]/""/" " /123/True 全 fail。
        vfv = self._get_module()
        for bad_asset_id in ([], "", "  ", 123, True, False, {}):
            bad_review = json.loads(json.dumps(self.review))
            bad_review["scenes"][0]["asset_id"] = bad_asset_id
            with self.assertRaises(ValueError):
                vfv.normalize_visual_diversity_review(bad_review, self.vocab)

    def test_invalid_scene_indices_fail(self):
        # D. scene_index={}/[]/-1/True/"0" 全 fail。
        vfv = self._get_module()
        for bad_index in ({}, [], -1, True, False, "0", 1.5):
            bad_review = json.loads(json.dumps(self.review))
            bad_review["scenes"][0]["scene_index"] = bad_index
            with self.assertRaises(ValueError):
                vfv.normalize_visual_diversity_review(bad_review, self.vocab)

    def test_duplicate_scene_references_fail(self):
        # E. duplicate scene reference fail。
        vfv = self._get_module()
        bad_review = json.loads(json.dumps(self.review))
        # Add a scene with identical asset_id and scene_index
        bad_review["scenes"].append({
            "asset_id": "f0001",
            "scene_index": 0,
            "visual_family": "running_training"
        })
        with self.assertRaises(ValueError):
            vfv.normalize_visual_diversity_review(bad_review, self.vocab)

    def test_existing_normalization_lineage_fails(self):
        # F. existing normalization lineage 不得被無聲覆寫。
        vfv = self._get_module()
        bad_review = json.loads(json.dumps(self.review))
        bad_review["scenes"][0]["visual_family_normalization"] = {
            "vocabulary_project": "old-project",
            "original_family": "night_search_action",
            "canonical_family": "night_search"
        }
        with self.assertRaises(ValueError):
            vfv.normalize_visual_diversity_review(bad_review, self.vocab)


if __name__ == "__main__":
    unittest.main()
