from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from video_pipeline_core.editorial_comparison import (
    ComparisonError,
    build_comparison_packet,
    build_owner_delta,
    validate_flags,
)
from video_pipeline_core.platform_tools import resolve_ffmpeg, resolve_ffprobe


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class EditorialComparisonTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.left = self.root / "maker_left.review.json"
        self.right = self.root / "maker_right.review.json"
        self.left.write_text(
            json.dumps({"variant_id": "left_original", "content": "left evidence", "frames": ["00:32-00:40"]}, ensure_ascii=False),
            encoding="utf-8",
        )
        self.right.write_text(
            json.dumps({"variant_id": "right_original", "content": "right evidence", "frames": ["00:32-00:40"]}, ensure_ascii=False),
            encoding="utf-8",
        )
        self.spec = {
            "proposition": "時代不斷向前，而人必須學會承擔責任。",
            "rubric": [
                {
                    "id": "ending_concreteness",
                    "question": "哪個 slot 讓這個命題更具體，或結果持平／UNKNOWN？",
                    "permitted_evidence": ["slot_1#00:32-00:40", "slot_2#00:32-00:40"],
                },
                {
                    "id": "ending_promise",
                    "question": "結尾是否履行前段證據建立的承諾？",
                    "permitted_evidence": ["slot_1#cell:ending", "slot_2#cell:ending"],
                },
            ],
        }

    def tearDown(self):
        self.tmp.cleanup()

    def _build(self, name="packet", seed=7):
        return build_comparison_packet(
            decision_id="canon67_seg10_ending",
            proposition_rubric=self.spec,
            variants=[
                {"id": "ending_v2_original", "path": str(self.left)},
                {"id": "ending_v3_original", "path": str(self.right)},
            ],
            output_dir=self.root / name,
            seed=seed,
        )

    def _valid_flags(self, packet_result):
        packet = Path(packet_result["packet_path"])
        return {
            "artifact_role": "editorial_comparison_flags",
            "schema_version": 1,
            "decision_id": "canon67_seg10_ending",
            "packet_path": str(packet),
            "packet_sha256": _sha256(packet),
            "authority": "flag_only",
            "answers": [
                {
                    "rubric_id": "ending_concreteness",
                    "answer": "tie",
                    "evidence_refs": ["slot_1#00:32-00:40"],
                },
                {
                    "rubric_id": "ending_promise",
                    "answer": "unknown",
                    "evidence_refs": [],
                },
            ],
            "findings": [
                {
                    "finding_id": "f1",
                    "rubric_id": "ending_concreteness",
                    "class": "taste",
                    "statement": "The final hold may need a closer comparison.",
                    "evidence_refs": ["slot_1#00:32-00:40"],
                }
            ],
            "human_creative_approval": False,
            "final_delivery_claimed": False,
        }

    def _probe_media(self, path):
        proc = subprocess.run(
            [
                resolve_ffprobe(),
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(path),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(proc.stdout)

    def _frame_md5s(self, path):
        proc = subprocess.run(
            [resolve_ffmpeg(), "-v", "error", "-i", str(path), "-map", "0:v:0", "-f", "framemd5", "-an", "-"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return [line.rsplit(",", 1)[-1] for line in proc.stdout.splitlines() if line and not line.startswith("#")]

    def _write_metadata_mp4(self, path):
        subprocess.run(
            [
                resolve_ffmpeg(),
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "color=c=red:s=16x16:r=5:d=1",
                "-map",
                "0:v:0",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-pix_fmt",
                "yuv420p",
                "-metadata",
                "comment=Made with Remotion test fixture",
                "-metadata",
                "backend=remotion",
                "-metadata",
                "variant_id=ending_v2_original",
                "-metadata",
                f"source_path={self.left}",
                str(path),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_mp4_neutral_transport_stream_copies_and_scrubs_metadata(self):
        source = self.root / "ending_v2_original.mp4"
        self._write_metadata_mp4(source)
        result = build_comparison_packet(
            decision_id="canon67_seg10_ending_mp4",
            proposition_rubric=self.spec,
            variants=[
                {"id": "ending_v2_original", "path": str(source)},
                {"id": "ending_v3_original", "path": str(source)},
            ],
            output_dir=self.root / "mp4_packet",
            seed=3,
        )
        neutral = next((self.root / "mp4_packet" / "reviewer" / "inputs").glob("slot_*.mp4"))
        source_probe = self._probe_media(source)
        neutral_probe = self._probe_media(neutral)

        def shape(probe):
            return {
                "duration": round(float(probe["format"]["duration"]), 6),
                "stream_count": len(probe["streams"]),
                "streams": [
                    {
                        key: stream.get(key)
                        for key in ("codec_type", "codec_name", "width", "height", "avg_frame_rate", "r_frame_rate")
                    }
                    for stream in probe["streams"]
                ],
            }

        self.assertEqual(shape(source_probe), shape(neutral_probe))
        self.assertEqual(self._frame_md5s(source), self._frame_md5s(neutral))
        neutral_text = json.dumps(neutral_probe, ensure_ascii=False).lower()
        for marker in ("remotion", str(source).lower(), "ending_v2_original", "ending_v3_original", "backend"):
            self.assertNotIn(marker, neutral_text)
        self.assertEqual(result["status"], "PASS")

    def test_supported_images_are_reencoded_without_metadata(self):
        source = self.root / "ending_v2_original.jpg"
        image = Image.new("RGB", (8, 6), (20, 40, 60))
        exif = image.getexif()
        exif[270] = "Made with Remotion; ending_v2_original"
        image.save(source, format="JPEG", quality=90, exif=exif, comment=b"backend=remotion")
        result = build_comparison_packet(
            decision_id="canon67_seg10_ending_image",
            proposition_rubric=self.spec,
            variants=[
                {"id": "ending_v2_original", "path": str(source)},
                {"id": "ending_v3_original", "path": str(source)},
            ],
            output_dir=self.root / "image_packet",
            seed=3,
        )
        neutral = next((self.root / "image_packet" / "reviewer" / "inputs").glob("slot_*.jpg"))
        with Image.open(source) as original, Image.open(neutral) as scrubbed:
            self.assertEqual(scrubbed.size, original.size)
            self.assertEqual(scrubbed.mode, original.mode)
            self.assertEqual(dict(scrubbed.getexif()), {})
            self.assertNotIn("exif", scrubbed.info)
            self.assertNotIn("software", scrubbed.info)
            self.assertNotIn("comment", scrubbed.info)
        self.assertEqual(result["status"], "PASS")

    def test_unsupported_binary_fails_closed_without_packet(self):
        source = self.root / "ending_v2_original.bin"
        source.write_bytes(b"not an allowed review binary")
        output = self.root / "unsupported_packet"
        with self.assertRaises(ComparisonError) as ctx:
            build_comparison_packet(
                decision_id="canon67_seg10_ending_binary",
                proposition_rubric=self.spec,
                variants=[
                    {"id": "ending_v2_original", "path": str(source)},
                    {"id": "ending_v3_original", "path": str(source)},
                ],
                output_dir=output,
            )
        self.assertEqual(ctx.exception.code, "comparison_unsupported_binary")
        self.assertFalse(output.exists())

    def test_neutralization_failure_does_not_leave_success_packet(self):
        calls = {"count": 0}

        def fail_on_second(source, destination, original_id):
            if calls["count"] == 0:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(b"partial neutral input")
                calls["count"] += 1
                return
            raise ComparisonError("comparison_blindness_leak", "test neutralization failure")

        output = self.root / "neutralization_failure"
        with patch("video_pipeline_core.editorial_comparison._materialize_neutral_input", side_effect=fail_on_second):
            with self.assertRaises(ComparisonError) as ctx:
                build_comparison_packet(
                    decision_id="canon67_seg10_ending_failure",
                    proposition_rubric=self.spec,
                    variants=[
                        {"id": "ending_v2_original", "path": str(self.left)},
                        {"id": "ending_v3_original", "path": str(self.right)},
                    ],
                    output_dir=output,
                )
        self.assertEqual(ctx.exception.code, "comparison_blindness_leak")
        self.assertFalse(output.exists())

    def test_duplicate_rubric_answer_is_rejected(self):
        result = self._build()
        flags = self._valid_flags(result)
        flags["answers"].append(copy.deepcopy(flags["answers"][0]))
        with self.assertRaises(ComparisonError) as ctx:
            validate_flags(Path(result["packet_path"]), flags)
        self.assertEqual(ctx.exception.code, "comparison_invalid_answer")

    def test_short_variant_id_is_rejected_before_blind_scan(self):
        with self.assertRaises(ComparisonError) as ctx:
            build_comparison_packet(
                decision_id="canon67_seg10_ending_short_id",
                proposition_rubric=self.spec,
                variants=[
                    {"id": "a", "path": str(self.left)},
                    {"id": "ending_v3_original", "path": str(self.right)},
                ],
                output_dir=self.root / "short_id_packet",
            )
        self.assertEqual(ctx.exception.code, "comparison_invalid_input")

    def test_requires_exactly_two_variants(self):
        with self.assertRaises(ComparisonError) as ctx:
            build_comparison_packet(
                decision_id="d",
                proposition_rubric=self.spec,
                variants=[{"id": "only", "path": str(self.left)}],
                output_dir=self.root / "one",
            )
        self.assertEqual(ctx.exception.code, "comparison_requires_exactly_two_variants")

    def test_slot_assignment_is_seed_deterministic_and_bound_to_inputs(self):
        first = self._build("packet_a", seed=19)
        second = self._build("packet_b", seed=19)
        key_a = json.loads(Path(first["key_path"]).read_text(encoding="utf-8"))
        key_b = json.loads(Path(second["key_path"]).read_text(encoding="utf-8"))
        self.assertEqual(key_a["slot_assignment"], key_b["slot_assignment"])
        packet = json.loads(Path(first["packet_path"]).read_text(encoding="utf-8"))
        self.assertEqual(
            {item["sha256"] for item in packet["slots"]},
            {_sha256(path) for path in (self.root / "packet_a" / "reviewer" / "inputs").glob("slot_*.json")},
        )

    def test_reviewer_packet_and_inputs_do_not_leak_maker_identity(self):
        result = self._build()
        packet_dir = self.root / "packet" / "reviewer"
        visible = "\n".join(
            p.read_text(encoding="utf-8", errors="replace")
            for p in packet_dir.rglob("*")
            if p.is_file() and p.suffix.lower() in {".json", ".md", ".txt"}
        )
        for secret in ("ending_v2_original", "ending_v3_original", str(self.left), str(self.right), "remotion"):
            self.assertNotIn(secret, visible)
        self.assertNotIn("owner", json.loads(Path(result["packet_path"]).read_text(encoding="utf-8")))
        self.assertNotIn('"owner_verdict"', visible.lower())
        self.assertNotIn("rationale", visible.lower())

    def test_output_is_immutable_and_existing_artifacts_are_rejected(self):
        result = self._build()
        packet = Path(result["packet_path"])
        before = packet.read_bytes()
        with self.assertRaises(ComparisonError) as ctx:
            self._build()
        self.assertEqual(ctx.exception.code, "comparison_output_exists")
        self.assertEqual(packet.read_bytes(), before)

    def test_valid_flag_only_result_and_packet_input_hash_binding(self):
        result = self._build()
        flags = self._valid_flags(result)
        validated = validate_flags(Path(result["packet_path"]), flags)
        self.assertEqual(validated["status"], "PASS")
        slot_path = next((self.root / "packet" / "reviewer" / "inputs").glob("slot_*.json"))
        slot_path.write_text("changed", encoding="utf-8")
        with self.assertRaises(ComparisonError) as ctx:
            validate_flags(Path(result["packet_path"]), flags)
        self.assertEqual(ctx.exception.code, "comparison_packet_hash_mismatch")

    def test_flags_reject_authority_smuggling_aliases_and_verdicts(self):
        result = self._build()
        cases = [
            {"winner": "slot_1"},
            {"globalWinner": "slot_1"},
            {"decision": "approved"},
            {"canonicalStateMutation": True},
            {"findings": [{"statement": "PASS and approved for delivery"}]},
        ]
        for mutation in cases:
            with self.subTest(mutation=mutation):
                flags = self._valid_flags(result)
                flags.update(mutation)
                with self.assertRaises(ComparisonError) as ctx:
                    validate_flags(Path(result["packet_path"]), flags)
                self.assertEqual(ctx.exception.code, "comparison_forbidden_verdict")

    def test_non_unknown_answer_and_finding_require_permitted_evidence(self):
        result = self._build()
        flags = self._valid_flags(result)
        flags["answers"][0]["evidence_refs"] = []
        with self.assertRaises(ComparisonError) as ctx:
            validate_flags(Path(result["packet_path"]), flags)
        self.assertEqual(ctx.exception.code, "comparison_evidence_required")

        flags = self._valid_flags(result)
        flags["findings"][0]["evidence_refs"] = ["slot_1#missing"]
        with self.assertRaises(ComparisonError) as ctx:
            validate_flags(Path(result["packet_path"]), flags)
        self.assertEqual(ctx.exception.code, "comparison_evidence_required")

    def test_unknown_and_tie_are_allowed_with_flag_only_authority(self):
        result = self._build()
        flags = self._valid_flags(result)
        flags["answers"][0] = {"rubric_id": "ending_concreteness", "answer": "unknown", "evidence_refs": []}
        flags["findings"] = []
        self.assertEqual(validate_flags(Path(result["packet_path"]), flags)["status"], "PASS")

    def test_flags_require_false_approval_fields(self):
        result = self._build()
        for field in ("human_creative_approval", "final_delivery_claimed"):
            flags = self._valid_flags(result)
            flags[field] = True
            with self.assertRaises(ComparisonError) as ctx:
                validate_flags(Path(result["packet_path"]), flags)
            self.assertIn(ctx.exception.code, {"comparison_forbidden_verdict", "comparison_invalid_authority"})

    def test_utf8_proposition_and_rubric_round_trip(self):
        result = self._build()
        packet = json.loads(Path(result["packet_path"]).read_text(encoding="utf-8"))
        self.assertEqual(packet["proposition"], self.spec["proposition"])
        self.assertNotIn("\ufffd", Path(result["packet_path"]).read_text(encoding="utf-8"))

    def test_generated_flags_template_resolves_from_reviewer_directory(self):
        result = self._build("generated_flags_template")
        template_path = Path(result["flags_template_path"])
        template = json.loads(template_path.read_text(encoding="utf-8"))
        fixture = self._valid_flags(result)
        template["answers"] = fixture["answers"]
        template["findings"] = fixture["findings"]
        flags_path = template_path.parent / "editorial_comparison_flags.json"
        flags_path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        self.assertEqual(template["packet_path"], "comparison_packet.json")
        other_cwd = self.root / "other_cwd"
        other_cwd.mkdir()
        original_cwd = Path.cwd()
        try:
            os.chdir(other_cwd)
            self.assertEqual(validate_flags(Path(result["packet_path"]), flags_path)["status"], "PASS")
        finally:
            os.chdir(original_cwd)

    def test_generated_owner_template_resolves_from_owner_directory(self):
        result = self._build("generated_owner_template")
        flags_template_path = Path(result["flags_template_path"])
        flags = json.loads(flags_template_path.read_text(encoding="utf-8"))
        fixture_flags = self._valid_flags(result)
        flags["answers"] = fixture_flags["answers"]
        flags["findings"] = fixture_flags["findings"]
        flags_path = flags_template_path.parent / "editorial_comparison_flags.json"
        flags_path.write_text(json.dumps(flags, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        owner_template_path = Path(result["owner_template_path"])
        verdict = json.loads(owner_template_path.read_text(encoding="utf-8"))
        self.assertEqual(verdict["packet_path"], "../reviewer/comparison_packet.json")
        self.assertEqual(verdict["flags_path"], "../reviewer/editorial_comparison_flags.template.json")
        base = self.root / "generated_owner_base.json"
        base.write_text("generated owner base fixture", encoding="utf-8")
        verdict.update(
            {
                "decision": "tie_keep_current",
                "rationale": "Human fixture rationale for binding closure.",
                "packet_sha256": _sha256(Path(result["packet_path"])),
                "flags_path": "../reviewer/editorial_comparison_flags.json",
                "flags_sha256": _sha256(flags_path),
                "base_state_path": str(base),
                "base_state_sha256": _sha256(base),
            }
        )
        verdict_path = owner_template_path.parent / "owner_verdict.fixture.json"
        verdict_path.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        output = self.root / "generated_owner_delta.json"
        built = build_owner_delta(
            packet_path=Path(result["packet_path"]),
            key_path=Path(result["key_path"]),
            flags_path=flags_path,
            verdict_path=verdict_path,
            base_state_path=base,
            output_path=output,
        )
        self.assertEqual(built["status"], "PASS")
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["operation_result"], "proposed_only")

    def test_owner_relative_references_never_fallback_to_process_cwd(self):
        result = self._build("owner_relative_no_cwd_fallback")
        flags = self._valid_flags(result)
        flags_path = self.root / "flags.json"
        flags_path.write_text(json.dumps(flags, ensure_ascii=False, indent=2), encoding="utf-8")
        base = self.root / "revision_0000.json"
        base.write_text("base state fixture", encoding="utf-8")
        packet_path = Path(result["packet_path"])
        verdict = {
            "artifact_role": "owner_comparison_verdict",
            "schema_version": 1,
            "reviewer_role": "human_owner",
            "decision_id": "canon67_seg10_ending",
            "decision": "tie_keep_current",
            "rationale": "Relative bindings must resolve beside this owner artifact only.",
            "packet_path": "comparison_packet.json",
            "packet_sha256": _sha256(packet_path),
            "flags_path": str(flags_path),
            "flags_sha256": _sha256(flags_path),
            "base_state_path": str(base),
            "base_state_sha256": _sha256(base),
        }
        verdict_path = self.root / "owner_verdict.json"
        verdict_path.write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")
        original_cwd = Path.cwd()
        try:
            os.chdir(packet_path.parent)
            with self.assertRaises(ComparisonError) as ctx:
                build_owner_delta(
                    packet_path=packet_path,
                    key_path=Path(result["key_path"]),
                    flags_path=flags_path,
                    verdict_path=verdict_path,
                    base_state_path=base,
                    output_path=self.root / "unexpected_delta.json",
                )
        finally:
            os.chdir(original_cwd)
        self.assertEqual(ctx.exception.code, "comparison_packet_hash_mismatch")
        self.assertFalse((self.root / "unexpected_delta.json").exists())

    def test_generated_flags_template_declares_exact_finding_schema(self):
        result = self._build("finding_schema_template")
        template = json.loads(Path(result["flags_template_path"]).read_text(encoding="utf-8"))
        schema = template["finding_schema"]
        self.assertEqual(
            schema["required_fields"],
            ["finding_id", "rubric_id", "class", "statement", "evidence_refs"],
        )
        self.assertEqual(schema["class_vocabulary"], ["structural_candidate", "taste"])
        self.assertEqual(schema["evidence_refs"], "non-empty list of permitted evidence references")

    def test_editing_loop_skill_declares_exact_finding_schema(self):
        skill = (ROOT / "skills" / "editing-loop-director.md").read_text(encoding="utf-8")
        for field in ("finding_id", "rubric_id", "class", "statement", "evidence_refs"):
            self.assertIn(field, skill)
        self.assertIn("structural_candidate | taste", skill)

    def test_owner_delta_requires_human_verdict_and_is_proposed_only(self):
        result = self._build()
        flags = self._valid_flags(result)
        flags_path = self.root / "flags.json"
        flags_path.write_text(json.dumps(flags, ensure_ascii=False, indent=2), encoding="utf-8")
        base = self.root / "revision_0000.json"
        base.write_text("base state fixture", encoding="utf-8")
        output = self.root / "proposed_delta.json"
        with self.assertRaises(ComparisonError) as ctx:
            build_owner_delta(
                packet_path=Path(result["packet_path"]),
                key_path=Path(result["key_path"]),
                flags_path=flags_path,
                verdict_path=None,
                base_state_path=base,
                output_path=output,
            )
        self.assertEqual(ctx.exception.code, "comparison_human_verdict_required")

        verdict = {
            "artifact_role": "owner_comparison_verdict",
            "schema_version": 1,
            "reviewer_role": "human_owner",
            "decision_id": "canon67_seg10_ending",
            "decision": "select_variant",
            "selected_variant_id": "ending_v2_original",
            "rationale": "Human owner rationale stays outside the blind reviewer packet.",
            "packet_path": str(result["packet_path"]),
            "packet_sha256": _sha256(Path(result["packet_path"])),
            "flags_path": str(flags_path),
            "flags_sha256": _sha256(flags_path),
            "base_state_path": str(base),
            "base_state_sha256": _sha256(base),
        }
        verdict_path = self.root / "owner_verdict.json"
        verdict_path.write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")
        base_before = base.read_bytes()
        built = build_owner_delta(
            packet_path=Path(result["packet_path"]),
            key_path=Path(result["key_path"]),
            flags_path=flags_path,
            verdict_path=verdict_path,
            base_state_path=base,
            output_path=output,
        )
        delta = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(built["status"], "PASS")
        self.assertEqual(delta["artifact_role"], "editorial_comparison_proposed_delta")
        self.assertEqual(delta["operation_result"], "proposed_only")
        self.assertEqual(delta["human_creative_approval"], False)
        self.assertEqual(delta["final_delivery_claimed"], False)
        self.assertEqual(base.read_bytes(), base_before)

    def test_owner_delta_rejects_wrong_base_key_packet_or_flags_hash(self):
        result = self._build()
        flags = self._valid_flags(result)
        flags_path = self.root / "flags.json"
        flags_path.write_text(json.dumps(flags, ensure_ascii=False, indent=2), encoding="utf-8")
        base = self.root / "revision_0000.json"
        base.write_text("base state fixture", encoding="utf-8")
        verdict = {
            "artifact_role": "owner_comparison_verdict",
            "schema_version": 1,
            "reviewer_role": "human_owner",
            "decision_id": "canon67_seg10_ending",
            "decision": "tie_keep_current",
            "rationale": "keep current",
            "packet_path": str(result["packet_path"]),
            "packet_sha256": _sha256(Path(result["packet_path"])),
            "flags_path": str(flags_path),
            "flags_sha256": _sha256(flags_path),
            "base_state_path": str(base),
            "base_state_sha256": "0" * 64,
        }
        verdict_path = self.root / "owner_verdict.json"
        verdict_path.write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")
        with self.assertRaises(ComparisonError) as ctx:
            build_owner_delta(
                packet_path=Path(result["packet_path"]),
                key_path=Path(result["key_path"]),
                flags_path=flags_path,
                verdict_path=verdict_path,
                base_state_path=base,
                output_path=self.root / "delta.json",
            )
        self.assertEqual(ctx.exception.code, "comparison_base_state_hash_mismatch")

    def test_cli_is_thin_and_emits_machine_readable_codes(self):
        proc = subprocess.run(
            [sys.executable, "tools/editorial_comparison.py", "build-packet", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("build-packet", proc.stdout)


if __name__ == "__main__":
    unittest.main()
