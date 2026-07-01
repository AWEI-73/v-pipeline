import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.verified_preview_package import (
    package_verified_preview,
    promote_verified_preview_to_final,
    record_verified_preview_review_decision,
)


def _write(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class VerifiedPreviewPackageTest(unittest.TestCase):
    def test_packages_verified_preview_without_creating_final_mp4(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            preview = root / "single_source_highlight_preview.mp4"
            preview.write_bytes(b"preview")
            _write(root / "delivery_gate.json", {
                "artifact_role": "delivery_gate",
                "pass": True,
                "blocking": [],
            })
            _write(root / "final_product_verify" / "final_product_verify_bundle.json", {
                "artifact_role": "final_product_verify_bundle",
                "pass": True,
                "video": str(preview),
            })
            _write(root / "highlight_cut_report.json", {
                "artifact_role": "highlight_cut_report",
                "out": str(preview),
            })

            package = package_verified_preview(root)

            self.assertEqual(package["artifact_role"], "verified_preview_package")
            self.assertEqual(package["status"], "ready_for_operator_delivery_review")
            self.assertEqual(package["source_video"], "single_source_highlight_preview.mp4")
            self.assertEqual(package["packaged_video"], "delivery_candidate.mp4")
            self.assertFalse(package["promotes_to_final_mp4"])
            self.assertTrue((root / "delivery_candidate.mp4").exists())
            self.assertFalse((root / "final.mp4").exists())
            saved = json.loads((root / "verified_preview_package.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["next_action"], "operator_review_or_explicit_final_promotion")
            packet = json.loads((root / "verified_preview_review_packet.json").read_text(encoding="utf-8"))
            self.assertEqual(packet["artifact_role"], "verified_preview_review_packet")
            self.assertEqual(packet["candidate_video"], "delivery_candidate.mp4")
            self.assertFalse(packet["promotes_to_final_mp4"])
            self.assertTrue((root / "review_report.md").is_file())

    def test_packages_rough_cut_preview_report_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            preview = root / "rough_cut_preview.mp4"
            preview.write_bytes(b"preview")
            _write(root / "delivery_gate.json", {
                "artifact_role": "delivery_gate",
                "pass": True,
                "blocking": [],
            })
            _write(root / "final_product_verify_bundle.json", {
                "artifact_role": "final_product_verify_bundle",
                "pass": True,
                "video": str(preview),
            })
            _write(root / "rough_cut_preview_report.json", {
                "artifact_role": "rough_cut_preview_report",
                "ok": True,
                "output_video": str(preview),
            })

            package = package_verified_preview(root)

            self.assertEqual(package["source_video"], "rough_cut_preview.mp4")
            self.assertEqual(package["packaged_video"], "delivery_candidate.mp4")
            self.assertTrue((root / "delivery_candidate.mp4").exists())
            self.assertFalse((root / "final.mp4").exists())

    def test_packages_storyboard_preview_report_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            preview = root / "rough_cut_storyboard_preview.mp4"
            preview.write_bytes(b"preview")
            _write(root / "delivery_gate.json", {
                "artifact_role": "delivery_gate",
                "pass": True,
                "blocking": [],
            })
            _write(root / "final_product_verify_bundle.json", {
                "artifact_role": "final_product_verify_bundle",
                "pass": True,
                "video": str(preview),
            })
            _write(root / "rough_cut_storyboard_preview_report.json", {
                "artifact_role": "rough_cut_storyboard_preview_report",
                "ok": True,
                "output_video": str(preview),
            })

            package = package_verified_preview(root)

            self.assertEqual(package["source_video"], "rough_cut_storyboard_preview.mp4")
            self.assertEqual(package["packaged_video"], "delivery_candidate.mp4")
            self.assertTrue((root / "delivery_candidate.mp4").exists())
            self.assertFalse((root / "final.mp4").exists())

    def test_requires_passing_delivery_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "single_source_highlight_preview.mp4").write_bytes(b"preview")
            _write(root / "delivery_gate.json", {
                "artifact_role": "delivery_gate",
                "pass": False,
            })
            _write(root / "final_product_verify_bundle.json", {
                "artifact_role": "final_product_verify_bundle",
                "pass": True,
            })

            with self.assertRaises(ValueError):
                package_verified_preview(root)

    def test_requires_passing_final_product_verify(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "single_source_highlight_preview.mp4").write_bytes(b"preview")
            _write(root / "delivery_gate.json", {
                "artifact_role": "delivery_gate",
                "pass": True,
            })
            _write(root / "final_product_verify_bundle.json", {
                "artifact_role": "final_product_verify_bundle",
                "pass": False,
            })

            with self.assertRaises(ValueError):
                package_verified_preview(root)

    def test_cli_writes_package(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            preview = root / "single_source_highlight_preview.mp4"
            preview.write_bytes(b"preview")
            _write(root / "delivery_gate.json", {
                "artifact_role": "delivery_gate",
                "pass": True,
                "blocking": [],
            })
            _write(root / "final_product_verify_bundle.json", {
                "artifact_role": "final_product_verify_bundle",
                "pass": True,
                "video": str(preview),
            })
            _write(root / "highlight_cut_report.json", {
                "artifact_role": "highlight_cut_report",
                "out": str(preview),
            })
            proc = subprocess.run(
                ["python", "tools/package_verified_preview.py", "--run", str(root), "--json"],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["artifact_role"], "verified_preview_package")
            self.assertTrue((root / "delivery_candidate.mp4").exists())

    def test_promotes_packaged_candidate_to_final_with_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate = root / "delivery_candidate.mp4"
            candidate.write_bytes(b"candidate")
            _write(root / "delivery_gate.json", {
                "artifact_role": "delivery_gate",
                "pass": True,
            })
            _write(root / "final_product_verify_bundle.json", {
                "artifact_role": "final_product_verify_bundle",
                "pass": True,
            })
            _write(root / "verified_preview_package.json", {
                "artifact_role": "verified_preview_package",
                "status": "ready_for_operator_delivery_review",
                "packaged_video": "delivery_candidate.mp4",
                "promotes_to_final_mp4": False,
            })

            report = promote_verified_preview_to_final(root, reviewer="operator")

            self.assertEqual(report["artifact_role"], "final_promotion_report")
            self.assertEqual(report["status"], "promoted")
            self.assertEqual(report["source_package"], "verified_preview_package.json")
            self.assertEqual(report["source_video"], "delivery_candidate.mp4")
            self.assertEqual(report["final_video"], "final.mp4")
            self.assertEqual(report["reviewer"], "operator")
            self.assertTrue((root / "final.mp4").exists())
            self.assertEqual((root / "final.mp4").read_bytes(), b"candidate")
            requirements = json.loads((root / "delivery_requirements.json").read_text(encoding="utf-8"))
            self.assertTrue(requirements["requires_audio"])
            self.assertFalse(requirements["requires_narration"])
            self.assertFalse(requirements["requires_music"])
            self.assertFalse(requirements["requires_subtitles"])
            mix = json.loads((root / "audio_mix_report.json").read_text(encoding="utf-8"))
            self.assertTrue(mix["audio_stream_present"])
            self.assertFalse(mix["narration_included"])
            self.assertFalse(mix["music_included"])
            saved = json.loads((root / "final_promotion_report.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["next_action"], "write_delivery_gate_report")

    def test_promote_does_not_overwrite_existing_delivery_requirements(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "delivery_candidate.mp4").write_bytes(b"candidate")
            _write(root / "verified_preview_package.json", {
                "artifact_role": "verified_preview_package",
                "status": "ready_for_operator_delivery_review",
                "packaged_video": "delivery_candidate.mp4",
            })
            _write(root / "delivery_requirements.json", {
                "artifact_role": "delivery_requirements",
                "requires_audio": True,
                "requires_narration": True,
                "requires_music": True,
                "requires_subtitles": True,
            })
            _write(root / "audio_mix_report.json", {
                "artifact_role": "audio_mix_report",
                "audio_stream_present": True,
                "narration_included": True,
                "music_included": True,
            })

            promote_verified_preview_to_final(root)

            requirements = json.loads((root / "delivery_requirements.json").read_text(encoding="utf-8"))
            mix = json.loads((root / "audio_mix_report.json").read_text(encoding="utf-8"))
            self.assertTrue(requirements["requires_narration"])
            self.assertTrue(requirements["requires_music"])
            self.assertTrue(requirements["requires_subtitles"])
            self.assertTrue(mix["narration_included"])
            self.assertTrue(mix["music_included"])

    def test_promote_refuses_to_overwrite_final_by_default(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "delivery_candidate.mp4").write_bytes(b"candidate")
            (root / "final.mp4").write_bytes(b"existing")
            _write(root / "verified_preview_package.json", {
                "artifact_role": "verified_preview_package",
                "status": "ready_for_operator_delivery_review",
                "packaged_video": "delivery_candidate.mp4",
            })

            with self.assertRaises(FileExistsError):
                promote_verified_preview_to_final(root)

            self.assertEqual((root / "final.mp4").read_bytes(), b"existing")

    def test_promote_requires_ready_package(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "delivery_candidate.mp4").write_bytes(b"candidate")
            _write(root / "verified_preview_package.json", {
                "artifact_role": "verified_preview_package",
                "status": "draft",
                "packaged_video": "delivery_candidate.mp4",
            })

            with self.assertRaises(ValueError):
                promote_verified_preview_to_final(root)

    def test_promote_cli_writes_final(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "delivery_candidate.mp4").write_bytes(b"candidate")
            _write(root / "verified_preview_package.json", {
                "artifact_role": "verified_preview_package",
                "status": "ready_for_operator_delivery_review",
                "packaged_video": "delivery_candidate.mp4",
            })

            proc = subprocess.run(
                [
                    "python",
                    "tools/promote_verified_preview.py",
                    "--run",
                    str(root),
                    "--reviewer",
                    "operator",
                    "--json",
                ],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["artifact_role"], "final_promotion_report")
            self.assertTrue((root / "final.mp4").exists())

    def test_records_review_decision_without_promoting_final(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "delivery_candidate.mp4").write_bytes(b"candidate")
            _write(root / "verified_preview_package.json", {
                "artifact_role": "verified_preview_package",
                "status": "ready_for_operator_delivery_review",
                "packaged_video": "delivery_candidate.mp4",
            })

            decision = record_verified_preview_review_decision(
                root,
                decision="revise-workbench",
                reviewer="tester",
                notes="tighten the ending",
            )

            self.assertEqual(decision["artifact_role"], "verified_preview_review_decision")
            self.assertEqual(decision["decision"], "revise_workbench")
            self.assertEqual(decision["reviewer"], "tester")
            self.assertEqual(decision["next_action"], "open_workbench_for_preview_revision")
            self.assertEqual(decision["route_back"][0]["owner"], "brownfield-edit")
            self.assertFalse((root / "final.mp4").exists())
            saved = json.loads((root / "verified_preview_review_decision.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["notes"], "tighten the ending")

    def test_review_decision_rejects_unknown_decision(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "delivery_candidate.mp4").write_bytes(b"candidate")
            _write(root / "verified_preview_package.json", {
                "artifact_role": "verified_preview_package",
                "status": "ready_for_operator_delivery_review",
                "packaged_video": "delivery_candidate.mp4",
            })

            with self.assertRaises(ValueError):
                record_verified_preview_review_decision(root, decision="maybe later")

    def test_review_decision_cli_writes_artifact(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "delivery_candidate.mp4").write_bytes(b"candidate")
            _write(root / "verified_preview_package.json", {
                "artifact_role": "verified_preview_package",
                "status": "ready_for_operator_delivery_review",
                "packaged_video": "delivery_candidate.mp4",
            })

            proc = subprocess.run(
                [
                    "python",
                    "tools/verified_preview_review_decision.py",
                    "--run",
                    str(root),
                    "--decision",
                    "rebuild_motion_preview",
                    "--reviewer",
                    "tester",
                    "--json",
                ],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["artifact_role"], "verified_preview_review_decision")
            self.assertEqual(payload["decision"], "rebuild_motion_preview")
            self.assertEqual(payload["mode"], "repair")
            self.assertTrue((root / "verified_preview_review_decision.json").exists())


if __name__ == "__main__":
    unittest.main()
