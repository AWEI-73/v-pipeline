import json
import hashlib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from video_pipeline_core.rendered_product_qa import build_rendered_product_qa, write_rendered_product_qa


class RenderedProductQATest(unittest.TestCase):
    @staticmethod
    def _probe_and_sampler(*, audio):
        def fake_probe(_path):
            streams = [{"codec_type": "video", "codec_name": "h264"}]
            if audio:
                streams.append({"codec_type": "audio", "codec_name": "aac"})
            return {
                "ok": True,
                "duration_sec": 42.0,
                "streams": streams,
                "raw": {"format": {"duration": "42.0"}},
            }

        def fake_sampler(_video, out_dir):
            frame = Path(out_dir) / "rendered_product_qa_frames" / "frame_000.jpg"
            frame.parent.mkdir(parents=True, exist_ok=True)
            frame.write_bytes(b"jpg")
            sheet = Path(out_dir) / "rendered_product_qa_contact_sheet.jpg"
            sheet.write_bytes(b"jpg")
            return {"ok": True, "frames": [frame], "contact_sheet": sheet}

        return fake_probe, fake_sampler

    @staticmethod
    def _write_silent_picture_contract(path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"picture_only": True, "audio_policy": "silent_no_source_audio"}
            ),
            encoding="utf-8",
        )

    def test_missing_rendered_candidate_blocks(self):
        with TemporaryDirectory() as tmp:
            result = build_rendered_product_qa(tmp, tmp)

        self.assertFalse(result["pass"])
        self.assertIn("missing_rendered_candidate", {item["rule"] for item in result["blocking"]})

    def test_candidate_requires_probe_and_frame_evidence(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "final.mp4").write_bytes(b"not a real video")

            result = build_rendered_product_qa(root, root)

            self.assertFalse(result["pass"])
            rules = {item["rule"] for item in result["blocking"]}
            self.assertIn("ffprobe_failed", rules)
            self.assertIn("missing_frame_evidence", rules)
            self.assertEqual(result["source_tool"], "tools/rendered_product_qa.py")

    def test_probe_and_frame_evidence_pass(self):
        def fake_probe(_path):
            return {
                "ok": True,
                "duration_sec": 42.0,
                "streams": [
                    {"codec_type": "video", "codec_name": "h264"},
                    {"codec_type": "audio", "codec_name": "aac"},
                ],
                "raw": {"format": {"duration": "42.0"}},
            }

        def fake_sampler(_video, out_dir):
            frame = Path(out_dir) / "rendered_product_qa_frames" / "frame_000.jpg"
            frame.parent.mkdir(parents=True, exist_ok=True)
            frame.write_bytes(b"jpg")
            sheet = Path(out_dir) / "rendered_product_qa_contact_sheet.jpg"
            sheet.write_bytes(b"jpg")
            return {"ok": True, "frames": [frame], "contact_sheet": sheet}

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "final.mp4").write_bytes(b"fake video")

            result = build_rendered_product_qa(
                root,
                root,
                probe_func=fake_probe,
                sampler_func=fake_sampler,
            )

            self.assertTrue(result["pass"])
            self.assertEqual(result["blocking"], [])
            self.assertTrue(result["contact_sheet"].endswith("rendered_product_qa_contact_sheet.jpg"))

    def test_legacy_missing_audio_remains_fail(self):
        probe, sampler = self._probe_and_sampler(audio=False)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "final.mp4").write_bytes(b"fake video")

            result = build_rendered_product_qa(root, root, probe_func=probe, sampler_func=sampler)

        self.assertFalse(result["pass"])
        self.assertIn("missing_audio_stream", {item["rule"] for item in result["blocking"]})
        self.assertEqual(result["audio_contract"]["expectation"], "required")

    def test_valid_silent_picture_only_contract_allows_no_audio(self):
        probe, sampler = self._probe_and_sampler(audio=False)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "final.mp4").write_bytes(b"fake video")
            contract = root / "inputs" / "combined_rough_cut_plan.json"
            self._write_silent_picture_contract(contract)

            result = build_rendered_product_qa(
                root, root, audio_contract=contract, probe_func=probe, sampler_func=sampler
            )
            contract_sha256 = hashlib.sha256(contract.read_bytes()).hexdigest()

        self.assertTrue(result["pass"])
        self.assertEqual(result["audio_contract"]["expectation"], "forbidden")
        self.assertEqual(result["audio_contract"]["contract_path"], "inputs/combined_rough_cut_plan.json")
        self.assertEqual(result["audio_contract"]["contract_sha256"], contract_sha256)
        self.assertTrue(result["audio_contract"]["picture_only"])
        self.assertEqual(result["audio_contract"]["audio_policy"], "silent_no_source_audio")

    def test_silent_picture_only_contract_rejects_unexpected_audio(self):
        probe, sampler = self._probe_and_sampler(audio=True)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "final.mp4").write_bytes(b"fake video")
            contract = root / "contract.json"
            self._write_silent_picture_contract(contract)

            result = build_rendered_product_qa(
                root, root, audio_contract=contract, probe_func=probe, sampler_func=sampler
            )

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("unexpected_audio_stream", rules)
        self.assertNotIn("missing_audio_stream", rules)

    def test_invalid_missing_out_of_run_and_unrecognized_contracts_fail_closed(self):
        probe, sampler = self._probe_and_sampler(audio=False)
        with TemporaryDirectory() as tmp, TemporaryDirectory() as outside_tmp:
            root = Path(tmp)
            (root / "final.mp4").write_bytes(b"fake video")
            outside = Path(outside_tmp) / "contract.json"
            self._write_silent_picture_contract(outside)
            cases = {
                "missing": root / "missing.json",
                "out_of_run": outside,
                "malformed": root / "malformed.json",
                "unrecognized": root / "unrecognized.json",
            }
            cases["malformed"].write_text("{not json", encoding="utf-8")
            cases["unrecognized"].write_text(
                json.dumps({"picture_only": True, "audio_policy": "unknown"}),
                encoding="utf-8",
            )

            for label, contract in cases.items():
                with self.subTest(contract=label):
                    result = build_rendered_product_qa(
                        root, root, audio_contract=contract, probe_func=probe, sampler_func=sampler
                    )
                    self.assertFalse(result["pass"])
                    self.assertIn(
                        "invalid_audio_contract",
                        {item["rule"] for item in result["blocking"]},
                    )

    def test_normal_video_audio_behavior_remains_pass(self):
        probe, sampler = self._probe_and_sampler(audio=True)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "final.mp4").write_bytes(b"fake video")

            result = build_rendered_product_qa(root, root, probe_func=probe, sampler_func=sampler)

        self.assertTrue(result["pass"])
        self.assertEqual(result["audio_contract"]["expectation"], "required")

    def test_json_readback_preserves_audio_contract_evidence(self):
        probe, sampler = self._probe_and_sampler(audio=False)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "final.mp4").write_bytes(b"fake video")
            contract = root / "contract.json"
            self._write_silent_picture_contract(contract)

            result = write_rendered_product_qa(
                root,
                root,
                audio_contract=contract,
                probe_func=probe,
                sampler_func=sampler,
            )
            loaded = json.loads((root / "rendered_product_qa.json").read_text(encoding="utf-8"))

        self.assertEqual(loaded["audio_contract"], result["audio_contract"])
        self.assertEqual(loaded["audio_contract"]["expectation"], "forbidden")

    @staticmethod
    def _passing_probe_and_sampler():
        def fake_probe(_path):
            return {
                "ok": True,
                "duration_sec": 42.0,
                "streams": [
                    {"codec_type": "video", "codec_name": "h264"},
                    {"codec_type": "audio", "codec_name": "aac"},
                ],
                "raw": {"format": {"duration": "42.0"}},
            }

        def fake_sampler(_video, out_dir):
            frame = Path(out_dir) / "rendered_product_qa_frames" / "frame_000.jpg"
            frame.parent.mkdir(parents=True, exist_ok=True)
            frame.write_bytes(b"jpg")
            sheet = Path(out_dir) / "rendered_product_qa_contact_sheet.jpg"
            sheet.write_bytes(b"jpg")
            return {"ok": True, "frames": [frame], "contact_sheet": sheet}

        return fake_probe, fake_sampler

    def test_title_effect_design_only_blocks_when_effects_required(self):
        probe, sampler = self._passing_probe_and_sampler()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "final.mp4").write_bytes(b"fake video")
            (root / "title_effect_lifecycle_qa.json").write_text(
                json.dumps({"pass": True}), encoding="utf-8"
            )
            # no render profile artifact -> effects treated as claimed -> hard block

            result = build_rendered_product_qa(root, root, probe_func=probe, sampler_func=sampler)

            self.assertFalse(result["pass"])
            self.assertIn("title_effect_evidence_missing", {b["rule"] for b in result["blocking"]})

    def test_title_effect_design_only_warns_for_music_subtitle_profile(self):
        probe, sampler = self._passing_probe_and_sampler()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "final.mp4").write_bytes(b"fake video")
            (root / "title_effect_lifecycle_qa.json").write_text(
                json.dumps({"pass": True}), encoding="utf-8"
            )
            (root / "render_handoff.json").write_text(
                json.dumps({"music_subtitle_profile": True}), encoding="utf-8"
            )

            result = build_rendered_product_qa(root, root, probe_func=probe, sampler_func=sampler)

            rules = {b["rule"] for b in result["blocking"]}
            self.assertNotIn("title_effect_evidence_missing", rules)
            self.assertIn(
                "title_effect_not_composited_in_profile",
                {w["rule"] for w in result["warnings"]},
            )
            self.assertTrue(result["pass"])

    def test_write_json_artifact(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = build_rendered_product_qa(root, root)
            out = root / "rendered_product_qa.json"
            out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

            loaded = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(loaded["artifact_role"], "rendered_product_qa")


if __name__ == "__main__":
    unittest.main()
